# algorithm_eamdsp.py
import math
import heapq
import networkx as nx
from typing import Any, List, Tuple, Dict


# -------------------------------------------------------------
# singleSourceSingleDestinationAlgorithm(G, S, T[i])
# using classic Dijkstra
# -------------------------------------------------------------
def dijkstra(graph: nx.Graph, origin: Any, destination: Any) -> Tuple[List[Any], float]:
    """
    Shortest path between two nodes (path, distance).
    Corresponds to singleSourceSingleDestinationAlgorithm in the pseudocode.
    """
    if origin == destination:
        return [origin], 0.0

    infinity = math.inf
    dist: Dict[Any, float] = {origin: 0.0}
    prev: Dict[Any, Any] = {}
    pq: List[Tuple[float, Any]] = [(0.0, origin)]

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

    # Reconstruct path
    path: List[Any] = []
    cur = destination
    while cur != origin:
        path.append(cur)
        cur = prev.get(cur)
        if cur is None:
            return [], math.inf
    path.append(origin)
    path.reverse()
    return path, dist[destination]


# -------------------------------------------------------------
# Direct implementation of the pseudocode (Algorithm 3: EAMDSP)
# -------------------------------------------------------------
def eamdsp_from_pseudocode(
    G: nx.Graph,
    S: Any,
    T: List[Any],
) -> Tuple[List[Any], float]:
    """
    Implementiert den Pseudocode:

        Declare: L1, L2, L3
        While (T.Length > 0)
            For i in T:
                nodes_path := singleSourceSingleDestinationAlgorithm(G, S, T[i])
                For j in nodes_path:
                    length_path += G[nodes_path[j], nodes_path[j+1]]
                    Add L2(col1:=nodes_path[j], col2:=T[i])
                Add L1(col1:=T[i], col2:=length_path)
            sort L1 by length_path
            e_Dest_Node := L1.col1 (kleinster length_path)
            For m in L2:
                If L2[m].col2 == e_Dest_Node:
                    Add L3.col := L2[m].col1
            S := e_Dest_Node
            remove e_Dest_Node from T
            reinitialize L1, L2
        Return L3

    Returns:
        L3: complete path (node sequence) from S through all destinations
        total_distance: sum of weights along L3
    """
    # Make T mutable
    remaining = list(T)

    L3: List[Any] = []  # final path
    total_distance = 0.0
    current_S = S
    first_segment = True  # avoid duplicate start nodes

    while len(remaining) > 0:
        L1: List[Tuple[Any, float]] = []       # (dest, length_path)
        L2: List[Tuple[Any, Any]] = []         # (node_on_path, dest) for all candidates

        # For (i = 0; i < T.Length; i++)
        for dest in remaining:
            nodes_path, _ = dijkstra(G, current_S, dest)
            if not nodes_path or len(nodes_path) < 2:
                # No path or trivial, skip
                continue

            # length_path: sum of edge weights along this path
            length_path = 0.0
            for j in range(len(nodes_path) - 1):
                u = nodes_path[j]
                v = nodes_path[j + 1]
                w = float(G[u][v].get("weight", 1.0))
                length_path += w
                # Add L2->col1 := nodes_path[j], L2->col2 := T[i]
                L2.append((u, dest))
            # Add the last node of the path to keep it complete
            L2.append((nodes_path[-1], dest))

            # Add L1->col1 := T[i], L1->col2 := length_path
            L1.append((dest, length_path))

        if not L1:
            # no reachable targets
            return [], math.inf

        # L1 sorting according to length_path
        L1.sort(key=lambda x: x[1])

        # e_Dest_Node := L1->col1 (with minimal length_path)
        e_Dest_Node, chosen_length = L1[0]

        # For (m = 0; m < L2.Length; m++)
        #   IF L2[m]->col2 == e_Dest_Node
        #       Add L3->col := L2[m]->col1
        #   End IF
        segment_nodes: List[Any] = [
            node for (node, dest) in L2 if dest == e_Dest_Node
        ]

        if not segment_nodes:
            # failsafe: should not happen in theory
            return [], math.inf

        # Append segment to L3
        if first_segment:
            L3.extend(segment_nodes)
            first_segment = False
        else:
            # Skip first node if identical to last node in L3
            if segment_nodes[0] == L3[-1]:
                L3.extend(segment_nodes[1:])
            else:
                L3.extend(segment_nodes)

        # Accumulate distance
        total_distance += chosen_length

        # S := e_Dest_Node
        current_S = e_Dest_Node
        # Remove the e_Dest_Node value from T
        remaining.remove(e_Dest_Node)
        # L1, L2 reinitialized at the start of each loop iteration

    return L3, float(total_distance)


# -------------------------------------------------------------
# run_algorithm with standard interface
# -------------------------------------------------------------
def run_algorithm(
    G: nx.Graph,
    entry: str,
    items: List[str],
    checkouts: List[str],
):
    """
    Standard interface matching the other algorithms.

    Strategy:
      1. EAMDSP (pseudocode) over all items to get the L3 path and distance.
      2. From the last item, use Dijkstra to reach the nearest checkout.
      3. "order": [entry] + item order + checkout
         "walk": complete node path (including checkout segment)
    """
    # Case: items present, run Algorithm 3 on items
    if items:
        # Path from entry through all items (in EAMDSP order)
        walk_items, dist_items = eamdsp_from_pseudocode(G, entry, items)

        if not walk_items or not math.isfinite(dist_items):
            return {
                "order": [],
                "walk": [],
                "total_distance": math.inf,
            }

        # Extract item order from the path:
        # all nodes from 'items' in their order of first occurrence
        seen = set()
        item_order: List[str] = []
        for node in walk_items:
            if node in items and node not in seen:
                seen.add(node)
                item_order.append(node)

        if not item_order:
            # If the path contains no items (should not happen)
            return {
                "order": [],
                "walk": [],
                "total_distance": math.inf,
            }

        last_node = item_order[-1]

        # Find the nearest checkout from this last item
        best_checkout = None
        best_d = math.inf
        best_path_to_checkout: List[Any] | None = None

        for c in checkouts:
            path_c, dist_c = dijkstra(G, last_node, c)
            if not path_c or not math.isfinite(dist_c):
                continue
            if dist_c < best_d:
                best_d = dist_c
                best_path_to_checkout = path_c
                best_checkout = c

        if best_checkout is None or best_path_to_checkout is None:
            return {
                "order": [],
                "walk": [],
                "total_distance": math.inf,
            }

        # Full order: entry + items (in computed order) + checkout
        full_order = [entry] + item_order + [best_checkout]

        # Full walk: EAMDSP path + checkout segment (without duplicate start node)
        walk = list(walk_items)
        if best_path_to_checkout[0] == walk[-1]:
            walk.extend(best_path_to_checkout[1:])
        else:
            walk.extend(best_path_to_checkout)

        total_dist = dist_items + best_d

    # Case: no items, go directly to the best checkout
    else:
        best_checkout = None
        best_d = math.inf
        best_path = None
        for c in checkouts:
            p, d = dijkstra(G, entry, c)
            if not p or not math.isfinite(d):
                continue
            if d < best_d:
                best_d = d
                best_path = p
                best_checkout = c

        if best_checkout is None or best_path is None:
            return {
                "order": [],
                "walk": [],
                "total_distance": math.inf,
            }

        full_order = [entry, best_checkout]
        walk = best_path
        total_dist = best_d

    return {
        "order": [str(n) for n in full_order],
        "walk": [str(n) for n in walk],
        "total_distance": float(total_dist),
    }
