# algorithm_testing/analysis/output_heatmap_summary.py
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Evaluation profiles for indoor shopping navigation
# Expected columns:
#   Shortest_Path, Fewest_Turns, Runtime

PROFILES = [
    # 1) Balanced — no clear preference, all criteria equally important
    {
        "name": "Balanced",
        "category_weights": {
            "Shortest_Path": 1.0 / 3.0,
            "Fewest_Turns": 1.0 / 3.0,
            "Runtime": 1.0 / 3.0,
        },
    },

    # 2) Quick Buy — user wants immediate results, computation time dominates
    {
        "name": "Quick_Buy",
        "category_weights": {
            "Shortest_Path": 0.25,
            "Fewest_Turns": 0.15,
            "Runtime": 0.60,
        },
    },

    # 3) Regular Shopping — realistic everyday shopping behavior
    {
        "name": "Regular_Shopping",
        "category_weights": {
            "Shortest_Path": 0.40,
            "Fewest_Turns": 0.30,
            "Runtime": 0.30,
        },
    },

    # 4) Comfort Navigation — minimize cognitive load (few turns preferred)
    {
        "name": "Comfort_Navigation",
        "category_weights": {
            "Shortest_Path": 0.25,
            "Fewest_Turns": 0.60,
            "Runtime": 0.15,
        },
    },
]


def _weighted_overall(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    w = pd.Series({c: weights.get(c, 0.0) for c in df.columns})
    if w.sum() == 0:
        return pd.Series(np.nan, index=df.index)
    return (df * w).sum(axis=1) / w.sum()


def _save_summary_table(df: pd.DataFrame, out_png: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13.33, 7.5))
    ax.axis("off")

    ax.text(
        0.5, 0.92, title,
        ha="center", va="center",
        fontsize=26, fontweight="bold",
        transform=ax.transAxes,
    )

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        colLoc="center",
        bbox=[0.06, 0.2, 0.88, 0.65],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(18)

    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#222222")
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#F5F6F7" if r % 2 else "white")

    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    base_dir = project_root / "analysis_output" / "output_heatmap_results"

    csv_path = base_dir / "heatmap_index_per_algorithm.csv"
    df = pd.read_csv(csv_path, index_col=0)

    numeric_df = df.drop(columns=["Overall"], errors="ignore")

    rows = []

    for profile in PROFILES:
        name = profile["name"]
        weights = profile["category_weights"]

        scores = _weighted_overall(numeric_df, weights)
        winner = scores.idxmax()
        score = float(scores.loc[winner])

        rows.append(
            {
                "Profile": name,
                "Winner": winner,
                "Score": round(score, 2),
            }
        )

    result_df = pd.DataFrame(rows).sort_values("Score", ascending=False)

    result_df.to_csv(base_dir / "overall_winners_by_profile.csv", index=False)
    _save_summary_table(
        result_df,
        base_dir / "overall_winners_by_profile.png",
        "Overall Algorithm Winners by Profile",
    )


if __name__ == "__main__":
    main()