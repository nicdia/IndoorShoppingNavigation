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
    Runs all three criteria in the same setup and returns the results as a dict.
    Expects algorithm_fn to return the following dict:
        {
            "order": [...],
            "walk": [...],
            "total_distance": float
        }
    """

    # 1) Run algorithm once (for distance + turns)
    result = algorithm_fn(G, entry, items, checkouts)

    # 2) Compute distance
    dist = distance_score(G, result)

    # 3) Count turns
    turns = count_turns(G, result)

    # 4) Measure runtime separately
    runtime_sec = measure_runtime(
        algorithm_fn, G, entry, items, checkouts, repeats=runtime_repeats
    )

    return {
        "route_result": result,       # contains order, walk, total_distance
        "runtime_seconds": runtime_sec,
        "distance": dist,
        "turns": turns,
    }