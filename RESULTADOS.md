# Registro de resultados (artefactos excluidos del ZIP/entrega)

Fecha: 2026-09-27. Experimento final: `final_v1`, config hash `718a8e29bed05af7`
(fuego k=2, p=0.4, MAX_TURNS=200, 30 agentes, GA H60/pop30/gen20).
Piloto clásico: `pilot_noGA`, hash `ddf4e79d6806bfd2` (k=3, p=0.3, 360 corridas).
Piloto GA acotado: `pilot_GA` (3 corridas map3, factibilidad).

El ZIP `tarea-1-ia_resultados_*.zip` incluye config/manifest/summary/plots de cada
experimento, pero **excluye** los CSV brutos por peso (ver tabla). Todo lo excluido
es regenerable con el mismo hash:

```bash
PYTHONPATH=. .venv/bin/python main.py benchmark --config config/final.json --workers 10
PYTHONPATH=. .venv/bin/python main.py analyze --outdir results/final_v1
```

## Archivos excluidos del ZIP (con verificación)

| Archivo | Filas | Tamaño | SHA-256 |
|---|---|---:|---|
| `results/final_v1/runs.csv` | 3000 corridas + header | 488K | `752e3fda…fd7a2535` |
| `results/final_v1/agents.csv` | 90000 agentes + header | 5.8M | `99a06e1b…c9ae85ad` |
| `results/pilot_noGA/runs.csv` | 360 corridas + header | 64K | `030c208f…f5e825e4` |
| `results/pilot_noGA/agents.csv` | 10800 agentes + header | 752K | `aa16a6c1…c7890d023` |
| `results/pilot_GA/runs.csv` | 3 corridas + header | 4K | `f75adc2a…d0df1ea96` |
| `results/pilot_GA/agents.csv` | 90 agentes + header | 8K | `e41b4f00…af09adb06` |

SHA-256 completos: ver `sha256sum results/*/runs.csv results/*/agents.csv`
al momento de generar este registro (hashes arriba truncados a 16+8 hex).

Completitud verificada `final_v1`: 3000 combos únicos, 0 duplicados/faltantes,
15/15 grupos (mapa, algoritmo) × 200, 1 solo config hash, 23 corridas con
clearance `NaN` (cero evacuados: map1 3 clásicos c/u + 7 GA, map2 GA 3, map3 GA 1).

## Lo que SÍ incluye el ZIP (por experimento)

`config.json` (config efectiva), `manifest.json` (esperadas/completadas + hash +
timestamp), `summary.csv` (media/std/min/max por mapa/algoritmo), `plots/`
(`survival.png`, `clearance.png` donde aplique).

## Resultados finales (summary.csv de final_v1)

### Supervivencia media ± std

| mapa | bfs | ucs | greedy | astar | ga |
|---|---|---|---|---|---|
| map1 | 0.49±0.32 | 0.49±0.32 | 0.48±0.32 | 0.49±0.32 | 0.18±0.10 |
| map2 | 0.85±0.25 | 0.84±0.25 | 0.83±0.26 | 0.84±0.25 | 0.55±0.28 |
| map3 | 0.85±0.24 | 0.85±0.24 | 0.85±0.24 | 0.85±0.24 | 0.80±0.28 |

### Clearance medio ± std (solo corridas con ≥1 evacuado)

| mapa | bfs | ucs | greedy | astar | ga |
|---|---|---|---|---|---|
| map1 | 47.6±28.0 | 49.1±29.4 | 51.1±30.2 | 48.8±29.1 | 84.7±58.1 |
| map2 | 34.8±7.3 | 36.1±8.2 | 36.2±8.5 | 35.9±8.0 | 57.9±28.1 |
| map3 | 32.9±6.7 | 33.0±6.8 | 32.9±6.7 | 33.0±6.8 | 35.1±9.2 |

### Lectura (detalle en informe F17)

- Clásicos indistinguibles en supervivencia (mismo snapshot + replan cada turno);
  Greedy +3 turnos vs BFS en map1.
- GA colapsa en map1 (H=60 corto para serpentina + fuego k=2 p=0.4), pierde en
  map2, compite solo en map3 abierto.
- Runtime es telemetría: GA ~146s/corrida map1 vs <2s clásicos.

## Piloto clásico (pilot_noGA, k=3 p=0.3 — previo a calibración)

| mapa | bfs | ucs | greedy | astar |
|---|---|---|---|---|
| map1 | 0.65±0.31 | 0.64±0.30 | 0.64±0.31 | 0.64±0.31 |
| map2 | 0.99±0.03 | 0.99±0.02 | 0.99±0.03 | 0.99±0.02 |
| map3 | 0.92±0.14 | 0.93±0.13 | 0.91±0.14 | 0.93±0.13 |

Decisión de calibración: map2 degenerado (~99%) → puertas 4→2+estrecha + pilares,
fuego k=3 p=0.3 → k=2 p=0.4 (discriminación verificada: map2 0.99→0.85).
