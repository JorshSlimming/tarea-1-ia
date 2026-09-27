# Migración segura: final_v1 → V2

## Objetivo

Conservar todo `final_v1` en Git como baseline reproducible y luego aplicar V2 sin sobrescribir sus resultados.

## 1. Antes de copiar V2

En el notebook/repo actual, comprobar que terminó el benchmark y que existen los CSV completos:

```bash
wc -l results/final_v1/runs.csv
wc -l results/final_v1/agents.csv
```

Esperado:

- `runs.csv`: 3001 líneas (header + 3000 corridas).
- `agents.csv`: 90001 líneas (header + 90000 agentes).

Luego hacer commit de V1 (ver mensaje sugerido al final de este documento).

## 2. Crear tag del baseline

```bash
git tag -a final-v1-baseline -m "Baseline final_v1: 3000 corridas completas antes de revisión V2"
git push origin final-v1-baseline
```

El tag no es obligatorio, pero es muy recomendable.

## 3. Aplicar este ZIP

Descomprimir **sobre la raíz del repositorio**. La extracción reemplaza código/configs modificados y agrega archivos V2, pero no debe borrar `results/final_v1/runs.csv` ni `agents.csv` de tu copia local.

Después:

```bash
git status
pytest -q
```

Esperado al empaquetar V2: `56 passed`.

## 4. No usar `config/final.json` para V2

`config/final.json` permanece como referencia V1.

Nuevos archivos:

- `config/pilot_classic_v2.json`
- `config/pilot_GA_v2_h60.json`
- `config/pilot_GA_v2_h100.json`
- `config/pilot_GA_v2_h120.json`
- `config/final_v2.json`

## 5. Pilotos recomendados

Clásicos con las condiciones finales:

```bash
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_classic_v2.json --workers 10
```

GA, comparación de horizontes usando **sólo seeds de piloto**:

```bash
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h60.json --workers 10

PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h100.json --workers 10

PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/pilot_GA_v2_h120.json --workers 10
```

Cada piloto GA usa 10 seeds × 3 mapas = 30 corridas. No usa seeds finales 0..199.

## 6. Elegir H antes de final_v2

Comparar, por mapa:

- supervivencia;
- clearance;
- esperas voluntarias;
- `ga_generations` / `ga_evaluations`;
- runtime.

Después fijar **una sola vez** `ga.horizon` y `ga.mutation_p=1/horizon` en `config/final_v2.json`.

No escoger H mirando los resultados de `final_v1` seed por seed; `final_v1` se usa para diagnosticar, mientras la calibración V2 se realiza con seeds 10000+.

## 7. Ejecutar final_v2

```bash
PYTHONPATH=. .venv/bin/python main.py hash --config config/final_v2.json
PYTHONPATH=. .venv/bin/python main.py benchmark \
  --config config/final_v2.json --workers 10
```

Reanudar exactamente con el mismo comando. Si código, mapas o config cambian, el `experiment_hash` cambia y el runner impedirá mezclar resultados en el mismo outdir.

Al terminar:

```bash
PYTHONPATH=. .venv/bin/python main.py analyze --outdir results/final_v2
```

## Commit sugerido para V1

Título:

```text
chore(results): archive complete final_v1 benchmark baseline
```

Cuerpo sugerido:

```text
Archive the first complete benchmark before the V2 review.

- 3 maps x 200 seeds x 5 algorithms = 3000 runs
- preserve raw runs/agents CSVs, summaries, manifests and plots
- keep final_v1 as an immutable diagnostic baseline
- document runtime bottleneck observed in the genetic algorithm

The next revision will fix turn indexing, occupancy invariants,
experiment provenance and GA initialization/performance without
overwriting these results.
```
