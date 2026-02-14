# algorithm_astar_bnb_mstbound.py
import math
import heapq
import itertools
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
# Pairwise A*
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
# MST-based lower bound (Prim's algorithm)
# -------------------------------------------------------------
def compute_mst_cost(nodes: list, dist: dict) -> float:
    """Computes MST cost for a set of nodes."""
    if len(nodes) <= 1:
        return 0.0

    in_tree = {nodes[0]}
    mst_cost = 0.0

    # Add nodes until all are in the tree
    while len(in_tree) < len(nodes):
        # Find shortest edge from tree to outside
        best_dist = math.inf
        best_node = None
        
        for u in in_tree:
            for v in nodes:
                if v in in_tree:
                    continue
                if u in dist and v in dist[u]:
                    if dist[u][v] < best_dist:
                        best_dist = dist[u][v]
                        best_node = v
        
        if best_node is None:
            break
            
        in_tree.add(best_node)
        mst_cost += best_dist

    return mst_cost


def compute_mst_lower_bound(current, remaining: list, checkouts: list, dist: dict) -> float:
    """
    MST-based lower bound:
    1. min(current to remaining)
    2. MST(remaining)
    3. min(remaining to checkout)
    """
    if not remaining:
        return 0.0

    # 1. Shortest distance to nearest remaining
    min_to_remaining = math.inf
    for r in remaining:
        if current in dist and r in dist[current]:
            if dist[current][r] < min_to_remaining:
                min_to_remaining = dist[current][r]

    if not math.isfinite(min_to_remaining):
        return math.inf

    # 2. MST over remaining
    mst_cost = compute_mst_cost(remaining, dist)

    # 3. Shortest distance to checkout
    min_to_checkout = math.inf
    for r in remaining:
        for c in checkouts:
            if r in dist and c in dist[r]:
                if dist[r][c] < min_to_checkout:
                    min_to_checkout = dist[r][c]

    if not math.isfinite(min_to_checkout):
        return math.inf

    return min_to_remaining + mst_cost + min_to_checkout


# -------------------------------------------------------------
# Branch & Bound with MST Lower Bound
# -------------------------------------------------------------
def bnb(current, remaining, cost, order_prefix, dist, checkouts, best):
    best_order, best_cost = best

    # Pruning with MST Lower Bound
    lb = compute_mst_lower_bound(current, remaining, checkouts, dist)
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
    B&B with A* and MST-based Lower Bound.
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
