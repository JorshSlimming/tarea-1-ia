"""Análisis de resultados por (mapa, algoritmo).

Antes de resumir, V2 comprueba que `runs.csv` contiene un único
`experiment_hash`; así no se mezclan accidentalmente experimentos distintos.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_runs(outdir: str | Path) -> pd.DataFrame:
    runs = pd.read_csv(Path(outdir) / "runs.csv")
    if "experiment_hash" not in runs.columns:
        raise ValueError(
            "runs.csv no contiene experiment_hash (formato v1). "
            "Analízalo con el código v1 o migra explícitamente los datos."
        )
    hashes = runs["experiment_hash"].dropna().astype(str).unique()
    if len(hashes) != 1:
        raise ValueError(
            f"runs.csv mezcla {len(hashes)} experiment_hash distintos: {hashes.tolist()}"
        )
    return runs


def summarize(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mid, algo), g in runs.groupby(["map_id", "algorithm"]):
        clear = g["clearance_turn"].dropna()
        rows.append(
            {
                "map_id": mid,
                "algorithm": algo,
                "n": len(g),
                "n_initial_mean": g["n_initial"].mean(),
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
                "generated_mean": g["generated_nodes"].mean(),
                "search_rt_mean": g["search_runtime"].mean(),
                "total_rt_mean": g["total_runtime"].mean(),
                "ga_generations_mean": g["ga_generations"].mean(),
                "ga_evaluations_mean": g["ga_evaluations"].mean(),
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values(["map_id", "algorithm"])
        .reset_index(drop=True)
    )


def write_summary(outdir: str | Path) -> Path:
    outdir = Path(outdir)
    summary = summarize(load_runs(outdir))
    path = outdir / "summary.csv"
    summary.to_csv(path, index=False)
    return path


def _plots_dir(outdir: str | Path) -> Path:
    path = Path(outdir) / "plots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def plot_survival(summary: pd.DataFrame, outdir: str | Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ax, mid in zip(axes, sorted(summary["map_id"].unique())):
        sub = summary[summary["map_id"] == mid]
        ax.bar(
            sub["algorithm"], sub["surv_mean"], yerr=sub["surv_std"], capsize=3
        )
        ax.set_title(mid)
        ax.set_ylim(0, 1.05)
        ax.tick_params(axis="x", rotation=30)
    fig.suptitle("Supervivencia media ± std por mapa/algoritmo")
    fig.tight_layout()
    path = _plots_dir(outdir) / "survival.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_clearance(summary: pd.DataFrame, outdir: str | Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ax, mid in zip(axes, sorted(summary["map_id"].unique())):
        sub = summary[summary["map_id"] == mid]
        ax.bar(
            sub["algorithm"], sub["clear_mean"], yerr=sub["clear_std"], capsize=3
        )
        ax.set_title(mid)
        ax.tick_params(axis="x", rotation=30)
    fig.suptitle("Clearance time medio ± std por mapa/algoritmo")
    fig.tight_layout()
    path = _plots_dir(outdir) / "clearance.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_outcomes(summary: pd.DataFrame, outdir: str | Path) -> Path:
    """Promedio de evacuados, muertos y atrapados por corrida."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, mid in zip(axes, sorted(summary["map_id"].unique())):
        sub = summary[summary["map_id"] == mid].reset_index(drop=True)
        x = np.arange(len(sub))
        evacuated = sub["surv_mean"] * sub["n_initial_mean"]
        ax.bar(x, evacuated, label="evacuados")
        ax.bar(x, sub["dead_mean"], bottom=evacuated, label="muertos")
        ax.bar(
            x,
            sub["trapped_mean"],
            bottom=evacuated + sub["dead_mean"],
            label="atrapados",
        )
        ax.set_xticks(x, sub["algorithm"], rotation=30)
        ax.set_title(mid)
    axes[0].set_ylabel("agentes promedio por corrida")
    axes[-1].legend(loc="best")
    fig.suptitle("Resultados finales promedio")
    fig.tight_layout()
    path = _plots_dir(outdir) / "outcomes.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_congestion(summary: pd.DataFrame, outdir: str | Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=False)
    for ax, mid in zip(axes, sorted(summary["map_id"].unique())):
        sub = summary[summary["map_id"] == mid]
        ax.bar(sub["algorithm"], sub["cong_waits_mean"])
        ax.set_title(mid)
        ax.tick_params(axis="x", rotation=30)
    fig.suptitle("Esperas por congestión promedio")
    fig.tight_layout()
    path = _plots_dir(outdir) / "congestion_waits.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
