# CDSSSD algorithm, not evaulated because the path is set by the order of nodes given.
import math
import heapq
import networkx as nx
from typing import Any, Dict, List


def single_source_dijkstra_matrix(
    G_mat: list[list[float]],
    source_idx: int,
) -> tuple[list[float], list[int | None]]:

    n = len(G_mat)
    dist = [math.inf] * n
    used = [False] * n
    previous: list[int | None] = [None] * n

    dist[source_idx] = 0.0

    while True:
        min_distance = math.inf
        min_node = -1

        for m in range(n):
            if not used[m] and dist[m] < min_distance:
                min_distance = dist[m]
                min_node = m

        if min_node == -1 or min_distance is math.inf:
            break

        used[min_node] = True

        for l in range(n):
            if G_mat[min_node][l] > 0: 
                shortest_to_min = dist[min_node]
                dist_to_next = G_mat[min_node][l]
                total = shortest_to_min + dist_to_next
                if total < dist[l]:
                    dist[l] = total
                    previous[l] = min_node

    return dist, previous


def reconstruct_path(
    previous: list[int | None],
    target_idx: int,
) -> list[int] | None:
    """
    Reconstructs the path from 'target_idx' back to the source using 'previous'.
    Returns a list of node indices in the correct order, or None.
    """
    path: list[int] = []
    cur: int | None = target_idx

    while cur is not None:
        path.append(cur)
        cur = previous[cur]

    path.reverse()
    return path


def build_adjacency_matrix(G: nx.Graph, nodes: list[Any]) -> list[list[float]]:

    index = {node: i for i, node in enumerate(nodes)}
    n = len(nodes)
    G_mat = [[0.0 for _ in range(n)] for _ in range(n)]

    for u, v, data in G.edges(data=True):
        i = index[u]
        j = index[v]
        w = float(data.get("weight", 1.0))
        G_mat[i][j] = w
        G_mat[j][i] = w

    return G_mat


def multi_target_dijkstra_ordered(
    G: nx.Graph,
    entry: Any,
    targets: list[Any],
) -> tuple[list[Any] | None, float]:

    if not targets:
        return [entry], 0.0

    # fixed node ordering
    nodes = list(G.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    G_mat = build_adjacency_matrix(G, nodes)

    L_indices: list[int] = []
    total_distance = 0.0

    current = entry
    for t in targets:
        s_idx = index[current]
        t_idx = index[t]

        dist, prev = single_source_dijkstra_matrix(G_mat, s_idx)

        if math.isinf(dist[t_idx]):
            return None, math.inf

        path_idx = reconstruct_path(prev, t_idx)
        if path_idx is None:
            return None, math.inf

        # Accumulate distance
        total_distance += dist[t_idx]

        # Merge path into L (without duplicating start node)
        if not L_indices:
            L_indices.extend(path_idx)
        else:
            L_indices.extend(path_idx[1:])

        current = t 

    walk = [nodes[i] for i in L_indices]
    return walk, total_distance


def run_algorithm(
    G: nx.Graph,
    entry: str,
    items: list[str],
    checkouts: list[str],
) -> Dict[str, Any]:

    if not items and not checkouts:
        return {
            "order": [entry],
            "walk": [entry],
            "total_distance": 0.0,
        }

    walk_items, dist_items = multi_target_dijkstra_ordered(G, entry, items)

    if walk_items is None or math.isinf(dist_items):
        return {
            "order": [],
            "walk": [],
            "total_distance": math.inf,
        }

    current = items[-1] if items else entry

    best_checkout = None
    best_dist = math.inf
    best_walk_checkout: list[Any] | None = None

    if checkouts:
        for c in checkouts:
            walk_c, dist_c = multi_target_dijkstra_ordered(G, current, [c])
            if walk_c is not None and dist_c < best_dist:
                best_dist = dist_c
                best_checkout = c
                best_walk_checkout = walk_c

    if best_checkout is None or best_walk_checkout is None:
        order = [entry] + items
        walk = walk_items
        total_distance = dist_items
    else:
        order = [entry] + items + [best_checkout]
        walk = walk_items + best_walk_checkout[1:]
        total_distance = dist_items + best_dist

    return {
        "order": [str(n) for n in order],
        "walk": [str(n) for n in walk],
        "total_distance": float(total_distance),
    }
