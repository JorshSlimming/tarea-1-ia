"""Tests F12: benchmark resume/hash (benchmark_y_persistencia.md)."""

import csv
import json

from src.experiment.benchmark import run_benchmark
from src.experiment.config import config_hash, load_config


def _mini_config(tmp_path):
    cfg = {
        "experiment_id": "test_mini",
        "maps": ["map3"],
        "seeds": [10000, 10001],
        "algorithms": ["bfs", "greedy"],
        "agents": 4,
        "max_turns": 30,
        "lam": 4.0,
        "fire": {"k": 99, "p": 0.0},
        "ga": {},
        "outdir": str(tmp_path / "mini"),
    }
    p = tmp_path / "mini.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return str(p)


def test_benchmark_completes_and_resumes(tmp_path):
    cfg_path = _mini_config(tmp_path)
    out = run_benchmark(cfg_path, limit=2)
    with open(out / "runs.csv", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 2
    # Segunda invocación con límite mayor: retoma sin duplicar.
    run_benchmark(cfg_path, limit=10)
    with open(out / "runs.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4  # 1 mapa x 2 seeds x 2 algos
    keys = [(r["map_id"], r["seed"], r["algorithm"]) for r in rows]
    assert len(set(keys)) == 4
    with open(out / "agents.csv", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 4 * 4
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["completed_runs"] == 4
    assert manifest["expected_runs"] == 4


def test_config_hash_stable_and_sensitive(tmp_path):
    cfg_path = _mini_config(tmp_path)
    cfg = load_config(cfg_path)
    assert config_hash(cfg) == config_hash(load_config(cfg_path))
    cfg["fire"]["p"] = 0.5
    assert config_hash(cfg) != config_hash(load_config(cfg_path))
