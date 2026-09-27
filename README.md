# Tarea 1 — Escape de la Torre

Simulador de evacuación multiagente en grilla 25×25 con congestión, fuego dinámico y cinco planners:

- BFS
- Uniform Cost Search
- Greedy Best-First
- A*
- Algoritmo Genético propio

## Autor

- Nombre: Jorge Slimming
- Curso: Inteligencia Artificial 2026-2

## Estado del proyecto

`final_v1` quedó archivado como baseline completo de 3000 corridas. La revisión V2 corrige indexación de turnos, invariantes de ocupación, trazabilidad experimental y la inicialización/rendimiento del GA.

Consultar:

- `CHANGELOG_V2.md`
- `MIGRACION_V1_A_V2.md`
- `V2_VALIDACION.md`
- `RESULTADOS.md`

## Requisitos

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Tests

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

Al empaquetar V2: **56 tests passing**.

## Ejecutar una simulación

```bash
PYTHONPATH=. .venv/bin/python main.py run \
  --map map1 --algorithm astar --seed 10000
```

Algoritmos válidos: `bfs`, `ucs`, `greedy`, `astar`, `ga`.

## Benchmark V2

### Piloto clásico con condiciones finales

```bash
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_classic_v2.json --workers 10
```

### Pilotos GA

```bash
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h60.json --workers 10

PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h100.json --workers 10

PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h120.json --workers 10
```

Estos pilotos usan seeds `10000..10009` y no contaminan las seeds finales `0..199`.

### Benchmark final V2

Después de escoger el horizonte del GA usando **sólo los pilotos**, actualizar si corresponde `config/final_v2.json` y ejecutar:

```bash
PYTHONPATH=. .venv/bin/python main.py hash --config config/final_v2.json
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/final_v2.json --workers 10
```

Reejecutar el mismo comando reanuda las corridas faltantes. El runner usa `experiment_hash = config + código + mapas` y aborta si se intenta mezclar otro experimento en el mismo directorio.

## Analizar resultados

```bash
PYTHONPATH=. .venv/bin/python main.py analyze --outdir results/final_v2
```

Genera `summary.csv` y gráficos de supervivencia, clearance, resultados finales y congestión.

## Resultados

```text
results/<experimento>/
├── config.json
├── manifest.json
├── runs.csv
├── agents.csv
├── summary.csv
└── plots/
```

`manifest.json` V2 registra:

- config hash;
- code hash;
- maps hash;
- experiment hash;
- commit/estado Git cuando está disponible;
- cantidad de corridas y workers.

## Mapas

Símbolos:

- `#`: muro, capacidad 0
- `.`: piso, capacidad 2
- `n`: paso estrecho, capacidad 1
- `E`: salida, capacidad 1

Mapas:

- `map1`: alta densidad / serpentina / cuello de botella.
- `map2`: oficinas / laberinto corporativo.
- `map3`: entorno semiabierto con múltiples rutas.

## Reproducibilidad

Un escenario se identifica por `(mapa, seed)` y fija:

- posiciones iniciales;
- foco de incendio;
- fire timeline;
- seeds de conflictos y GA.

Los cinco algoritmos enfrentan el mismo escenario. Los planners sólo observan el presente; no conocen el futuro del incendio.

## Nota sobre `final_v1`

No borrar ni sobrescribir `results/final_v1`. Es el baseline anterior a V2 y permite documentar qué problemas se detectaron y cuánto se optimizó el GA.

## Uso de IA generativa

Se utilizaron ChatGPT (OpenAI) y el asistente de codificación indicado durante el desarrollo como apoyo para discutir diseño, revisar arquitectura/código, detectar problemas, proponer tests y optimizaciones, y estructurar documentación. Las decisiones, ejecución, validación y análisis deben ser revisados por el autor, quien es responsable de comprender y explicar el código, los modelos y los resultados presentados.
