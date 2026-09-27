# Tarea 1 — Escape de la Torre

Simulador de evacuación multiagente (30 agentes, grilla 25×25, congestión + fuego dinámico) con 5 planners: BFS, UCS, Greedy, A\* y Algoritmo Genético propio.

## Autor

- Nombre: Jorge Slimming
- Curso: Inteligencia Artificial 2026-2

## Requisitos

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Ejecutar simulación (una corrida)

```bash
PYTHONPATH=. .venv/bin/python main.py run --map map1 --algorithm astar --seed 10000
```

Algoritmos: `bfs`, `ucs`, `greedy`, `astar`, `ga`.

## Ejecutar benchmark (lote con checkpoints y resume)

```bash
PYTHONPATH=. .venv/bin/python main.py benchmark --config config/pilot.json
PYTHONPATH=. .venv/bin/python main.py benchmark --config config/final.json
```

## Reanudar benchmark

El runner omite corridas ya completadas (clave `experiment_id, config_hash, mapa, seed, algoritmo`). Reejecutar el mismo comando retoma donde quedó. `--no-resume` ignora lo previo; `--limit N` corre solo N pendientes.

## Resultados

```
results/<experimento>/
├── config.json     # config efectiva
├── manifest.json   # corridas esperadas/completadas + hash
├── runs.csv        # una fila por simulación
├── agents.csv      # una fila por agente/simulación
├── summary.csv     # media/std/min/max por (mapa, algoritmo)
└── plots/          # survival.png, clearance.png
```

## Mapas

Símbolos: `#` muro (C=0), `.` piso (C=2), `n` paso estrecho (C=1), `E` salida única (C=1, 1 evacuado/turno). Regenerar con `PYTHONPATH=. .venv/bin/python maps/generate_maps.py`.

- `map1`: serpentina de alta densidad (muros alternados, pasos angostos).
- `map2`: oficinas / laberinto corporativo (retícula de salas con puertas).
- `map3`: semiabierto con pilares y compuertas angostas.

## Reproducibilidad

Escenario = `(mapa, seed)`: spawns, foco de fuego, fire timeline y seeds derivadas (`hashlib`, nunca `hash()`). Los 5 algoritmos enfrentan el mismo escenario. RNGs separados: spawn, fuego, conflictos, GA.

## Uso de IA generativa

Herramienta: asistente de codificación (Muse Spark). Apoyo: andamiaje de módulos, tests y layouts bajo especificación de `docs/`. Revisión: cada decisión se verificó contra `docs/` y con los 52 tests + pilotos; se corrigieron motor de conflictos, evacuación 1/turno y layouts. Responsabilidad: el autor comprende y puede explicar cada módulo.
