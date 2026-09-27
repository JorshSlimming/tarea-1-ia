# Validación técnica V2

## Suite automática

Al empaquetar:

```text
56 passed
```

## Microbenchmark GA

Prueba: 30 llamadas a `GeneticPlanner.plan()` para los 30 agentes iniciales de `map1`, seed 0, usando el mismo snapshot inicial y parámetros GA por defecto.

Promedio de tres ejecuciones:

| versión | tiempo bloque |
|---|---:|
| V1 | 1.747 s |
| V2 | 0.338 s |

Speedup observado:

`1.747 / 0.338 ≈ 5.17×`

Este dato mide el hot path inicial del GA, no promete el mismo factor para una simulación completa.

## Qué debe validar el notebook después de copiar el ZIP

```bash
pytest -q
PYTHONPATH=. .venv/bin/python main.py hash --config config/pilot_GA_v2_h60.json
```

Luego ejecutar pilotos. No lanzar `final_v2` hasta haber escogido el horizonte del GA con seeds 10000+.
