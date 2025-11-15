# metrics_wrapper.py
from typing import Callable, Dict, Any
import networkx as nx

from .metric_runtime import measure_runtime
from .metric_distance import distance_score
from .metric_turns import count_turns



def evaluate_all_criteria(
    algorithm_fn: Callable[[nx.Graph, str, list[str], list[str]], Dict[str, Any]],
    G: nx.Graph,
    entry: str,
    items: list[str],
    checkouts: list[str],
    runtime_repeats: int = 1,
) -> Dict[str, Any]:
    """
    Führt alle drei Kriterien im gleichen Setting aus und gibt die Ergebnisse als Dict zurück.
    Erwartet, dass algorithm_fn folgendes Dict zurückgibt:
        {
            "order": [...],
            "walk": [...],
            "total_distance": float
        }
    """

    # 1) Algorithmus einmal ausführen (für Distanz + Turns)
    result = algorithm_fn(G, entry, items, checkouts)

    # 2) Distanz berechnen
    dist = distance_score(G, result)

    # 3) Anzahl Abbiegen
    turns = count_turns(G, result)

    # 4) Laufzeit separat messen
    runtime_sec = measure_runtime(
        algorithm_fn, G, entry, items, checkouts, repeats=runtime_repeats
    )

    return {
        "route_result": result,       # enthält order, walk, total_distance
        "runtime_seconds": runtime_sec,
        "distance": dist,
        "turns": turns,
    }