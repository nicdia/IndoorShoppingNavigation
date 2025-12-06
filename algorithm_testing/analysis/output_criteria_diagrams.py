"""
Erzeugt Vergleichsdiagramme für die drei Bewertungsdimensionen des Routing-Benchmarks:
    - Kuerzeste_Distanz   → distance
    - Wenig_Abbiegen      → turns
    - Laufzeit            → runtime_seconds

Ablauf:

1) run_experiments() liefert Rohmetriken für jede Kombination aus
   (Szenario × Algorithmus), u. a.:
       distance, turns, runtime_seconds.

2) Diese Rohdaten werden vollständig gespeichert
   (criteria_raw_metrics_per_setup.csv), um alle Szenarien einzeln
   nachvollziehbar zu halten.

3) Danach werden die Metriken PRO ALGORITHMUS über alle Szenarien gemittelt,
   sodass für jede Bewertungsdimension ein einziger absoluter Wert
   pro Algorithmus entsteht.  
   Ergebnis: criteria_metrics_per_algorithm.csv

4) Für jede der drei Kategorien wird ein Balkendiagramm erzeugt:
       - Kuerzeste_Distanz → distance
       - Wenig_Abbiegen    → turns
       - Laufzeit          → runtime_seconds

   Diese Diagramme visualisieren absolute Leistungsunterschiede
   (im Gegensatz zur Heatmap, die normalisierte Scores zeigt).

Ziel:
Ein klarer, szenarioübergreifender Vergleich der Routing-Algorithmen in den
drei Hauptkategorien des Benchmarks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd

from .benchmark import run_experiments


# Konsistente Kategorien wie im Heatmap-Skript
CATEGORY_METRICS: Dict[str, List[str]] = {
    "Kuerzeste_Distanz": ["distance"],
    "Wenig_Abbiegen": ["turns"],
    "Laufzeit": ["runtime_seconds"],
}

# Farben pro Kategorie
CATEGORY_COLORS: Dict[str, str] = {
    "Kuerzeste_Distanz": "#2ca02c",  # grün
    "Wenig_Abbiegen": "#ff7f0e",     # orange
    "Laufzeit": "#1f77b4",           # blau
}

# Achsenlabels
Y_LABELS: Dict[str, str] = {
    "distance": "Gesamtdistanz (Gewicht, gemittelt)",
    "turns": "Anzahl Abbiegen (gemittelt)",
    "runtime_seconds": "Laufzeit (Sekunden, gemittelt)",
}


def plot_metric_bar(
    df: pd.DataFrame,
    metric: str,
    category: str,
    color: str,
    out_dir: Path,
) -> None:
    """
    Erzeugt ein Balkendiagramm mit absoluten Werten einer Metrik,
    aggregiert pro Algorithmus (über alle Szenarien gemittelt).
    """
    if metric not in df.columns:
        return

    values = df[metric]
    algos = df.index

    fig, ax = plt.subplots(figsize=(8, 4))

    x_pos = range(len(algos))
    bars = ax.bar(x_pos, values.values, color=color)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(algos, rotation=45, ha="right", fontsize=9)

    y_label = Y_LABELS.get(metric, metric)
    ax.set_ylabel(y_label, fontsize=11)

    ax.set_title(f"{category}", fontsize=14)

    # Werte über Balken schreiben
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

    print(f"Diagramm gespeichert: {out_dir / filename}")


def main() -> None:
    df = run_experiments()

    # Basisordner
    analysis_dir = Path(__file__).resolve().parent
    algo_root = analysis_dir.parent
    out_dir = algo_root / "analysis_output" / "output_criteria_diagram_results" / "output_criteria_diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Rohdaten sichern
    raw_csv = out_dir / "criteria_raw_metrics_per_setup.csv"
    df.to_csv(raw_csv)
    print(f"Rohmetriken (pro Setup) gespeichert: {raw_csv}")

    # Aggregation pro Algorithmus
    agg = (
        df.groupby("algorithm_setup")[["runtime_seconds", "distance", "turns"]]
        .mean()
        .sort_index()
    )

    agg_csv = out_dir / "criteria_metrics_per_algorithm.csv"
    agg.to_csv(agg_csv)
    print(f"Aggregierte Metriken (pro Algorithmus) gespeichert: {agg_csv}")

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