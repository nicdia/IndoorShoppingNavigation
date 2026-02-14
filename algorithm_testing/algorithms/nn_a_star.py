# algorithm_astar_bnb.py
import math
import heapq
import itertools
import networkx as nx
from typing import Any, Tuple


# -------------------------------------------------------------
# A* IMPLEMENTATION (replaces Dijkstra)
# -------------------------------------------------------------
def _node_coord(graph: nx.Graph, node: Any) -> Tuple[float, float] | None:
    """Reads (x, y) coordinates of a node, if available."""
    data = graph.nodes[node]
    if "x" in data and "y" in data:
        return float(data["x"]), float(data["y"])
    if "lon" in data and "lat" in data:
        return float(data["lon"]), float(data["lat"])
    return None


def _heuristic(graph: nx.Graph, u: Any, v: Any) -> float:
    """Euclidean heuristic. Returns 0 if coordinates are missing."""
    cu = _node_coord(graph, u)
    cv = _node_coord(graph, v)
    if cu is None or cv is None:
        return 0.0
    x1, y1 = cu
    x2, y2 = cv
    return math.hypot(x2 - x1, y2 - y1)


def astar(graph: nx.Graph, origin: Any, destination: Any):
    """Pure A* shortest path (path, distance)."""
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

    # Reconstruct path
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
# Pairwise A* (replaces compute_pairwise_dijkstra)
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
# Branch & Bound (unchanged, currently unused)
# -------------------------------------------------------------
def bnb(current, remaining, cost, order_prefix, dist, checkouts, best):
    best_order, best_cost = best

    if cost >= best_cost:
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
# Nearest Neighbour heuristic
# -------------------------------------------------------------
def nearest_neighbour(entry: str, items: list[str], dist: dict, checkouts: list[str]):
    """
    Nearest-Neighbour heuristic:
    - Start at 'entry'
    - Iteratively pick the closest unvisited item
    - Finally pick the closest checkout
    Returns (order, total_cost).
    """
    order: list[str] = [entry]
    current = entry
    remaining = set(items)
    total_cost = 0.0
    infinity = math.inf

    # Visit items one by one using NN
    while remaining:
        nxt = min(remaining, key=lambda x: dist[current].get(x, infinity))
        d = dist[current].get(nxt, infinity)

        if not math.isfinite(d):
            return [], math.inf

        total_cost += d
        order.append(nxt)
        current = nxt
        remaining.remove(nxt)

    # Pick the best checkout from the last position
    best_checkout = None
    best_d = infinity
    for c in checkouts:
        d = dist[current].get(c, infinity)
        if d < best_d:
            best_d = d
            best_checkout = c

    if best_checkout is None or not math.isfinite(best_d):
        return [], math.inf

    order.append(best_checkout)
    total_cost += best_d

    return order, total_cost


# -------------------------------------------------------------
# run_algorithm: same interface, same output format
# -------------------------------------------------------------
def run_algorithm(G: nx.Graph, entry: str, items: list[str], checkouts: list[str]):
    """
    Same as algorithm_bnb.run_algorithm,
    but using A* for pathfinding and Nearest Neighbour for visit order.
    """
    relevant = [entry] + items + checkouts
    dist, spath = compute_pairwise_astar(G, relevant)

    if items:
        best_order, best_cost = nearest_neighbour(
            entry,
            items,
            dist,
            checkouts,
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
