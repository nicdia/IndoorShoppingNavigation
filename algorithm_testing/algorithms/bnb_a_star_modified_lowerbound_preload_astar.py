 # algorithm_astar_bnb_lowerbound_preload.py
"""
B&B with lower-bound pruning.
Uses precomputed distances from CSV for the visit order.
Computes the final route with A* based on the found order.
"""
import math
import heapq
import itertools
import csv
import os
import networkx as nx
from typing import Any, Tuple


# -------------------------------------------------------------
# A* IMPLEMENTATION
# -------------------------------------------------------------
def _node_coord(graph: nx.Graph, node: Any) -> Tuple[float, float] | None:
    data = graph.nodes[node]
    if "x" in data and "y" in data:
        return float(data["x"]), float(data["y"])
    if "lon" in data and "lat" in data:
        return float(data["lon"]), float(data["lat"])
    return None


def _heuristic(graph: nx.Graph, u: Any, v: Any) -> float:
    cu = _node_coord(graph, u)
    cv = _node_coord(graph, v)
    if cu is None or cv is None:
        return 0.0
    x1, y1 = cu
    x2, y2 = cv
    return math.hypot(x2 - x1, y2 - y1)


def astar(graph: nx.Graph, origin: Any, destination: Any):
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
# Load precomputed distances from CSV
# -------------------------------------------------------------
def load_precomputed_distances(csv_path: str) -> dict:
    """Loads precomputed distance matrix from CSV."""
    dist = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            u = row["from"]
            v = row["to"]
            d = float(row["distance"])
            if u not in dist:
                dist[u] = {}
            dist[u][v] = d
    return dist


# -------------------------------------------------------------
# Lower-bound computation
# -------------------------------------------------------------
def compute_lower_bound(remaining: list, checkouts: list, dist: dict) -> float:
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
# Branch & Bound with lower-bound pruning (uses preloaded dist)
# -------------------------------------------------------------
def bnb(current, remaining, cost, order_prefix, dist, checkouts, best):
    best_order, best_cost = best

    # Pruning mit Lower-Bound
    lb = compute_lower_bound(remaining, checkouts, dist)
    if cost + lb >= best_cost:
        return best

    if not remaining:
        for c in checkouts:
            if current in dist and c in dist[current]:
                d = dist[current][c]
                total = cost + d
                if math.isfinite(total) and total < best_cost:
                    best_order = order_prefix + [c]
                    best_cost = total
        return best_order, best_cost

    for nxt in sorted(remaining, key=lambda x: dist.get(current, {}).get(x, math.inf)):
        if current not in dist or nxt not in dist[current]:
            continue
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
# Recompute route with A* based on visit order
# -------------------------------------------------------------
def compute_route_from_order(G: nx.Graph, order: list[str]):
    """Computes the full route with A* for a given visit order."""
    walk = []
    total_dist = 0.0

    for a, b in zip(order[:-1], order[1:]):
        path, d = astar(G, a, b)
        if not path:
            return [], math.inf
        walk.extend(path if not walk else path[1:])
        total_dist += d

    return walk, total_dist


# -------------------------------------------------------------
# run_algorithm
# -------------------------------------------------------------
_preloaded_dist = None
_preload_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "preload_astar",
    "precomputed_distances.csv"
)


def run_algorithm(G: nx.Graph, entry: str, items: list[str], checkouts: list[str]):
    """
    B&B with lower-bound pruning.
    - Uses precomputed distances for the visit order
    - Computes the final route with A*
    """
    global _preloaded_dist

    # Preload distances on first call
    if _preloaded_dist is None:
        if os.path.exists(_preload_path):
            _preloaded_dist = load_precomputed_distances(_preload_path)
        else:
            # Fallback: no preload file, compute live
            _preloaded_dist = {}

    # Check if all required nodes exist in preload
    relevant = [entry] + items + checkouts
    missing = [n for n in relevant if n not in _preloaded_dist]

    if missing or not _preloaded_dist:
        # Fallback: compute pairwise A* live
        dist = {u: {} for u in relevant}
        for u, v in itertools.permutations(relevant, 2):
            _, d = astar(G, u, v)
            dist[u][v] = d
    else:
        dist = _preloaded_dist

    # B&B for visit order
    if items:
        best_order, _ = bnb(
            entry,
            items,
            0.0,
            [entry],
            dist,
            checkouts,
            (None, math.inf),
        )
    else:
        if entry in dist and checkouts:
            best_checkout = min(checkouts, key=lambda c: dist.get(entry, {}).get(c, math.inf))
            best_order = [entry, best_checkout]
        else:
            best_order = [entry] + checkouts[:1]

    if not best_order:
        return {
            "order": [],
            "walk": [],
            "total_distance": math.inf,
        }

    # Recompute route with A* based on visit order
    walk, total_dist = compute_route_from_order(G, best_order)

    return {
        "order": best_order,
        "walk": walk,
        "total_distance": float(total_dist),
    }
