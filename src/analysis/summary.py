"""Análisis: summary por (mapa, algoritmo) + gráficos (metricas_y_telemetria.md).

- Supervivencia: media/std/min/max + n.
- Clearance: media/std/min/max + n_con_evacuados (NaN si cero evacuados).
- Secundarias: muertos/atrapados, mean/median evac, waits, replans,
  nodos, runtime, GA.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_runs(outdir: str | Path) -> pd.DataFrame:
    return pd.read_csv(Path(outdir) / "runs.csv")


def summarize(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mid, algo), g in runs.groupby(["map_id", "algorithm"]):
        clear = g["clearance_turn"].dropna()
        rows.append({
            "map_id": mid,
            "algorithm": algo,
            "n": len(g),
            "surv_mean": g["survival_rate"].mean(),
            "surv_std": g["survival_rate"].std(ddof=0),
            "surv_min": g["survival_rate"].min(),
            "surv_max": g["survival_rate"].max(),
            "clear_n": len(clear),
            "clear_mean": clear.mean() if len(clear) else float("nan"),
            "clear_std": clear.std(ddof=0) if len(clear) else float("nan"),
            "clear_min": clear.min() if len(clear) else float("nan"),
            "clear_max": clear.max() if len(clear) else float("nan"),
            "dead_mean": g["dead"].mean(),
            "trapped_mean": g["trapped"].mean(),
            "mean_evac_mean": g["mean_evac_turn"].mean(),
            "vol_waits_mean": g["voluntary_waits"].mean(),
            "cong_waits_mean": g["congestion_waits"].mean(),
            "replans_mean": g["replans"].mean(),
            "expanded_mean": g["expanded_nodes"].mean(),
            "search_rt_mean": g["search_runtime"].mean(),
            "total_rt_mean": g["total_runtime"].mean(),
        })
    return pd.DataFrame(rows).sort_values(["map_id", "algorithm"]).reset_index(drop=True)


def write_summary(outdir: str | Path) -> Path:
    outdir = Path(outdir)
    summary = summarize(load_runs(outdir))
    path = outdir / "summary.csv"
    summary.to_csv(path, index=False)
    return path


def plot_survival(summary: pd.DataFrame, outdir: str | Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    outdir = Path(outdir) / "plots"
    outdir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ax, mid in zip(axes, sorted(summary["map_id"].unique())):
        sub = summary[summary["map_id"] == mid]
        ax.bar(sub["algorithm"], sub["surv_mean"], yerr=sub["surv_std"],
               capsize=3)
        ax.set_title(mid)
        ax.set_ylim(0, 1.05)
        ax.tick_params(axis="x", rotation=30)
    fig.suptitle("Supervivencia media ± std por mapa/algoritmo")
    fig.tight_layout()
    path = outdir / "survival.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_clearance(summary: pd.DataFrame, outdir: str | Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    outdir = Path(outdir) / "plots"
    outdir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ax, mid in zip(axes, sorted(summary["map_id"].unique())):
        sub = summary[summary["map_id"] == mid]
        ax.bar(sub["algorithm"], sub["clear_mean"], yerr=sub["clear_std"],
               capsize=3)
        ax.set_title(mid)
        ax.tick_params(axis="x", rotation=30)
    fig.suptitle("Clearance time medio ± std por mapa/algoritmo")
    fig.tight_layout()
    path = outdir / "clearance.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
