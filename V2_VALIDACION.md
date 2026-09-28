# Validación técnica V2

## Suite automática

Al empaquetar:

```text
56 passed
```

## Microbenchmark GA (hot path)

Prueba: 30 llamadas a `GeneticPlanner.plan()` para los 30 agentes iniciales de `map1`, seed 0, usando el mismo snapshot inicial y parámetros GA por defecto.

Promedio de tres ejecuciones:

| versión | tiempo bloque |
|---|---:|
| V1 | 1.747 s |
| V2 | 0.338 s |

Speedup observado:

`1.747 / 0.338 ≈ 5.17×`

Este dato mide el hot path inicial del GA, no promete el mismo factor para una simulación completa.

## Benchmark completo final_v2 (2026-09-27)

3000/3000 corridas (experiment hash `a65eb91a39ef4179`), 0 duplicados,
200 por combinación (mapa, algoritmo), workers=10, wall ~22 min.

CPU total: V1 15.6h → V2 3.7h (**4.2×**). Medianas: bfs 2.0×, ucs 2.1×,
greedy 1.5×, astar 1.8×, **ga 65.3→12.4s (5.2×)**.

Supervivencia clásicos idéntica V1=V2 (dif 0.000 en los 12 grupos);
GA map2 0.55→0.73, map3 0.80→0.84, map1 0.18→0.20.
Suite: **56 passed**.

## Qué debe validar el notebook después de copiar el ZIP

```bash
pytest -q
PYTHONPATH=. .venv/bin/python main.py hash --config config/pilot_GA_v2_h60.json
```

Luego ejecutar pilotos. No lanzar `final_v2` hasta haber escogido el horizonte del GA con seeds 10000+.

## Nota de cierre (benchmark ya completo)

`final_v2` terminó 3000/3000 el 2026-09-27 (~22 min, 10 workers).
No relanzar `final_v2` salvo cambio de código/mapas/config — el runner
abortaría por cambio de `experiment_hash`. Los resultados del informe
son los de `results/final_v2/summary.csv` + `plots/`.
