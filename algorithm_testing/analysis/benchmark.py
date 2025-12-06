"""
Benchmark-Skript für die Indoor-Routing-Algorithmen (BnB + Dijkstra / A*).

Ablauf / Aufbau:

1) Algorithmus-Konfigurationen (CONFIGS)
   - Es werden verschiedene Routing-Algorithmen konfiguriert, aktuell:
         * bnb_dijkstra  (Branch & Bound + Dijkstra als Shortest-Path)
         * bnb_astar     (Branch & Bound + A* als Shortest-Path)
   - Für jeden Algorithmus kann festgelegt werden, wie oft die Laufzeit
     gemessen werden soll (runtime_repeats).

2) Testszenarien (SCENARIOS)
   - Jedes Szenario beschreibt ein fixes Routing-Setup auf demselben Graphen:
         * graph_path  → Pfad zur GraphML-Datei
         * entry       → Einstiegs-Knoten
         * items       → Liste von Item-Knoten, die besucht werden müssen
         * checkouts   → mögliche Ziel-/Checkout-Knoten
   - Die Szenarien unterscheiden sich v. a. durch die Anzahl und räumliche
     Verteilung der Items (klein, mittel, groß), um unterschiedliche
     Schwierigkeitsgrade abzudecken.

3) run_experiments()
   - Für jede Kombination aus (Szenario × Algorithmus) wird:
         * der Graph geladen (mit sichergestelltem 'weight'-Attribut),
         * der Algorithmus über evaluate_all_criteria ausgeführt,
         * folgende Metriken extrahiert:
               - runtime_seconds (Laufzeit, ggf. über mehrere Wiederholungen gemittelt)
               - distance        (Gesamtdistanz entlang des Walks)
               - turns           (Anzahl der Richtungswechsel im Walk)
               - route_order     (Reihenfolge: Entry → Items → Checkout)
               - walk_length     (Anzahl der Knoten im Walk)
   - Alle Ergebnisse werden in einem DataFrame gesammelt, wobei jede Zeile
     einem Setup "scenario__algorithm" entspricht.
   - Dieses DataFrame ist die Grundlage für:
         * Tabellenausgaben (output_table.py),
         * Heatmap-Visualisierung (output_heatmap.py),
         * Kriteriendiagramme (output_criteria_diagrams.py).

4) run_scaling_experiments()
   - Optionaler Benchmark zur Skalierung:
         * Es wird für ein ausgewähltes Szenario die Anzahl der Items
           variiert (n_items_list).
         * Für jede Item-Anzahl und jeden Algorithmus werden Laufzeit,
           Distanz und Turns gemessen.
   - Ziel: zu analysieren, wie die Algorithmen mit wachsender Problemgröße
     (mehr Items) skalieren.

Ziel:
Ein reproduzierbarer Benchmark-Rahmen, um Routing-Algorithmen anhand
klarer Szenarien und einheitlicher Metriken zu vergleichen und sowohl
Qualität (Distanz, Turns) als auch Effizienz (Laufzeit) auszuwerten.
"""

from __future__ import annotations
from typing import Any, Dict, List

import pandas as pd
import networkx as nx

from ..criteria.metrics_wrapper import evaluate_all_criteria
from ..algorithms.bnb_algorithm import run_algorithm as run_bnb_dijkstra
from ..algorithms.bnb_a_star import run_algorithm as run_bnb_astar


# ---------------------------------------------------------
# Gemeinsame Konfigurationen: Algorithmen
# ---------------------------------------------------------

CONFIGS: List[Dict[str, Any]] = [
    {
        "name": "bnb_dijkstra",
        "algo": run_bnb_dijkstra,
        "runtime_repeats": 5,
    },
    {
        "name": "bnb_astar",
        "algo": run_bnb_astar,
        "runtime_repeats": 5,
    },
    # weitere Algorithmen könntest du hier ergänzen
]


# ---------------------------------------------------------
# Testszenarien (Graph + Entry + Items + Checkouts)
# ---------------------------------------------------------

SCENARIOS: List[Dict[str, Any]] = [
    # 1) Kleines, lokales Szenario – alles in der Nähe von Entry (unten links)
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

    # 2) Mittleres Szenario – Items von unten links bis mittig/oben rechts (~y 26)
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

    # 3) Großes Szenario – Items über den ganzen Store verteilt (maximale Ausdehnung)
    {
        "name": "large_10_items",
        "graph_path": "resources/graph.graphml",
        "entry": "21",  # (2, 2)
        "items": [
            "41",   # (1, 6)    – unten links
            "59",   # (1, 13)
            "72",   # (6, 24)
            "88",   # (14, 16)
            "95",   # (19, 26)
            "132",  # (11, 26)
            "101",  # (15, 36)  – oben mittig/rechts
            "111",  # (9, 38)   – oben mittig
            "127",  # (1, 39)   – oben ganz links
            "146",  # (19, 34)  – oben rechts
        ],
        "checkouts": [
            "14",  # (15, 6)
            "15",  # (19, 6)
        ],
    },
]

# ---------------------------------------------------------
# Helper: Graph laden (mit Weight-Attribut)
# ---------------------------------------------------------

def load_graph(path: str) -> nx.Graph:
    """
    Lädt den Graphen und stellt sicher, dass jede Kante ein 'weight'-Attribut hat.
    """
    G = nx.read_graphml(path)
    for u, v, d in G.edges(data=True):
        d["weight"] = float(d.get("weight", d.get("length", 1.0)))
    return G


# ---------------------------------------------------------
# 1) Quality Benchmark – alle Szenarien × Algorithmen
# ---------------------------------------------------------

def run_experiments() -> pd.DataFrame:
    """
    Führt alle Algorithmus+Szenario-Kombis aus und gibt ein DataFrame
    mit allen Metriken zurück (runtime, distance, turns).
    """

    rows: List[Dict[str, Any]] = []
    graph_cache: Dict[str, nx.Graph] = {}

    for scenario in SCENARIOS:
        scen_name = scenario["name"]
        graph_path = scenario["graph_path"]
        entry = scenario["entry"]
        items = scenario["items"]
        checkouts = scenario["checkouts"]

        # Graph nur einmal pro Datei laden
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
                # Schlüssel für eindeutige Zeile
                "setup": f"{scen_name}__{algo_name}",

                # Meta
                "scenario": scen_name,
                "graph_path": graph_path,
                "algorithm_setup": algo_name,
                "algorithm": getattr(algo, "__name__", str(algo)),

                "entry": entry,
                "items": ",".join(items),
                "checkouts": ",".join(checkouts),
                "n_items": len(items),
                "n_checkouts": len(checkouts),

                # Metriken aus evaluate_all_criteria
                "runtime_seconds": float(eval_result["runtime_seconds"]),
                "distance": float(eval_result["distance"]),
                "turns": int(eval_result["turns"]),

                # Route-Infos
                "route_order": " -> ".join(order) if order else "",
                "walk_length": len(walk),
            }

            rows.append(row)

    df = pd.DataFrame(rows).set_index("setup")

    # Optionale Spalten-Reihenfolge
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
# 2) Scaling Benchmark – optional: Skalierung nach Item-Anzahl
# ---------------------------------------------------------

def run_scaling_experiments(
    scenario_name: str,
    n_items_list: List[int],
    repeats: int = 3,
) -> pd.DataFrame:
    """
    Misst Laufzeit-Skalierung für ein Szenario, indem die Anzahl der Items variiert wird.
    Es wird eine Teilmenge der Items des gewählten Szenarios verwendet.
    """

    base_scenarios = {s["name"]: s for s in SCENARIOS}
    if scenario_name not in base_scenarios:
        raise ValueError(f"Szenario '{scenario_name}' nicht in SCENARIOS definiert.")

    base_scen = base_scenarios[scenario_name]
    graph_path = base_scen["graph_path"]
    entry = base_scen["entry"]
    base_items = base_scen["items"]
    checkouts = base_scen["checkouts"]

    G = load_graph(graph_path)

    rows: List[Dict[str, Any]] = []

    for n in n_items_list:
        # Begrenzung: nicht mehr Items als im Szenario existieren
        n_eff = min(n, len(base_items))

        for run_id in range(repeats):
            # einfache Variante: deterministische ersten n_eff Items
            # (wenn du Randomisierung willst → random.sample mit seed)
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
    # Einfacher manueller Run
    df = run_experiments()
    with pd.option_context("display.max_columns", None, "display.width", 180):
        print("\n=== Algorithm Comparison (Routing) ===\n")
        print(df)