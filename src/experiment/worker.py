"""Worker de benchmark: ejecuta UNA corrida en un proceso independiente."""

from __future__ import annotations

import time


def run_one(
    cfg: dict,
    prov: dict,
    exp_id: str,
    map_id: str,
    seed: int,
    algo: str,
) -> dict:
    from src.domain.map import load_map
    from src.experiment.benchmark import build_planner
    from src.simulation.engine import SimulationEngine
    from src.simulation.scenario import build_scenario

    t0 = time.perf_counter()
    smap = load_map(f"maps/{map_id}.txt")
    sc = build_scenario(
        smap,
        seed,
        num_agents=cfg.get("agents", 30),
        k=cfg["fire"]["k"],
        p=cfg["fire"]["p"],
        max_turns=cfg.get("max_turns", 200),
    )
    planner = build_planner(algo, cfg, sc.ga_seed)
    m = SimulationEngine(
        sc,
        planner,
        max_turns=cfg.get("max_turns", 200),
        lam=cfg.get("lam", 4.0),
        algorithm_name=algo,
        config_hash=prov["config_hash"],
        code_hash=prov["code_hash"],
        maps_hash=prov["maps_hash"],
        experiment_hash=prov["experiment_hash"],
    ).run()
    return {
        "row": {"experiment_id": exp_id, **m.run_row()},
        "agents": m.per_agent,
        "map_id": map_id,
        "seed": seed,
        "algorithm": algo,
        "evacuated": m.evacuated,
        "clearance": m.clearance_turn,
        "duration": time.perf_counter() - t0,
    }
