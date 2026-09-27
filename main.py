"""CLI del simulador: `run` (una corrida) y `benchmark` (lote con resume)."""

from __future__ import annotations

import argparse
import sys

from src.domain.map import load_map
from src.experiment.benchmark import build_planner, run_benchmark
from src.experiment.config import config_hash, load_config, provenance
from src.simulation.engine import SimulationEngine
from src.simulation.scenario import build_scenario


def cmd_run(args) -> int:
    sm = load_map(f"maps/{args.map}.txt")
    sc = build_scenario(sm, args.seed, num_agents=args.agents,
                        k=args.k, p=args.p, max_turns=args.max_turns)
    planner = build_planner(args.algorithm, {"ga": {}}, sc.ga_seed)
    m = SimulationEngine(sc, planner, max_turns=args.max_turns,
                         algorithm_name=args.algorithm).run()
    print(f"{args.map}/{args.algorithm}/{args.seed}: "
          f"evac={m.evacuated}/{m.n_initial} dead={m.dead} "
          f"trapped={m.trapped} clear={m.clearance_turn} "
          f"turns={m.turns} runtime={m.total_runtime:.2f}s")
    return 0


def cmd_benchmark(args) -> int:
    run_benchmark(args.config, resume=not args.no_resume, limit=args.limit,
                  workers=args.workers)
    return 0


def cmd_analyze(args) -> int:
    from src.analysis.summary import (
        load_runs,
        plot_clearance,
        plot_congestion,
        plot_outcomes,
        plot_survival,
        summarize,
        write_summary,
    )

    runs = load_runs(args.outdir)
    summary = summarize(runs)
    write_summary(args.outdir)
    print(summary.to_string(index=False))
    print(
        "plots:",
        plot_survival(summary, args.outdir),
        plot_clearance(summary, args.outdir),
        plot_outcomes(summary, args.outdir),
        plot_congestion(summary, args.outdir),
    )
    return 0


def cmd_hash(args) -> int:
    cfg = load_config(args.config)
    print(provenance(cfg))
    return 0

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tarea1",
                                 description="Escape de la Torre (Tarea 1 IA)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="una simulación")
    r.add_argument("--map", default="map1")
    r.add_argument("--algorithm", default="bfs",
                   choices=["bfs", "ucs", "greedy", "astar", "ga"])
    r.add_argument("--seed", type=int, default=10000)
    r.add_argument("--agents", type=int, default=30)
    r.add_argument("--k", type=int, default=3)
    r.add_argument("--p", type=float, default=0.3)
    r.add_argument("--max-turns", type=int, default=200)
    r.set_defaults(func=cmd_run)
    b = sub.add_parser("benchmark", help="lote con checkpoints y resume")
    b.add_argument("--config", default="config/pilot.json")
    b.add_argument("--no-resume", action="store_true")
    b.add_argument("--limit", type=int, default=None)
    b.add_argument("--workers", type=int, default=1)
    b.set_defaults(func=cmd_benchmark)
    a = sub.add_parser("analyze", help="summary.csv + gráficos desde runs.csv")
    a.add_argument("--outdir", default="results/final_v1")
    a.set_defaults(func=cmd_analyze)
    h = sub.add_parser("hash", help="hashes de config/código/mapas/experimento")
    h.add_argument("--config", default="config/pilot.json")
    h.set_defaults(func=cmd_hash)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
