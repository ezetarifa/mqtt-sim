"""Cinco escenarios demostrativos para la presentación del 14/10."""
import csv
import json
from pathlib import Path
from simulacion import Configuracion, Mockup, guardar


def main():
    destino = Path(__file__).resolve().parents[1] / 'resultados'
    casos = [('base_2B_1msg', 2, 1), ('base_3B_10msg', 3, 10),
             ('medio_1KiB_10msg', 1024, 10), ('alto_128KiB_10msg', 131072, 10),
             ('estres_128KiB_50msg', 131072, 50)]
    filas = []
    for nombre, payload, frecuencia in casos:
        r = Mockup(Configuracion(payload_bytes=payload, frecuencia=frecuencia)).ejecutar()
        guardar(r, destino / 'detalle' / nombre)
        filas.append({'escenario': nombre, 'payload_bytes': payload,
                      'frecuencia': frecuencia, **r['resumen']})
        s = r['resumen']
        print(f"{nombre}: recibidos={s['recibidos']} descartados={s['descartados']} "
              f"latencia={s['latencia_media_ms']:.3f} ms "
              f"jitter={s['jitter_desviacion_ms']:.3f} ms "
              f"throughput={s['throughput_util_KiB_s']:.3f} KiB/s")
    destino.mkdir(parents=True, exist_ok=True)
    with (destino / 'comparacion.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
    (destino / 'comparacion.json').write_text(json.dumps(filas, indent=2), encoding='utf-8')
    print('Los cinco casos son simulados. Home I/O se reemplaza temporalmente por un receptor de prueba.')


if __name__ == '__main__':
    main()
