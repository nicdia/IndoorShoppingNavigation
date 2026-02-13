"""
Benchmark script for the indoor routing algorithms (BnB + Dijkstra / A*).

Workflow / Structure:

1) Algorithm configurations (CONFIGS)
   - Different routing algorithms are configured, currently:
         * bnb_dijkstra  (Branch & Bound + Dijkstra as shortest-path method)
         * bnb_astar     (Branch & Bound + A* as shortest-path method)
   - For each algorithm, the number of runtime measurements can be specified
     (runtime_repeats).

2) Test scenarios (SCENARIOS)
   - Each scenario defines a fixed routing setup on the same graph:
         * graph_path  → path to the GraphML file
         * entry       → entry node
         * items       → list of item nodes that must be visited
         * checkouts   → possible target / checkout nodes
   - The scenarios mainly differ in the number and spatial distribution
     of items (small, medium, large) in order to cover different
     difficulty levels.

3) run_experiments()
   - For each combination of (scenario × algorithm):
         * the graph is loaded (ensuring the 'weight' attribute is present),
         * the algorithm is executed via evaluate_all_criteria,
         * the following metrics are extracted:
               - runtime_seconds (runtime, optionally averaged over multiple repetitions)
               - distance        (total distance along the walk)
               - turns           (number of direction changes in the walk)
               - route_order     (order: Entry → Items → Checkout)
               - walk_length     (number of nodes in the walk)
   - All results are collected in a DataFrame, where each row corresponds
     to one setup "scenario__algorithm".
   - This DataFrame serves as the basis for:
         * table outputs (output_table.py),
         * heatmap visualization (output_heatmap.py),
         * criteria diagrams (output_criteria_diagrams.py).

4) run_scaling_experiments()
   - Optional benchmark for scalability:
         * For a selected scenario, the number of items is varied
           (n_items_list).
         * For each item count and each algorithm, runtime,
           distance, and turns are measured.
   - Objective: analyze how the algorithms scale with increasing
     problem size (more items).

Goal:
A reproducible benchmarking framework to compare routing algorithms
based on clearly defined scenarios and standardized metrics, evaluating
both solution quality (distance, turns) and efficiency (runtime).
"""

from __future__ import annotations
from typing import Any, Dict, List

import pandas as pd
import networkx as nx

from ..criteria.metrics_wrapper import evaluate_all_criteria
from ..algorithms.bnb_dijkstra import run_algorithm as run_bnb_dijkstra
from ..algorithms.bnb_a_star import run_algorithm as run_bnb_astar
from ..algorithms.bnb_a_star_modified_lowerbound import run_algorithm as run_bnb_astar_lowerbound
from ..algorithms.bnb_a_star_modified_lowerbound_preload_astar import run_algorithm as run_bnb_astar_lowerbound_preload_astar
from ..algorithms.bnb_a_star_modified_mstbound import run_algorithm as run_bnb_astar_mstbound  
from ..algorithms.nn_dijkstra import run_algorithm as run_nn_dijkstra 
from ..algorithms.nn_a_star import run_algorithm as run_nn_astar      
from ..algorithms.EAMDSP import run_algorithm as run_eamdsp
from ..algorithms.MDMSMD import run_algorithm as run_mdmsmd

# ---------------------------------------------------------
# Common Configuration: Algorithms
# ---------------------------------------------------------

CONFIGS = [
    {"name": "bnb_dijkstra",                        "algo": run_bnb_dijkstra,                       "runtime_repeats": 5},
    {"name": "bnb_astar",                           "algo": run_bnb_astar,                          "runtime_repeats": 5},
    {"name": "nn_dijkstra",                         "algo": run_nn_dijkstra,                        "runtime_repeats": 5},
    {"name": "nn_astar",                            "algo": run_nn_astar,                           "runtime_repeats": 5},
    {"name": "EAMDSP",                              "algo": run_eamdsp,                             "runtime_repeats": 5},
    {"name": "MDMSMD",                              "algo": run_mdmsmd,                             "runtime_repeats": 5},
    {"name": "bnb_astar_lowerbound",                "algo": run_bnb_astar_lowerbound,               "runtime_repeats": 5},
    {"name": "bnb_astar_lowerbound_preload_astar",  "algo": run_bnb_astar_lowerbound_preload_astar, "runtime_repeats": 5},
    {"name": "bnb_astar_mstbound",                  "algo": run_bnb_astar_mstbound,                 "runtime_repeats": 5}
]

# ---------------------------------------------------------
# Test Scenarios (Graph + Entry + Items + Checkouts)
# ---------------------------------------------------------

SCENARIOS: List[Dict[str, Any]] = [
    # 1) Small, local scenario with 3 items close to the entry
    {
        "name": "small_3_items",
        "graph_path": "resources/graph.graphml",
        "entry": "21",  # (2, 2)
        "items": [
            "41",  # (1, 6)
            "61",  # (1, 9)
            "59",  # (1, 13)
        ],
        "checkouts": [
            "14",  # (15, 6)
            "15",  # (19, 6)
        ],
    },

    # 2) Medium senario with 3 items
    {
        "name": "medium_6_items",
        "graph_path": "resources/graph.graphml",
        "entry": "21",  # (2, 2)
        "items": [
            "41",  # (1, 6)
            "59",  # (1, 13)
            "72",  # (6, 24)
            "88",  # (14, 16)
            "95",  # (19, 26)
            "132", # (11, 26)
        ],
        "checkouts": [
            "14",  # (15, 6)
            "15",  # (19, 6)
        ],
    },

    # 3) Larger Scenario with 10 items distributed in the whole store 
    {
        "name": "large_10_items",
        "graph_path": "resources/graph.graphml",
        "entry": "21",  # (2, 2)
        "items": [
            "41",   # (1, 6)
            "59",   # (1, 13)
            "72",   # (6, 24)
            "88",   # (14, 16)
            "95",   # (19, 26)
            "132",  # (11, 26)
            "101",  # (15, 36)
            "111",  # (9, 38)
            "127",  # (1, 39)
            "146",  # (19, 34)
        ],
        "checkouts": [
            "14",  # (15, 6)
            "15",  # (19, 6)
        ],
    },
]

# ---------------------------------------------------------
# Helper: load graph 
# ---------------------------------------------------------

def load_graph(path: str) -> nx.Graph:
    """
    Loads the graph and ensures that every edge has a 'weight' attribute.
    """
    G = nx.read_graphml(path)
    for u, v, d in G.edges(data=True):
        d["weight"] = float(d.get("weight", d.get("length", 1.0)))
    return G


# ---------------------------------------------------------
# 1) Quality Benchmark – all Scenarien × Algorithms
# ---------------------------------------------------------

def run_experiments() -> pd.DataFrame:
    """
    Executes all algorithm+scenario combinations and returns 
    a DataFrame with all metrics. (runtime, distance, turns).
    """

    rows: List[Dict[str, Any]] = []
    graph_cache: Dict[str, nx.Graph] = {}

    for scenario in SCENARIOS:
        scen_name = scenario["name"]
        graph_path = scenario["graph_path"]
        entry = scenario["entry"]
        items = scenario["items"]
        checkouts = scenario["checkouts"]

        if graph_path not in graph_cache:
            graph_cache[graph_path] = load_graph(graph_path)
        G = graph_cache[graph_path]

        for cfg in CONFIGS:
            algo = cfg["algo"]
            algo_name = cfg["name"]
            runtime_repeats = cfg.get("runtime_repeats", 1)

            eval_result = evaluate_all_criteria(
                algorithm_fn=algo,
                G=G,
                entry=entry,
                items=items,
                checkouts=checkouts,
                runtime_repeats=runtime_repeats,
            )

            route = eval_result["route_result"]
            order = route.get("order", [])
            walk = route.get("walk", [])

            row: Dict[str, Any] = {
                "setup": f"{scen_name}__{algo_name}",

                "scenario": scen_name,
                "graph_path": graph_path,
                "algorithm_setup": algo_name,
                "algorithm": getattr(algo, "__name__", str(algo)),

                "entry": entry,
                "items": ",".join(items),
                "checkouts": ",".join(checkouts),
                "n_items": len(items),
                "n_checkouts": len(checkouts),

                "runtime_seconds": float(eval_result["runtime_seconds"]),
                "distance": float(eval_result["distance"]),
                "turns": int(eval_result["turns"]),

                "route_order": " -> ".join(order) if order else "",
                "walk_length": len(walk),
            }

            rows.append(row)

    df = pd.DataFrame(rows).set_index("setup")

    # optional column order
    preferred_order = [
        "scenario",
        "algorithm_setup",
        "algorithm",
        "graph_path",

        "entry",
        "items",
        "checkouts",
        "n_items",
        "n_checkouts",

        "runtime_seconds",
        "distance",
        "turns",

        "route_order",
        "walk_length",
    ]

    existing_cols = [c for c in preferred_order if c in df.columns]
    remaining_cols = [c for c in df.columns if c not in existing_cols]
    df = df[existing_cols + remaining_cols]

    print(df)
    return df


# ---------------------------------------------------------
# 2) Scaling Benchmark – optional: scaling by number of items
# ---------------------------------------------------------

def run_scaling_experiments(
    scenario_name: str,
    n_items_list: List[int],
    repeats: int = 3,
) -> pd.DataFrame:
    """
    Measures runtime scaling for a scenario by varying the number of items.
    A subset of the items from the selected scenario is used.
    """

    base_scenarios = {s["name"]: s for s in SCENARIOS}
    if scenario_name not in base_scenarios:
        raise ValueError(f"Szenario '{scenario_name}' not defined in SCENARIOS.")

    base_scen = base_scenarios[scenario_name]
    graph_path = base_scen["graph_path"]
    entry = base_scen["entry"]
    base_items = base_scen["items"]
    checkouts = base_scen["checkouts"]

    G = load_graph(graph_path)

    rows: List[Dict[str, Any]] = []

    for n in n_items_list:
        n_eff = min(n, len(base_items))

        for run_id in range(repeats):
            items = base_items[:n_eff]

            for cfg in CONFIGS:
                algo = cfg["algo"]
                algo_name = cfg["name"]
                runtime_repeats = cfg.get("runtime_repeats", 1)

                eval_result = evaluate_all_criteria(
                    algorithm_fn=algo,
                    G=G,
                    entry=entry,
                    items=items,
                    checkouts=checkouts,
                    runtime_repeats=runtime_repeats,
                )

                rows.append(
                    {
                        "scenario": scenario_name,
                        "algorithm_setup": algo_name,
                        "algorithm": getattr(algo, "__name__", str(algo)),
                        "n_items": n_eff,
                        "run_id": run_id,
                        "runtime_seconds": float(eval_result["runtime_seconds"]),
                        "distance": float(eval_result["distance"]),
                        "turns": int(eval_result["turns"]),
                    }
                )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = run_experiments()
    with pd.option_context("display.max_columns", None, "display.width", 180):
        print("\n=== Algorithm Comparison (Routing) ===\n")
        print(df)