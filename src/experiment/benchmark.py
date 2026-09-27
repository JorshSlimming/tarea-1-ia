"""Benchmark runner reproducible con checkpoints, resume y ETA por bloque.

V2 añade:
- `experiment_hash` = config + código + mapas;
- aborta si el outdir contiene otro experimento (evita mezclar CSVs);
- manifest con hashes y Git;
- ETA ponderado por (mapa, algoritmo), importante porque GA es mucho más caro.
"""

from __future__ import annotations

import csv
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from src.experiment.config import load_config, provenance
from src.experiment.metrics import RunMetrics
from src.planners.astar import AStarPlanner
from src.planners.bfs import BFSPlanner
from src.planners.genetic import GAConfig, GeneticPlanner
from src.planners.greedy import GreedyPlanner
from src.planners.uniform_cost import UCSPlanner

RUN_FIELDS = [
    "experiment_id",
    *[
        k
        for k in RunMetrics(algorithm="", map_id="", seed=0).run_row()
    ],
]
AGENT_FIELDS = [
    "experiment_id",
    "algorithm",
    "map_id",
    "seed",
    "config_hash",
    "code_hash",
    "maps_hash",
    "experiment_hash",
    "agent_id",
    "status",
    "status_reason",
    "evacuation_turn",
    "death_turn",
    "voluntary_waits",
    "congestion_waits",
    "replans",
]


def build_planner(name: str, cfg: dict, ga_seed: int):
    if name == "bfs":
        return BFSPlanner()
    if name == "ucs":
        return UCSPlanner()
    if name == "greedy":
        return GreedyPlanner()
    if name == "astar":
        return AStarPlanner()
    if name == "ga":
        g = cfg.get("ga", {})
        return GeneticPlanner(
            GAConfig(
                horizon=g.get("horizon", 60),
                population=g.get("population", 30),
                generations=g.get("generations", 20),
                tournament=g.get("tournament", 3),
                crossover_p=g.get("crossover_p", 0.8),
                mutation_p=g.get("mutation_p", 1 / 60),
                elite=g.get("elite", 2),
                stagnation=g.get("stagnation", 6),
            ),
            ga_seed=ga_seed,
        )
    raise ValueError(f"algoritmo desconocido: {name}")


def _read_rows(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _assert_compatible_outdir(
    runs_path: Path, experiment_id: str, experiment_hash: str, resume: bool
) -> list[dict]:
    rows = _read_rows(runs_path)
    if not rows:
        return []
    if not resume:
        raise RuntimeError(
            f"{runs_path} ya contiene resultados. Usa --resume o un outdir nuevo."
        )
    hashes = {row.get("experiment_hash", "") for row in rows}
    ids = {row.get("experiment_id", "") for row in rows}
    if hashes != {experiment_hash} or ids != {experiment_id}:
        raise RuntimeError(
            "El outdir contiene resultados incompatibles. "
            f"Encontrado experiment_id={sorted(ids)}, hashes={sorted(hashes)}; "
            f"actual experiment_id={experiment_id}, hash={experiment_hash}. "
            "Usa un outdir/experiment_id nuevo (por ejemplo final_v2)."
        )
    return rows


def _done_keys(rows: list[dict]) -> set[tuple[str, int, str]]:
    return {
        (row["map_id"], int(row["seed"]), row["algorithm"])
        for row in rows
    }


def _ensure_header(path: Path, fields: list[str]) -> bool:
    if path.exists() and path.stat().st_size > 0:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    return True


def _hms(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def run_benchmark(
    config_path: str,
    resume: bool = True,
    limit: int | None = None,
    workers: int = 1,
) -> Path:
    import fcntl
    import os
    from concurrent.futures import ProcessPoolExecutor, as_completed

    from .worker import run_one

    cfg = load_config(config_path)
    prov = provenance(cfg)
    exp_id = cfg.get("experiment_id", "exp")
    outdir = Path(cfg.get("outdir", f"results/{exp_id}"))
    outdir.mkdir(parents=True, exist_ok=True)
    runs_path, agents_path = outdir / "runs.csv", outdir / "agents.csv"

    existing_rows = _assert_compatible_outdir(
        runs_path, exp_id, prov["experiment_hash"], resume
    )
    done = _done_keys(existing_rows) if resume else set()

    combos = [
        (m, s, a)
        for m in cfg["maps"]
        for s in cfg["seeds"]
        for a in cfg["algorithms"]
    ]
    pending_all = [c for c in combos if c not in done]
    pending = pending_all[:limit] if limit is not None else pending_all
    total = len(combos)
    n_done = len(done)
    t_start = time.perf_counter()

    print(
        f"{exp_id}: {n_done}/{total} ya listas, {len(pending)} pendientes "
        f"en esta invocación ({len(pending_all)} restantes, "
        f"experiment_hash {prov['experiment_hash']}, workers={workers})",
        flush=True,
    )

    # Guardar configuración sólo después de validar que el outdir es compatible.
    (outdir / "config.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lock_path = outdir / ".lock"
    new_runs = 0

    def _persist(res: dict) -> None:
        with open(lock_path, "a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                if _ensure_header(runs_path, RUN_FIELDS):
                    with open(runs_path, "w", newline="", encoding="utf-8") as f:
                        csv.DictWriter(f, fieldnames=RUN_FIELDS).writeheader()
                with open(runs_path, "a", newline="", encoding="utf-8") as f:
                    csv.DictWriter(f, fieldnames=RUN_FIELDS).writerow(res["row"])

                if _ensure_header(agents_path, AGENT_FIELDS):
                    with open(agents_path, "w", newline="", encoding="utf-8") as f:
                        csv.DictWriter(f, fieldnames=AGENT_FIELDS).writeheader()
                with open(agents_path, "a", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=AGENT_FIELDS)
                    for a in res["agents"]:
                        w.writerow(
                            {
                                "experiment_id": exp_id,
                                "algorithm": res["algorithm"],
                                "map_id": res["map_id"],
                                "seed": res["seed"],
                                "config_hash": prov["config_hash"],
                                "code_hash": prov["code_hash"],
                                "maps_hash": prov["maps_hash"],
                                "experiment_hash": prov["experiment_hash"],
                                **a,
                            }
                        )
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    # Estadísticas de runtime para ETA. Se alimentan de corridas ya existentes
    # y de las que terminan en esta invocación.
    runtime_sum: dict[tuple[str, str], float] = defaultdict(float)
    runtime_n: dict[tuple[str, str], int] = defaultdict(int)
    algo_sum: dict[str, float] = defaultdict(float)
    algo_n: dict[str, int] = defaultdict(int)
    global_sum = 0.0
    global_n = 0

    for row in existing_rows:
        try:
            dur = float(row["total_runtime"])
        except (KeyError, TypeError, ValueError):
            continue
        key = (row["map_id"], row["algorithm"])
        runtime_sum[key] += dur
        runtime_n[key] += 1
        algo_sum[row["algorithm"]] += dur
        algo_n[row["algorithm"]] += 1
        global_sum += dur
        global_n += 1

    remaining = Counter((m, a) for m, _s, a in pending)
    completed = n_done

    def _estimate_eta() -> float | None:
        nonlocal global_sum, global_n
        if not remaining or sum(remaining.values()) == 0:
            return 0.0
        if global_n == 0:
            return None
        global_mean = global_sum / global_n
        cpu_seconds = 0.0
        for key, count in remaining.items():
            if count <= 0:
                continue
            mid, algo = key
            if runtime_n[key]:
                est = runtime_sum[key] / runtime_n[key]
            elif algo_n[algo]:
                est = algo_sum[algo] / algo_n[algo]
            else:
                est = global_mean
            cpu_seconds += count * est
        return cpu_seconds / max(1, workers)

    def _report(res: dict) -> None:
        nonlocal completed, global_sum, global_n
        elapsed = time.perf_counter() - t_start
        completed += 1
        key = (res["map_id"], res["algorithm"])
        remaining[key] -= 1
        dur = float(res["duration"])
        runtime_sum[key] += dur
        runtime_n[key] += 1
        algo_sum[res["algorithm"]] += dur
        algo_n[res["algorithm"]] += 1
        global_sum += dur
        global_n += 1
        eta = _estimate_eta()
        key_mean = runtime_sum[key] / runtime_n[key]
        print(
            f"[{completed}/{total}] {res['map_id']}/{res['algorithm']}/"
            f"{res['seed']}: evac={res['evacuated']} clear={res['clearance']} "
            f"run={dur:.2f}s mean[{res['map_id']}/{res['algorithm']}]="
            f"{key_mean:.2f}s elapsed={_hms(elapsed)} ETA~{_hms(eta)}",
            flush=True,
        )

    if workers <= 1:
        for mid, seed, algo in pending:
            res = run_one(cfg, prov, exp_id, mid, seed, algo)
            _persist(res)
            new_runs += 1
            _report(res)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [
                ex.submit(run_one, cfg, prov, exp_id, mid, seed, algo)
                for mid, seed, algo in pending
            ]
            for fut in as_completed(futs):
                res = fut.result()
                _persist(res)
                new_runs += 1
                _report(res)

    manifest = {
        "experiment_id": exp_id,
        **prov,
        "expected_runs": total,
        "completed_runs": n_done + new_runs,
        "new_runs_this_invocation": new_runs,
        "workers": workers,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    try:
        os.remove(lock_path)
    except OSError:
        pass
    return outdir
