# Simulador MQTT con SimPy

**Sistemas de Tiempo Real — Trabajo Final Integrador**

## Requisitos

- Python 3.10 o superior — verificar con `python3 --version`
- SimPy 4.1.2

## Instalación

```bash
# 1. Crear el entorno virtual dentro de mqtt-sim/
python3 -m venv .venv

# 2. Activar el entorno
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 3. Instalar la dependencia
pip install -r codigo/requirements.txt
```

## Uso

Todos los comandos se ejecutan desde la carpeta `mqtt-sim/` con el entorno activado.

### Correr la demostración (5 casos)

```bash
python codigo/demo.py
```

Ejecuta los cinco escenarios con 100 mensajes cada uno y guarda los resultados en `resultados/`.

### Ejecutar los tests

```bash
python codigo/pruebas.py -v
```

Deben pasar los 5 tests. Si alguno falla, el modelo tiene un error.

### Probar un caso personalizado

```bash
python codigo/simulacion.py --payload 1024 --frecuencia 5 --mensajes 100 --cola 10
```

| Argumento | Descripción | Ejemplo |
|---|---|---|
| `--payload` | Tamaño útil del mensaje en bytes | `131072` (128 KiB) |
| `--frecuencia` | Mensajes generados por segundo | `50` |
| `--mensajes` | Cantidad total de mensajes | `100` |
| `--cola` | Tamaño del buffer en cada recurso | `0` (sin espera) |
| `--sin-jitter` | Desactiva la variación aleatoria de propagación | — |

Los resultados quedan en `resultados/otro_caso/`.


## Cinco escenarios de la demo

| Caso | Payload | Frecuencia | Resultado destacado |
|---|---|---|---|
| `base_2B_1msg` | 2 B | 1 msg/s | Caso base del TP anterior |
| `base_3B_10msg` | 3 B | 10 msg/s | Otro caso base, sin descarte |
| `medio_1KiB_10msg` | 1 KiB | 10 msg/s | Latencia mayor |
| `alto_128KiB_10msg` | 128 KiB | 10 msg/s | Latencia media ~ 536 ms (supera deadline de 250 ms) |
| `estres_128KiB_50msg` | 128 KiB | 50 msg/s | 71 % de descarte por buffer lleno |


## Métricas calculadas

| Métrica | Descripción |
|---|---|
| **Latencia media** | Promedio de `(t_llegada − t_generación)` en ms, solo sobre mensajes recibidos |
| **Latencia máxima** | Peor caso registrado |
| **Jitter** | Desviación estándar de las latencias (ms) |
| **Throughput útil** | `recibidos × payload_bytes / 1024 / duración_total` en KiB/s |
| **Tasa de descarte** | `descartados / generados × 100` en % |
| **Tardíos** | % de mensajes recibidos que superaron el deadline de 250 ms |


## Estructura del repositorio

```
mqtt-sim/
├── codigo/
│   ├── simulacion.py      
│   ├── calculos.py        
│   ├── demo.py           
│   ├── pruebas.py        
│   └── requirements.txt   
├── resultados/
│   ├── comparacion.csv    
│   ├── comparacion.json   
│   ├── comparacion.png    
│   └── detalle/          
├
└── README.md  
```
