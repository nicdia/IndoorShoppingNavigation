# algorithm_testing/analysis/output_heatmap.py
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .benchmark import run_experiments


def _normalize_series(s: pd.Series, invert: bool = False) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    min_val = s.min()
    max_val = s.max()

    if pd.isna(min_val) or pd.isna(max_val):
        return pd.Series(np.nan, index=s.index, dtype=float)

    if max_val == min_val:
        return pd.Series(100.0, index=s.index, dtype=float)

    norm = (s - min_val) / (max_val - min_val)

    if invert:
        norm = 1.0 - norm

    return (norm * 100.0).astype(float)


def build_indices(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:

    required_cols = {"scenario", "algorithm_setup", "distance", "turns", "runtime_seconds"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in df: {missing}")

    rows = []

    for scen, scen_df in df.groupby("scenario"):
        idx = scen_df.index

        dist_score = _normalize_series(scen_df["distance"], invert=True)
        turns_score = _normalize_series(scen_df["turns"], invert=True)
        runtime_score = _normalize_series(scen_df["runtime_seconds"], invert=True)

        comp_df = pd.concat(
            [dist_score, turns_score, runtime_score],
            axis=1,
        )
        overall = comp_df.mean(axis=1)

        tmp = pd.DataFrame(
            {
                "scenario": scen,
                "algorithm_setup": scen_df["algorithm_setup"],
                "Shortest_Path": dist_score,
                "Fewest_Turns": turns_score,
                "Runtime": runtime_score,
                "Overall": overall,
            },
            index=idx,
        )
        rows.append(tmp)

    per_setup_index = pd.concat(rows).sort_index()

    per_algorithm_index = (
        per_setup_index
        .groupby("algorithm_setup")[["Shortest_Path", "Fewest_Turns", "Runtime", "Overall"]]
        .mean()
        .sort_index()
    )

    return per_setup_index, per_algorithm_index


def save_heatmap(index_df: pd.DataFrame, filename: Path) -> None:
    filename = Path(filename)
    filename.parent.mkdir(parents=True, exist_ok=True)

    data = index_df.values.astype(float)
    mask = np.isnan(data)
    data_filled = np.where(mask, 0.0, data)

    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("white_to_green", ["#ffffff", "#007f00"])

    fig, ax = plt.subplots(
        figsize=(1.3 * data.shape[1] + 4, 0.6 * data.shape[0] + 3)
    )
    im = ax.imshow(data_filled, aspect="auto", cmap=cmap, vmin=0, vmax=100)

    ax.set_xticks(np.arange(index_df.shape[1]))
    ax.set_yticks(np.arange(index_df.shape[0]))
    ax.set_xticklabels(index_df.columns, rotation=45, ha="right", fontsize=10)
    ax.set_yticklabels(index_df.index, fontsize=10)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = "" if mask[i, j] else f"{data[i, j]:.1f}"
            ax.text(j, i, val, ha="center", va="center", fontsize=9, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Score (0–100)", rotation=90)

    ax.set_title("Routing Algorithm Performance (aggregated over scenarios)", fontsize=14)

    plt.tight_layout()
    fig.savefig(str(filename), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = run_experiments()
    per_setup_index, per_algorithm_index = build_indices(df)

    analysis_dir = Path(__file__).resolve().parent
    algo_root = analysis_dir.parent
    out_dir = algo_root / "analysis_output" / "output_heatmap_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    per_setup_index.to_csv(out_dir / "heatmap_index_per_setup.csv")
    per_algorithm_index.to_csv(out_dir / "heatmap_index_per_algorithm.csv")

    save_heatmap(
        per_algorithm_index,
        out_dir / "heatmap_index_per_algorithm.png",
    )


if __name__ == "__main__":
    main()