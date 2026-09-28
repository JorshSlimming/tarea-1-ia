# Registro de resultados — experimento definitivo: final_v2

Fecha: 2026-09-27. Experimento: `final_v2`, experiment hash `a65eb91a39ef4179`
(config `e807fcfc735986e9`, código `e02d0416b7d51b2a`, mapas `b3362d9604322a0c`).
**3000/3000 corridas**: 3 mapas × 200 seeds × 5 algoritmos, 200 por
combinación (mapa, algoritmo), 0 duplicados/faltantes, 1 solo hash.
Configuración final: fuego k=2 p=0.4, MAX_TURNS=200, 30 agentes,
GA H=60/pop30/gen20, 10 workers, wall ~22 min (20:34–20:56).

Calibración H (pilotos seeds 10000..10009): H60/H100/H120 indistinguibles
en supervivencia (±0.01); H60 fijado por menor runtime (media 30s vs 47s/62s).

## Resultados finales (summary.csv de final_v2)

### Supervivencia media ± std

| mapa | bfs | ucs | greedy | astar | ga |
|---|---|---|---|---|---|
| map1 | 0.49±0.32 | 0.49±0.32 | 0.48±0.32 | 0.49±0.32 | 0.20±0.10 |
| map2 | 0.85±0.25 | 0.84±0.25 | 0.83±0.26 | 0.84±0.25 | 0.73±0.28 |
| map3 | 0.85±0.24 | 0.85±0.24 | 0.85±0.24 | 0.85±0.24 | 0.84±0.25 |

### Clearance medio ± std (solo corridas con ≥1 evacuado)

| mapa | bfs | ucs | greedy | astar | ga |
|---|---|---|---|---|---|
| map1 | 48.6±28.0 | 50.1±29.4 | 52.1±30.2 | 49.8±29.1 | 52.4±36.8 |
| map2 | 35.8±7.3 | 37.1±8.2 | 37.2±8.5 | 36.9±8.0 | 49.4±19.1 |
| map3 | 33.9±6.7 | 34.0±6.8 | 33.9±6.7 | 34.0±6.8 | 34.0±7.2 |

### Mejora V1→V2 (misma carga, 10 workers)

CPU total: 15.6h→3.7h (**4.2×**). Medianas por algoritmo:
bfs 0.66→0.33s (2.0×), ucs 1.43→0.68s (2.1×), greedy 0.19→0.13s (1.5×),
astar 0.47→0.26s (1.8×), **ga 65.3→12.4s (5.2×)**. Wall: 93→22 min.
Clásicos con supervivencia idéntica V1=V2 (dif 0.000); GA map2 0.55→0.73
y map3 0.80→0.84 por población guiada real; map1 0.18→0.20 (H=60 corto
para la serpentina).

---

Fecha: 2026-09-27. Experimento final: `final_v1`, config hash `718a8e29bed05af7`

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

---

## Nota posterior: revisión V2

`final_v1` se conserva como **baseline histórico/diagnóstico** y no debe ser
sobrescrito. La revisión posterior detectó:

1. `evacuation_turn` y las muertes causadas por propagación post-movimiento se
   registraban con índice 0-based; los valores de clearance V1 están desplazados
   en -1 respecto del número humano de turnos.
2. La ocupación no se reconstruía inmediatamente después de muertos/atrapados.
3. El bloque “guided” del GA era efectivamente uniforme, igual que `PURE`.
4. El hash V1 cubría sólo el JSON y no código/mapas.
5. El hot path del GA reconstruía el mapa de ocupación reiteradamente.

Los resultados utilizados en el informe final son exclusivamente los de `final_v2`.
`final_v1` se conserva únicamente como baseline histórico para documentar
el diagnóstico y comparar tiempos antes/después.
