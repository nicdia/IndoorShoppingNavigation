# criteria/distance_criterion.py
import networkx as nx
from route_types import RouteResult

def compute_distance_from_walk(G: nx.Graph, result: RouteResult) -> float:
    """
    Berechnet die Distanz entlang des Walks im Graphen.
    """
    dist = 0.0
    for u, v in zip(result.walk[:-1], result.walk[1:]):
        edge_data = G.get_edge_data(u, v, default={})
        w = float(edge_data.get("weight", 1.0))
        dist += w
    return dist

def distance_score(G: nx.Graph, result: RouteResult) -> float:
    """
    Holt die Distanz aus RouteResult oder berechnet sie aus dem Walk.
    """
    if result.total_distance and result.total_distance > 0:
        return float(result.total_distance)
    return compute_distance_from_walk(G, result)