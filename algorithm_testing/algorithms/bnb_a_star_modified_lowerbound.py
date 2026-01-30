# algorithm_astar_bnb_lowerbound.py
import math
import heapq
import itertools
import networkx as nx
from typing import Any, Tuple


# -------------------------------------------------------------
# A* IMPLEMENTATION
# -------------------------------------------------------------
def _node_coord(graph: nx.Graph, node: Any) -> Tuple[float, float] | None:
    """Liest (x, y)-Koordinaten eines Knotens, falls vorhanden."""
    data = graph.nodes[node]
    if "x" in data and "y" in data:
        return float(data["x"]), float(data["y"])
    if "lon" in data and "lat" in data:
        return float(data["lon"]), float(data["lat"])
    return None


def _heuristic(graph: nx.Graph, u: Any, v: Any) -> float:
    """Euklidische Heuristik. Falls keine Koordinaten existieren → 0."""
    cu = _node_coord(graph, u)
    cv = _node_coord(graph, v)
    if cu is None or cv is None:
        return 0.0
    x1, y1 = cu
    x2, y2 = cv
    return math.hypot(x2 - x1, y2 - y1)


def astar(graph: nx.Graph, origin: Any, destination: Any):
    """Reiner A*-Shortest-Path (Pfad, Distanz)."""
    if origin == destination:
        return [origin], 0.0

    infinity = math.inf
    g_score = {origin: 0.0}
    f_score = {origin: _heuristic(graph, origin, destination)}
    came_from = {}

    open_heap = [(f_score[origin], origin)]

    while open_heap:
        _, u = heapq.heappop(open_heap)

        if u == destination:
            break

        for v, attrs in graph[u].items():
            w = float(attrs.get("weight", 1.0))
            tentative = g_score.get(u, infinity) + w
            if tentative < g_score.get(v, infinity):
                came_from[v] = u
                g_score[v] = tentative
                f_score[v] = tentative + _heuristic(graph, v, destination)
                heapq.heappush(open_heap, (f_score[v], v))

    if destination not in g_score:
        return [], math.inf

    # Pfad rekonstruieren
    path = []
    cur = destination
    while cur != origin:
        path.append(cur)
        cur = came_from.get(cur)
        if cur is None:
            return [], math.inf
    path.append(origin)
    path.reverse()

    return path, g_score[destination]


# -------------------------------------------------------------
# Paarweise A*
# -------------------------------------------------------------
def compute_pairwise_astar(G: nx.Graph, relevant: list[str]):
    dist = {u: {} for u in relevant}
    spath = {u: {} for u in relevant}

    for u, v in itertools.permutations(relevant, 2):
        p, d = astar(G, u, v)
        dist[u][v] = d
        spath[u][v] = p

    return dist, spath


# -------------------------------------------------------------
# Lower-Bound Berechnung
# -------------------------------------------------------------
def compute_lower_bound(remaining: list, checkouts: list, dist: dict) -> float:
    """Summe der minimalen Distanz von jedem remaining-Knoten zu einem anderen remaining oder checkout."""
    if not remaining:
        return 0.0

    lb = 0.0
    targets = set(remaining) | set(checkouts)

    for r in remaining:
        min_dist = math.inf
        for t in targets:
            if t != r and r in dist and t in dist[r]:
                d = dist[r][t]
                if d < min_dist:
                    min_dist = d
        if math.isfinite(min_dist):
            lb += min_dist

    return lb


# -------------------------------------------------------------
# Branch & Bound mit Lower-Bound Pruning
# -------------------------------------------------------------
def bnb(current, remaining, cost, order_prefix, dist, checkouts, best):
    best_order, best_cost = best

    # Pruning mit Lower-Bound
    lb = compute_lower_bound(remaining, checkouts, dist)
    if cost + lb >= best_cost:
        return best

    if not remaining:
        for c in checkouts:
            d = dist[current][c]
            total = cost + d
            if math.isfinite(total) and total < best_cost:
                best_order = order_prefix + [c]
                best_cost = total
        return best_order, best_cost

    for nxt in sorted(remaining, key=lambda x: dist[current][x]):
        d = dist[current][nxt]
        if not math.isfinite(d):
            continue

        best_order, best_cost = bnb(
            nxt,
            [r for r in remaining if r != nxt],
            cost + d,
            order_prefix + [nxt],
            dist,
            checkouts,
            (best_order, best_cost),
        )

    return best_order, best_cost


# -------------------------------------------------------------
# run_algorithm
# -------------------------------------------------------------
def run_algorithm(G: nx.Graph, entry: str, items: list[str], checkouts: list[str]):
    """
    B&B mit A* und Lower-Bound Pruning.
    """
    relevant = [entry] + items + checkouts
    dist, spath = compute_pairwise_astar(G, relevant)

    if items:
        best_order, best_cost = bnb(
            entry,
            items,
            0.0,
            [entry],
            dist,
            checkouts,
            (None, math.inf),
        )
    else:
        best_order = [entry] + [min(checkouts, key=lambda c: dist[entry][c])]
        best_cost = dist[entry][best_order[-1]]

    if not best_order:
        return {
            "order": [],
            "walk": [],
            "total_distance": math.inf,
        }

    walk = []
    for a, b in zip(best_order[:-1], best_order[1:]):
        seg = spath[a][b]
        walk.extend(seg if not walk else seg[1:])

    return {
        "order": best_order,
        "walk": walk,
        "total_distance": float(best_cost),
    }
