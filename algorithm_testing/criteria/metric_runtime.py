# metric_runtime.py
import time
from typing import Callable
import networkx as nx


def measure_runtime(
    algorithm_fn: Callable[[nx.Graph, str, list[str], list[str]], dict],
    G: nx.Graph,
    entry: str,
    items: list[str],
    checkouts: list[str],
    repeats: int = 1
) -> float:
    """
    Misst die Laufzeit des Algorithmus in Sekunden (Durchschnitt über 'repeats' Läufe).
    Erwartet, dass algorithm_fn ein Dict zurückgibt.
    """
    start = time.perf_counter()
    for _ in range(repeats):
        _ = algorithm_fn(G, entry, items, checkouts)
    end = time.perf_counter()
    return (end - start) / repeats