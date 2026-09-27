"""Benchmark runner: escenarios emparejados, checkpoints, resume, hash, ETA.

Uso serial (1 worker):
    run_benchmark(config_path)
Uso paralelo (N workers, mismo config):
    run_benchmark(config_path, workers=N)  o  main.py benchmark --workers N
    Corte limpio: Ctrl-C / kill detiene tras la corrida en curso; reejecutar
    retoma (clave experiment_id, config_hash, mapa, seed, algoritmo).

- Escenario (mapa, seed) generado una vez -> cinco algoritmos (protocolo).
- Orden: mapa -> seed -> algoritmo.
- Persistencia por corrida: flush inmediato (runs.csv, agents.csv) con
  lock inter-proceso (fcntl) para escritura paralela segura.
- Resume: clave (experiment_id, config_hash, map_id, seed, algorithm).
- results/<exp>/config.json, manifest.json, runs.csv, agents.csv.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from src.domain.map import load_map
from src.experiment.config import config_hash, load_config
from src.experiment.metrics import RunMetrics
from src.planners.astar import AStarPlanner
from src.planners.bfs import BFSPlanner
from src.planners.genetic import GAConfig, GeneticPlanner
from src.planners.greedy import GreedyPlanner
from src.planners.uniform_cost import UCSPlanner
from src.simulation.engine import SimulationEngine
from src.simulation.scenario import build_scenario

RUN_FIELDS = ["experiment_id", *[k for k in RunMetrics(
    algorithm="", map_id="", seed=0).run_row()]]
AGENT_FIELDS = ["experiment_id", "algorithm", "map_id", "seed", "config_hash",
                "agent_id", "status", "status_reason", "evacuation_turn",
                "death_turn", "voluntary_waits", "congestion_waits", "replans"]


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
        return GeneticPlanner(GAConfig(
            horizon=g.get("horizon", 60),
            population=g.get("population", 30),
            generations=g.get("generations", 20),
            tournament=g.get("tournament", 3),
            crossover_p=g.get("crossover_p", 0.8),
            mutation_p=g.get("mutation_p", 1 / 60),
            elite=g.get("elite", 2),
            stagnation=g.get("stagnation", 6),
        ), ga_seed=ga_seed)
    raise ValueError(f"algoritmo desconocido: {name}")


def _done_keys(runs_path: Path, experiment_id: str, chash: str) -> set:
    done = set()
    if not runs_path.exists():
        return done
    with open(runs_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("experiment_id") == experiment_id and \
                    row.get("config_hash") == chash:
                done.add((row["map_id"], int(row["seed"]), row["algorithm"]))
    return done


def _ensure_header(path: Path, fields: list[str]) -> bool:
    """True si el archivo es nuevo (hay que escribir header)."""
    if path.exists() and path.stat().st_size > 0:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    return True


def run_benchmark(config_path: str, resume: bool = True,
                  limit: int | None = None, workers: int = 1) -> Path:
    import os
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures import as_completed

    from .worker import run_one

    cfg = load_config(config_path)
    chash = config_hash(cfg)
    exp_id = cfg.get("experiment_id", "exp")
    outdir = Path(cfg.get("outdir", f"results/{exp_id}"))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "config.json").write_text(json.dumps(cfg, indent=2),
                                        encoding="utf-8")
    runs_path, agents_path = outdir / "runs.csv", outdir / "agents.csv"
    done = _done_keys(runs_path, exp_id, chash) if resume else set()
    combos = [(m, s, a) for m in cfg["maps"] for s in cfg["seeds"]
              for a in cfg["algorithms"]]
    pending_all = [c for c in combos if c not in done]
    pending = pending_all[:limit] if limit is not None else pending_all
    total, n_done, t_start = len(combos), len(done), time.perf_counter()
    print(f"{exp_id}: {n_done}/{total} ya listas, "
          f"{len(pending)} pendientes en esta invocación "
          f"({len(pending_all)} restantes, hash {chash}, workers={workers})",
          flush=True)
    lock_path = outdir / ".lock"
    new_runs = 0

    def _persist(res: dict) -> None:
        import fcntl

        with open(lock_path, "a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                if _ensure_header(runs_path, RUN_FIELDS):
                    with open(runs_path, "w", newline="",
                              encoding="utf-8") as f:
                        csv.DictWriter(f, fieldnames=RUN_FIELDS).writeheader()
                with open(runs_path, "a", newline="", encoding="utf-8") as f:
                    csv.DictWriter(f, fieldnames=RUN_FIELDS).writerow(res["row"])
                if _ensure_header(agents_path, AGENT_FIELDS):
                    with open(agents_path, "w", newline="",
                              encoding="utf-8") as f:
                        csv.DictWriter(f, fieldnames=AGENT_FIELDS).writeheader()
                with open(agents_path, "a", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=AGENT_FIELDS)
                    for a in res["agents"]:
                        w.writerow({"experiment_id": exp_id,
                                    "algorithm": res["algorithm"],
                                    "map_id": res["map_id"],
                                    "seed": res["seed"],
                                    "config_hash": chash, **a})
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    completed = [n_done]  # mutable, compartido por reportes concurrentes

    def _report(res: dict) -> None:
        elapsed = time.perf_counter() - t_start
        completed[0] += 1
        done_n = completed[0]
        eta = elapsed / done_n * (total - done_n) if done_n else 0
        print(f"[{done_n}/{total}] {res['map_id']}/{res['algorithm']}/"
              f"{res['seed']}: evac={res['evacuated']} "
              f"clear={res['clearance']} {res['duration']:.1f}s "
              f"(elapsed {elapsed:.0f}s, ETA {eta:.0f}s)", flush=True)

    # Corte limpio: KeyboardInterrupt/kill termina el pool; lo ya persistido
    # queda; reejecutar retoma por clave (experiment_id, hash, mapa, seed, algo).
    if workers <= 1:
        for (mid, seed, algo) in pending:
            res = run_one(cfg, chash, exp_id, mid, seed, algo)
            _persist(res)
            new_runs += 1
            _report(res)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(run_one, cfg, chash, exp_id, mid, seed, algo)
                    for (mid, seed, algo) in pending]
            for fut in as_completed(futs):
                res = fut.result()
                _persist(res)
                new_runs += 1
                _report(res)
    manifest = {
        "experiment_id": exp_id, "config_hash": chash,
        "expected_runs": total,
        "completed_runs": n_done + new_runs,
        "new_runs_this_invocation": new_runs,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                          encoding="utf-8")
    try:
        os.remove(lock_path)
    except OSError:
        pass
    return outdir
