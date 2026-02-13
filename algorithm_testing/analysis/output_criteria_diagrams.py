"""
Generates comparison diagrams for the three evaluation dimensions of the routing benchmark:
    - Shortest_Distance   → distance
    - Few_Turns           → turns
    - Runtime             → runtime_seconds

Workflow:

1) run_experiments() provides raw metrics for each combination of
   (scenario × algorithm), including:
       distance, turns, runtime_seconds.

2) These raw data are stored completely
   (criteria_raw_metrics_per_setup.csv) in order to keep all scenarios
   individually traceable.

3) Afterwards, the metrics are averaged PER ALGORITHM across all scenarios,
   resulting in a single absolute value per algorithm for each
   evaluation dimension.  
   Result: criteria_metrics_per_algorithm.csv

4) For each of the three categories, a bar chart is generated:
       - Shortest_Distance → distance
       - Few_Turns         → turns
       - Runtime           → runtime_seconds

   These diagrams visualize absolute performance differences
   (in contrast to the heatmap, which shows normalized scores).

Goal:
A clear, cross-scenario comparison of the routing algorithms across
the three main benchmark categories.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd

from .benchmark import run_experiments


CATEGORY_METRICS: Dict[str, List[str]] = {
    "Comparison_of_Distances": ["distance"],
    "Comparison_of_Turns": ["turns"],
    "Comparison_of_Runtime": ["runtime_seconds"],
}

CATEGORY_COLORS: Dict[str, str] = {
    "Comparison_of_Distances": "#2ca02c",   # green
    "Comparison_of_Turns": "#ff7f0e",       # orange
    "Comparison_of_Runtime": "#1f77b4",     # blue
}

Y_LABELS: Dict[str, str] = {
    "distance": "Overall distance (m, average)",
    "turns": "Number of Turns (average)",
    "runtime_seconds": "Runtime (s, average)",
}


def plot_metric_bar(
    df: pd.DataFrame,
    metric: str,
    category: str,
    color: str,
    out_dir: Path,
) -> None:
    """
    Generates a bar chart with absolute values ​​of a metric,
    aggregated per algorithm (averaged across all scenarios).
    """
    if metric not in df.columns:
        return

    values = df[metric]
    algos = df.index

    fig, ax = plt.subplots(figsize=(8, 5))

    x_pos = range(len(algos))
    bars = ax.bar(x_pos, values.values, color=color)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(algos, rotation=45, ha="right", fontsize=9)

    y_label = Y_LABELS.get(metric, metric)
    ax.set_ylabel(y_label, fontsize=11)

    ax.set_title(f"{category}", fontsize=14)

    for rect, value in zip(bars, values.values):
        ax.text(
            rect.get_x() + rect.get_width() / 2.0,
            rect.get_height(),
            f"{value:.4g}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    plt.tight_layout()
    filename = f"{category}.png"
    fig.savefig(out_dir / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"image saved as: {out_dir / filename}")


def main() -> None:
    df = run_experiments()

    analysis_dir = Path(__file__).resolve().parent
    algo_root = analysis_dir.parent
    out_dir = algo_root / "analysis_output" / "output_criteria_diagram_results" / "output_criteria_diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_csv = out_dir / "criteria_raw_metrics_per_setup.csv"
    df.to_csv(raw_csv)
    print(f"metrics saved as: {raw_csv}")

    agg = (
        df.groupby("algorithm_setup")[["runtime_seconds", "distance", "turns"]]
        .mean()
        .sort_index()
    )

    agg_csv = out_dir / "criteria_metrics_per_algorithm.csv"
    agg.to_csv(agg_csv)
    print(f"Aggregated metrics (per algorithm) stored: {agg_csv}")

    # Diagramme erzeugen
    for category, metrics in CATEGORY_METRICS.items():
        color = CATEGORY_COLORS.get(category, "#333333")

        for metric in metrics:
            plot_metric_bar(
                df=agg,
                metric=metric,
                category=category,
                color=color,
                out_dir=out_dir,
            )


if __name__ == "__main__":
    main()