# benchmark_items_compare.py
"""
Benchmark Script: Item-Based Scaling Comparison of Routing Algorithms

This script benchmarks multiple routing/pathfinding algorithms on the same graph while
varying the number of items (targets) to visit.

Workflow:
1) Load a GraphML graph and ensure each edge has a numeric 'weight'.
2) For each run:
   - Create a new random permutation of candidate item IDs from a configurable pool.
   - For each configured item count (e.g., 1..10), take a prefix of that permutation
     as the current item set.
   - Run every algorithm on the exact same item set (fair comparison).
3) Collect runtime measurements for each (algorithm, item_count, run).
4) Produce:
   - A log-log scaling plot with scatter points, mean curve, and std shading.
   - A CSV file containing the aggregated mean/std table (English headers).
   - A PNG image of the aggregated table (English headers).

Central configuration:
- CFG["SEED"]        : Reproducible randomness for item permutations
- CFG["RUNS"]        : Number of iterations per algorithm
- CFG["ITEM_COUNTS"] : Item counts to benchmark (x-axis)
- CFG["PLOT_FILENAME"]: Output plot filename (PNG)
- CFG["CSV_FILENAME"] : Output table filename (CSV)
- CFG["TABLE_PNG_FILENAME"]: Output table image filename (PNG)

All outputs are saved dynamically under:
<repo_root>/analysis_output/output_scaling_results/
(where <repo_root> is the parent directory of this script's folder).
"""

from __future__ import annotations

import os
from pathlib import Path
import random
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from ..criteria.metrics_wrapper import evaluate_all_criteria

from ..algorithms.nn_dijkstra import run_algorithm as nn_dijkstra
from ..algorithms.nn_a_star import run_algorithm as nn_a_star
from ..algorithms.EAMDSP import run_algorithm as EAMDSP
from ..algorithms.MDMSMD import run_algorithm as MDMSMD

from ..algorithms.bnb_dijkstra import run_algorithm as bnb_dijkstra
from ..algorithms.bnb_a_star import run_algorithm as bnb_a_star
from ..algorithms.bnb_a_star_modified_lowerbound import run_algorithm as bnb_a_star_modified_lowerbound
from ..algorithms.bnb_a_star_modified_lowerbound_preload_astar import (
    run_algorithm as bnb_a_star_modified_lowerbound_preload_astar,
)
from ..algorithms.bnb_a_star_modified_mstbound import run_algorithm as bnb_a_star_modified_mstbound

# =========================
# Central Benchmark Config
# =========================
CFG = {
    "SEED": 42,
    "RUNS": 10,
    "ITEM_COUNTS": list(range(1, 31)),
    "POOL_SIZE": 150,
    "EXCLUDED": {"14", "15", "21"},
    "GRAPH_PATH": "resources/graph.graphml",
    "ENTRY": "21",
    "CHECKOUTS": ["14", "15"],
    "TIME_LIMIT_SECONDS": 60.0, 
    "PLOT_FILENAME": "item_scaling.png",
    "CSV_FILENAME": "item_scaling.csv",
    "TABLE_PNG_FILENAME": "item_scaling_table.png",
}


def load_graph(path: str) -> nx.Graph:
    G = nx.read_graphml(path)
    for u, v, d in G.edges(data=True):
        d["weight"] = float(d.get("weight", d.get("length", 1.0)))
    return G


def compute_slope_loglog(x: np.ndarray, y: np.ndarray) -> float:
    logx = np.log10(x)
    logy = np.log10(y)
    k, _ = np.polyfit(logx, logy, 1)
    return float(k)


def save_table_as_image(df: pd.DataFrame, filename: str, title: str = "Aggregated Results") -> None:
    df_disp = df.copy()
    for col in df_disp.columns:
        if pd.api.types.is_float_dtype(df_disp[col]):
            df_disp[col] = df_disp[col].map(lambda x: f"{x:.6g}")

    fig, ax = plt.subplots(figsize=(12, max(3, 0.35 * len(df_disp) + 1.5)))
    ax.axis("off")
    ax.set_title(title, fontsize=12, pad=10)

    table = ax.table(
        cellText=df_disp.values,
        colLabels=df_disp.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.2)

    fig.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_items_scaling_with_errorbars(df: pd.DataFrame, item_counts: List[int], filename: str) -> None:
    agg = (
        df.groupby(["setup", "n_points"])
        .agg(
            runtime_mean=("runtime_seconds", "mean"),
            runtime_std=("runtime_seconds", "std"),
            num_samples=("runtime_seconds", "count"),
        )
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(14, 6))

    colors = [
        "#0072B2",
        "#E69F00",
        "#009E73",
        "#D55E00",
        "#CC79A7",
        "#F0E442",
        "#56B4E9",
        "#000000",
    ]

    setups = agg["setup"].dropna().unique().tolist()

    for idx, setup in enumerate(setups):
        sub = agg[agg["setup"] == setup].sort_values("n_points")
        x = sub["n_points"].to_numpy(dtype=float)
        y = sub["runtime_mean"].to_numpy(dtype=float)

        if len(x) == 0:
            continue

        color = colors[idx % len(colors)]

        if len(x) >= 2 and np.all(x > 0) and np.all(y > 0):
            k = compute_slope_loglog(x, y)
            label = f"{setup}  (k = {k:.2f})"
        else:
            label = f"{setup}  (k = n/a)"

        std = sub["runtime_std"].fillna(0.0).to_numpy(dtype=float)

        lower = np.maximum(y - std, 1e-8)
        upper = y + std

        yerr = np.vstack((y - lower, upper - y))

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            fmt="o-",
            color=color,
            linewidth=2,
            markersize=5,
            elinewidth=1,
            capsize=3,
            capthick=1,
            alpha=0.9,
            label=label,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")

    max_n = int(max(item_counts))

    ticks_small = list(range(1, min(16, max_n + 1)))
    ticks_large = list(range(20, max_n + 1, 10))
    xticks = sorted(set(ticks_small + ticks_large))

    ax.set_xticks(xticks)
    ax.set_xticklabels([str(t) for t in xticks])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{int(v)}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{v:g}"))

    ax.set_xlim(min(item_counts), max(item_counts))

    y_min = float(agg["runtime_mean"].min())
    y_max = float(agg["runtime_mean"].max())
    ax.set_ylim(y_min * 0.7, y_max * 1.3)

    ax.set_xlabel("Number of Nodes (log scale)", fontsize=12)
    ax.set_ylabel("Runtime (seconds, log scale)", fontsize=12)
    ax.set_title("Scaling (log-log): Runtime vs. Number of Nodes", fontsize=14)

    ax.grid(True, which="major", alpha=0.4)
    ax.grid(True, which="minor", alpha=0.15, linestyle=":")

    ax.legend(fontsize=9, title="Algorithms")

    out_dir = os.path.dirname(filename)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    fig.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Plot saved to: {filename}")


def run_item_benchmarks(
    G: nx.Graph,
    entry: str,
    checkouts: List[str],
    pool_size: int,
    excluded: set[str],
    item_counts: List[int],
    runs: int,
    algorithms: Dict[str, callable],
    seed: int,
    time_limit_seconds: float,
) -> Tuple[pd.DataFrame, Dict[str, dict], Dict[str, int | None]]:
    """
    Returns:
      df with columns: setup, n_points, runtime_seconds, run_idx
      last_logs: per setup the results dict of the last successful measurement it performed
                (usually max items, last run; but may be smaller if the algo stopped early)
      cutoff_n: per setup the first n where runtime exceeded time_limit_seconds (or None)
    """
    rng = random.Random(seed)

    valid_items = [str(i) for i in range(1, pool_size + 1) if str(i) not in excluded]
    if max(item_counts) > len(valid_items):
        raise ValueError("max(ITEM_COUNTS) is larger than the available item pool.")

    rows: List[dict] = []
    last_logs: Dict[str, dict] = {}

    active: Dict[str, bool] = {name: True for name in algorithms.keys()}
    cutoff_n: Dict[str, int | None] = {name: None for name in algorithms.keys()}

    for run_idx in range(runs):
    # run 1 does not affect run 2
        active = {name: True for name in algorithms.keys()}

        items_perm = valid_items[:]
        rng.shuffle(items_perm)
        prefixes = {n: items_perm[:n] for n in item_counts}

        for setup, algo_fn in algorithms.items():
            if not active[setup]:
                continue

            print(f"[Run {run_idx + 1}/{runs}] Running algorithm: {setup}")

            for n in item_counts:
                if not active[setup]:
                    break

                current_items = prefixes[n]

                results = evaluate_all_criteria(
                    algorithm_fn=algo_fn,
                    G=G,
                    entry=entry,
                    items=current_items,
                    checkouts=checkouts,
                    runtime_repeats=1,
                )

                t = float(results["runtime_seconds"])

                rows.append(
                    {
                        "setup": setup,
                        "algorithm": setup,
                        "n_points": int(n),
                        "runtime_seconds": t,
                        "run_idx": int(run_idx),
                    }
                )

                last_logs[setup] = results

                if t > time_limit_seconds:
                    cutoff_n[setup] = int(n)
                    active[setup] = False
                    print(
                        f"  -> Cutoff triggered for {setup} at n={n}: runtime={t:.3f}s "
                        f"(will skip n>{n} for this run only)"
                    )
                    break


    return pd.DataFrame(rows), last_logs, cutoff_n


def main() -> None:
    analysis_dir = Path(__file__).resolve().parent
    repo_root = analysis_dir.parent
    out_dir = repo_root / "analysis_output" / "output_scaling_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / CFG["CSV_FILENAME"]
    plot_png_path = out_dir / CFG["PLOT_FILENAME"]
    table_png_path = out_dir / CFG["TABLE_PNG_FILENAME"]

    G = load_graph(CFG["GRAPH_PATH"])

    ### Choose algorithms here ###

    ALGORITHMS: Dict[str, callable] = {
        # "nn_dijkstra": nn_dijkstra,
        "nn_a_star": nn_a_star,
        "EAMDSP": EAMDSP,
        # "MDMSMD": MDMSMD,
        "bnb_a_star_modified_mstbound": bnb_a_star_modified_mstbound,
        "bnb_a_star_modified_lowerbound": bnb_a_star_modified_lowerbound,
        # "bnb_a_star_modified_lowerbound_preload_astar": bnb_a_star_modified_lowerbound_preload_astar,
        # "bnb_dijkstra": bnb_dijkstra,
        "bnb_a_star": bnb_a_star,
    }

    df, last_logs, cutoff_n = run_item_benchmarks(
        G=G,
        entry=CFG["ENTRY"],
        checkouts=CFG["CHECKOUTS"],
        pool_size=CFG["POOL_SIZE"],
        excluded=CFG["EXCLUDED"],
        item_counts=CFG["ITEM_COUNTS"],
        runs=CFG["RUNS"],
        algorithms=ALGORITHMS,
        seed=CFG["SEED"],
        time_limit_seconds=CFG["TIME_LIMIT_SECONDS"],
    )

    # Aggregated table
    agg = (
        df.groupby(["setup", "n_points"])
        .agg(
            MeanRuntimeSeconds=("runtime_seconds", "mean"),
            StdRuntimeSeconds=("runtime_seconds", "std"),
            NumSamples=("runtime_seconds", "count"),
        )
        .reset_index()
        .rename(columns={"setup": "Algorithm", "n_points": "NumItems"})
        .sort_values(["Algorithm", "NumItems"])
    )

    agg.to_csv(csv_path, index=False)
    print(f"CSV saved to: {csv_path}")

    save_table_as_image(agg, filename=str(table_png_path), title="Aggregated Runtime Table")
    print(f"Table image saved to: {table_png_path}")

    plot_items_scaling_with_errorbars(
        df=df,
        item_counts=CFG["ITEM_COUNTS"],
        filename=str(plot_png_path),
    )


    print("\n=== Cutoff summary (first n with runtime > 60s) ===")
    for algo in ALGORITHMS.keys():
        cn = cutoff_n.get(algo)
        if cn is None:
            print(f"{algo}: no cutoff (completed all configured item counts)")
        else:
            print(f"{algo}: cutoff at n={cn} (logged n={cn}, skipped n>{cn})")

    print("\n=== Final logged output per algorithm (last measurement it performed) ===")
    for setup, results in last_logs.items():
        route = results.get("route_result", {})
        order = route.get("order", None)

        print(f"\n[{setup}]")
        if isinstance(order, list):
            print("Route order:", " -> ".join(order))
        else:
            print("Route order: (not available as route_result['order'])")

        dist = results.get("distance", float("nan"))
        turns = results.get("turns", "n/a")
        if isinstance(dist, (float, int)):
            print(f"Distance (weighted): {dist:.6f}")
        else:
            print(f"Distance (weighted): {dist}")
        print(f"Turns: {turns}")

    print("\n=== Aggregated mean/std by algorithm and item count ===")
    print(agg.to_string(index=False))


if __name__ == "__main__":
    main()