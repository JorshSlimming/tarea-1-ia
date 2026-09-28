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

Experimento definitivo: **`final_v2`** (experiment hash `a65eb91a39ef4179`).
**3000/3000 corridas completas**: 3 mapas × 200 seeds × 5 algoritmos,
200 corridas por combinación (mapa, algoritmo), 0 duplicados.
Configuración final: fuego k=2 p=0.4, MAX_TURNS=200, 30 agentes,
GA H=60/pop30/gen20, 10 workers.

`final_v1` (hash `718a8e29bed05af7`) se preserva como baseline histórico
de diagnóstico; no borrar ni sobrescribir `results/final_v1`.

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

## Benchmark V2 (completo)

Pilotos de calibración (seeds `10000..10009`, nunca seeds finales):

```bash
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_classic_v2.json --workers 10
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h60.json --workers 10
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h100.json --workers 10
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h120.json --workers 10
```

Decisión: **H=60** — H100/H120 no mejoran supervivencia (±0.01, ruido)
y duplican runtime. `config/final_v2.json` quedó fijado con H60.

### Benchmark final V2 (3000/3000, 2026-09-27)

```bash
PYTHONPATH=. .venv/bin/python main.py hash --config config/final_v2.json
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/final_v2.json --workers 10
```

Reejecutar el mismo comando reanuda las corridas faltantes. El runner usa
`experiment_hash = config + código + mapas` y aborta si se intenta mezclar
otro experimento en el mismo directorio.

## Analizar resultados

```bash
PYTHONPATH=. .venv/bin/python main.py analyze --outdir results/final_v2
```

Genera `summary.csv` y gráficos de supervivencia, clearance, resultados finales y congestión.

## Resultados finales (summary.csv de final_v2)

Supervivencia media ± std:

| mapa | bfs | ucs | greedy | astar | ga |
|---|---|---|---|---|---|
| map1 | 0.49±0.32 | 0.49±0.32 | 0.48±0.32 | 0.49±0.32 | 0.20±0.10 |
| map2 | 0.85±0.25 | 0.84±0.25 | 0.83±0.26 | 0.84±0.25 | 0.73±0.28 |
| map3 | 0.85±0.24 | 0.85±0.24 | 0.85±0.24 | 0.85±0.24 | 0.84±0.25 |

Clearance medio ± std (solo corridas con ≥1 evacuado):

| mapa | bfs | ucs | greedy | astar | ga |
|---|---|---|---|---|---|
| map1 | 48.6±28.0 | 50.1±29.4 | 52.1±30.2 | 49.8±29.1 | 52.4±36.8 |
| map2 | 35.8±7.3 | 37.1±8.2 | 37.2±8.5 | 36.9±8.0 | 49.4±19.1 |
| map3 | 33.9±6.7 | 34.0±6.8 | 33.9±6.7 | 34.0±6.8 | 34.0±7.2 |

Lectura: clásicos indistinguibles en supervivencia (mismo snapshot + replan
cada turno). GA guiado real V2 mejora map2 (0.55→0.73) y map3 (0.80→0.84)
respecto de V1; map1 sigue bajo (0.20, H=60 corto para la serpentina).
Runtime es telemetría: GA V2 ~12s/corrida (mediana) vs ~65s en V1 (5.2×);
CPU total 15.6h→3.7h (4.2×), wall 93→22 min con 10 workers.

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

## Nota sobre `final_v1` (baseline histórico)

No borrar ni sobrescribir `results/final_v1` (3000 corridas, hash
`718a8e29bed05af7`). Es el baseline anterior a V2: documenta los problemas
detectados (turnos 0-based, occupancy sin rebuild, GA uniforme, hash solo
JSON) y permite cuantificar la optimización (CPU 15.6h→3.7h, GA 5.2×).
Los resultados del informe son los de `final_v2`.

## Uso de IA generativa

Se utilizaron ChatGPT (OpenAI) y el asistente de codificación indicado durante el desarrollo como apoyo para discutir diseño, revisar arquitectura/código, detectar problemas, proponer tests y optimizaciones, y estructurar documentación. Las decisiones, ejecución, validación y análisis deben ser revisados por el autor, quien es responsable de comprender y explicar el código, los modelos y los resultados presentados.
