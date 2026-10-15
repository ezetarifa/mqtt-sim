"""Mock-up de eventos discretos. Home I/O todavía no está conectado."""
import argparse
import csv
import json
import random
import statistics
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import simpy
from calculos import tamanio_publish


@dataclass(frozen=True)
class Configuracion:
    payload_bytes: int = 2
    frecuencia: float = 1
    mensajes: int = 100
    subida_bps: float = 10_000_000
    bajada_bps: float = 10_000_000
    propagacion_por_trayecto_s: float = 0.040
    jitter_por_trayecto_s: float = 0.005
    broker_s: float = 0.001
    cola_maxima: int = 10
    plazo_s: float = 0.250
    semilla: int = 14
    tema: str = 'hogar/orden'

    def validar(self):
        if self.frecuencia <= 0 or self.subida_bps <= 0 or self.bajada_bps <= 0:
            raise ValueError('Frecuencia y capacidades deben ser positivas')
        if not isinstance(self.mensajes, int) or self.mensajes < 1:
            raise ValueError('Se necesita al menos un mensaje')
        if not isinstance(self.cola_maxima, int) or self.cola_maxima < 0:
            raise ValueError('La cola debe ser un entero no negativo')
        if min(self.propagacion_por_trayecto_s, self.jitter_por_trayecto_s, self.broker_s, self.plazo_s) < 0:
            raise ValueError('Los tiempos no pueden ser negativos')
        if self.jitter_por_trayecto_s > self.propagacion_por_trayecto_s:
            raise ValueError('El jitter no puede generar propagación negativa')
        tamanio_publish(self.payload_bytes, self.tema)


class Mockup:
    def __init__(self, config):
        config.validar()
        self.config = config
        self.env = simpy.Environment()
        self.recursos = {nombre: simpy.Resource(self.env, capacity=1)
                         for nombre in ('subida', 'broker', 'bajada')}
        self.registros = []
        self.eventos = []
        self.maximos = dict.fromkeys(self.recursos, 0)
        rng = random.Random(config.semilla)
        self.propagaciones = [tuple(config.propagacion_por_trayecto_s + rng.uniform(
            -config.jitter_por_trayecto_s, config.jitter_por_trayecto_s)
            for _ in range(2)) for _ in range(config.mensajes)]

    def evento(self, mensaje, estado, etapa=''):
        self.eventos.append({'tiempo_s': self.env.now, 'id': mensaje['id'],
                             'evento': estado, 'etapa': etapa,
                             **{'cola_' + k: len(r.queue) for k, r in self.recursos.items()}})

    def atender(self, mensaje, etapa, duracion):
        recurso = self.recursos[etapa]
        if recurso.count >= recurso.capacity and len(recurso.queue) >= self.config.cola_maxima:
            mensaje['estado'] = 'descartado'
            mensaje['descarte_en'] = etapa
            mensaje['final_s'] = self.env.now
            self.evento(mensaje, 'descarte por buffer lleno', etapa)
            return False
        inicio = self.env.now
        with recurso.request() as solicitud:
            self.maximos[etapa] = max(self.maximos[etapa], len(recurso.queue))
            self.evento(mensaje, 'solicitud', etapa)
            yield solicitud
            mensaje['espera_' + etapa + '_s'] = self.env.now - inicio
            self.evento(mensaje, 'inicio de servicio', etapa)
            yield self.env.timeout(duracion)
        self.evento(mensaje, 'fin de servicio', etapa)
        return True

    def mensaje(self, identificador):
        c = self.config
        fila = {'id': identificador, 'payload_bytes': c.payload_bytes,
                'paquete_mqtt_bytes': tamanio_publish(c.payload_bytes, c.tema),
                'generacion_s': self.env.now, 'final_s': '',
                'estado': 'en transito', 'descarte_en': '',
                'espera_subida_s': 0.0, 'espera_broker_s': 0.0, 'espera_bajada_s': 0.0,
                'latencia_ms': '', 'fuera_de_plazo': ''}
        self.registros.append(fila)
        self.evento(fila, 'generado')
        bits = fila['paquete_mqtt_bytes'] * 8
        ok = yield self.env.process(self.atender(fila, 'subida', bits / c.subida_bps))
        if not ok:
            return
        # La propagación no bloquea el transmisor.
        yield self.env.timeout(self.propagaciones[identificador][0])
        ok = yield self.env.process(self.atender(fila, 'broker', c.broker_s))
        if not ok:
            return
        ok = yield self.env.process(self.atender(fila, 'bajada', bits / c.bajada_bps))
        if not ok:
            return
        yield self.env.timeout(self.propagaciones[identificador][1])
        # Receptor provisional. El adaptador real de Home I/O corresponde al 28/10.
        fila['final_s'] = self.env.now
        fila['estado'] = 'recibido en receptor provisional'
        fila['latencia_ms'] = 1000 * (self.env.now - fila['generacion_s'])
        fila['fuera_de_plazo'] = (self.env.now - fila['generacion_s']) > c.plazo_s
        self.evento(fila, 'recibido en receptor provisional')

    def generar(self):
        for identificador in range(self.config.mensajes):
            self.env.process(self.mensaje(identificador))
            if identificador + 1 < self.config.mensajes:
                yield self.env.timeout(1 / self.config.frecuencia)

    def ejecutar(self):
        self.env.process(self.generar())
        self.env.run()  # Se vacían todas las colas al finalizar la generación.
        recibidos = [r for r in self.registros if r['latencia_ms'] != '']
        latencias = [r['latencia_ms'] for r in recibidos]
        descartados = sum(r['estado'] == 'descartado' for r in self.registros)
        assert len(self.registros) == len(recibidos) + descartados
        s = {'generados': len(self.registros), 'recibidos': len(recibidos),
             'descartados': descartados, 'pendientes': 0,
             'latencia_media_ms': statistics.mean(latencias) if latencias else None,
             'jitter_desviacion_ms': statistics.pstdev(latencias) if latencias else None,
             'latencia_maxima_ms': max(latencias) if latencias else None,
             'throughput_util_KiB_s': len(recibidos) * self.config.payload_bytes / 1024 / self.env.now if self.env.now else 0,
             'tasa_descarte_pct': 100 * descartados / self.config.mensajes,
             'tardios_entre_recibidos_pct': 100 * sum(r['fuera_de_plazo'] for r in recibidos) / len(recibidos) if recibidos else None,
             'duracion_total_s': self.env.now, **{'cola_maxima_' + k: v for k, v in self.maximos.items()}}
        return {'configuracion': asdict(self.config), 'resumen': s,
                'mensajes': self.registros, 'eventos': self.eventos}


def guardar(resultado, carpeta):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    for clave in ('mensajes', 'eventos'):
        filas = resultado[clave]
        with (carpeta / (clave + '.csv')).open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=filas[0].keys())
            writer.writeheader()
            writer.writerows(filas)
    (carpeta / 'resumen.json').write_text(json.dumps(
        {k: resultado[k] for k in ('configuracion', 'resumen')}, indent=2, ensure_ascii=False), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=int, default=2, help='Bytes del payload')
    parser.add_argument('--frecuencia', type=float, default=1)
    parser.add_argument('--mensajes', type=int, default=100)
    parser.add_argument('--cola', type=int, default=10, help='Máximo de mensajes esperando en cada recurso')
    parser.add_argument('--sin-jitter', action='store_true')
    parser.add_argument('--salida', default=str(Path(__file__).resolve().parents[1] / 'resultados' / 'otro_caso'))
    args = parser.parse_args()
    c = Configuracion(payload_bytes=args.payload, frecuencia=args.frecuencia,
                      mensajes=args.mensajes, cola_maxima=args.cola)
    if args.sin_jitter:
        c = replace(c, jitter_por_trayecto_s=0)
    r = Mockup(c).ejecutar()
    guardar(r, args.salida)
    print(json.dumps(r['resumen'], indent=2, ensure_ascii=False))
    print('Receptor provisional: Home I/O todavía no está conectado.')


if __name__ == '__main__':
    main()
