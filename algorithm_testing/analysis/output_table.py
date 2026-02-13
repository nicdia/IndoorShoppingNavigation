# analysis/output_table.py
from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from .benchmark import run_experiments


def save_table_as_image(
    df: pd.DataFrame,
    filename: str,
) -> None:
    cols_for_plot = [
        "scenario",
        "algorithm_setup",
        "algorithm",
        "n_items",
        "n_checkouts",
        "runtime_seconds",
        "distance",
        "turns",
        "walk_length",
    ]

    cols_for_plot = [c for c in cols_for_plot if c in df.columns]
    plot_df = df[cols_for_plot].copy()

    n_rows, n_cols = plot_df.shape
    fig_width = max(10, n_cols * 1.8)
    fig_height = max(3, n_rows * 0.6)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=plot_df.values,
        colLabels=plot_df.columns,
        rowLabels=df.index,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.2, 1.3)

    plt.tight_layout()
    fig.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = run_experiments()

    print("\n=== Algorithm Comparison (Routing Table) ===\n")
    with pd.option_context("display.max_columns", None, "display.width", 180):
        print(df)

    # analysis_dir = algorithm_testing/analysis
    analysis_dir = Path(__file__).resolve().parent
    # algo_root = algorithm_testing
    algo_root = analysis_dir.parent

    # Goal: algorithm_testing/analysis_output/output_table_results
    out_dir = algo_root / "analysis_output" / "output_table_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "routing_table.csv"
    png_path = out_dir / "routing_table.png"

    df.to_csv(csv_path)
    print(f"CSV saved as: {csv_path}")

    save_table_as_image(df, filename=str(png_path))
    print(f"table saved as: {png_path}")


if __name__ == "__main__":
    main()