# criteria/turns_criterion.py
import math
import networkx as nx
from route_types import RouteResult

def _angle_between(p1, p2, p3) -> float:
    """
    Winkel in Grad zwischen den Vektoren p1->p2 und p2->p3.
    """
    v1 = (p2[0] - p1[0], p2[1] - p1[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])

    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return 0.0

    dot = v1[0] * v2[0] + v1[1] * v2[1]
    cos_val = max(-1.0, min(1.0, dot / (n1 * n2)))
    return math.degrees(math.acos(cos_val))

def count_turns(G: nx.Graph, result: RouteResult, angle_threshold: float = 45.0) -> int:
    """
    Zählt, wie oft die Route abbiegt.
    Turn = Winkel zwischen zwei Segmenten >= angle_threshold.
    """
    walk = result.walk
    if len(walk) < 3:
        return 0

    turns = 0
    for a, b, c in zip(walk[:-2], walk[1:-1], walk[2:]):
        try:
            p1 = (float(G.nodes[a]["x"]), float(G.nodes[a]["y"]))
        except KeyError:
            continue
        try:
            p2 = (float(G.nodes[b]["x"]), float(G.nodes[b]["y"]))
            p3 = (float(G.nodes[c]["x"]), float(G.nodes[c]["y"]))
        except KeyError:
            continue

        angle = _angle_between(p1, p2, p3)
        if angle >= angle_threshold:
            turns += 1

    return turns