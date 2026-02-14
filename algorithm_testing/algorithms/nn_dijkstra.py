# algorithm_bnb.py
import math
import heapq
import itertools
import networkx as nx


def dijkstra(graph: nx.Graph, origin: str, destination: str):
    """
    Shortest path between two nodes using Dijkstra.
    Returns (path, distance).
    """
    if origin == destination:
        return [origin], 0.0

    infinity = math.inf
    dist = {origin: 0.0}
    prev = {}
    pq = [(0.0, origin)]

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, infinity):
            continue
        if u == destination:
            break

        for v, attrs in graph[u].items():
            w = float(attrs.get("weight", 1.0))
            nd = d + w
            if nd < dist.get(v, infinity):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    if destination not in dist:
        return [], math.inf

    path = []
    cur = destination
    while cur != origin:
        path.append(cur)
        cur = prev.get(cur)
        if cur is None:
            return [], math.inf

    path.append(origin)
    path.reverse()
    return path, dist[destination]


def compute_pairwise_dijkstra(G: nx.Graph, relevant: list[str]):
    """
    Computes shortest paths and distances for all ordered pairs
    (u, v) in 'relevant'.
    """
    dist = {u: {} for u in relevant}
    spath = {u: {} for u in relevant}

    for u, v in itertools.permutations(relevant, 2):
        p, d = dijkstra(G, u, v)
        dist[u][v] = d
        spath[u][v] = p

    return dist, spath


def bnb(current, remaining, cost, order_prefix, dist, checkouts, best):
    """
    Branch-and-Bound for determining the optimal visit order.
    (Currently unused, kept for reference only.)
    """
    best_order, best_cost = best

    # Pruning
    if cost >= best_cost:
        return best

    # If no items left: append best checkout
    if not remaining:
        for c in checkouts:
            d = dist[current][c]
            total = cost + d
            if math.isfinite(total) and total < best_cost:
                best_order = order_prefix + [c]
                best_cost = total
        return best_order, best_cost

    # Recurse over remaining items (sorted by distance)
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


def nearest_neighbour(entry: str, items: list[str], dist: dict, checkouts: list[str]):
    """
    Nearest-Neighbour heuristic:
    - Start at 'entry'
    - Repeatedly pick the closest unvisited item
    - Finally pick the closest checkout
    Returns (order, total_cost).
    """
    order: list[str] = [entry]
    current = entry
    remaining = set(items)
    total_cost = 0.0
    infinity = math.inf

    # Visit all items using Nearest Neighbour
    while remaining:
        # Find next item closest to current position
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


def run_algorithm(G: nx.Graph, entry: str, items: list[str], checkouts: list[str]):
    """
    Standard interface for the testbench / metrics.

    Input:
        G         - NetworkX graph with 'weight' on edges
        entry     - Entry node ID (str)
        items     - List of item node IDs (str)
        checkouts - List of checkout node IDs (str)

    Output (Dict):
        {
            "order": [...],          # e.g. ["21", "41", "61", "14"]
            "walk": [...],           # complete node sequence in the graph
            "total_distance": float  # total distance along 'order'
        }
    """
    relevant = [entry] + items + checkouts
    dist, spath = compute_pairwise_dijkstra(G, relevant)

    # Nearest Neighbour statt Branch & Bound
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

    # No path found
    if not best_order:
        return {
            "order": [],
            "walk": [],
            "total_distance": math.inf,
        }

    # Assemble walk from partial paths
    walk: list[str] = []
    for a, b in zip(best_order[:-1], best_order[1:]):
        seg = spath[a][b]
        walk.extend(seg if not walk else seg[1:])

    return {
        "order": best_order,
        "walk": walk,
        "total_distance": float(best_cost),
    }
