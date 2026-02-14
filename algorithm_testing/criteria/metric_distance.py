# metric_distance.py
import networkx as nx


def compute_distance_from_walk(G: nx.Graph, result: dict) -> float:
    """
    Computes the distance based on result["walk"].
    """
    walk = result.get("walk", [])
    dist = 0.0

    for u, v in zip(walk[:-1], walk[1:]):
        edge_data = G.get_edge_data(u, v, default={})
        w = float(edge_data.get("weight", 1.0))
        dist += w

    return dist


def distance_score(G: nx.Graph, result: dict) -> float:
    """
    Returns the distance.
    Uses result["total_distance"] if available and > 0,
    else computes the distance from the walk.
    """
    total_dist = result.get("total_distance", None)

    if total_dist is not None and total_dist > 0:
        return float(total_dist)

    return compute_distance_from_walk(G, result)