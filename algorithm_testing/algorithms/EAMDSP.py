# algorithm_eamdsp.py
import math
import heapq
import networkx as nx
from typing import Any, List, Tuple, Dict


# -------------------------------------------------------------
# singleSourceSingleDestinationAlgorithm(G, S, T[i])
# → wir verwenden klassischen Dijkstra
# -------------------------------------------------------------
def dijkstra(graph: nx.Graph, origin: Any, destination: Any) -> Tuple[List[Any], float]:
    """
    Kürzester Pfad zwischen zwei Knoten (Pfad, Distanz).
    Entspricht singleSourceSingleDestinationAlgorithm im Pseudocode.
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

    # Pfad rekonstruieren
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
# Direkte Umsetzung des Pseudocodes (Algorithm 3: EAMDSP)
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
            L1, L2 neu initialisieren
        Return L3

    Rückgabe:
        L3: vollständiger Pfad (Knotenfolge) von S über alle Ziele
        total_distance: Summe der Gewichte entlang L3
    """
    # Wir machen T veränderbar
    remaining = list(T)

    L3: List[Any] = []  # finaler Pfad
    total_distance = 0.0
    current_S = S
    first_segment = True  # um doppelte Startknoten zu vermeiden

    while len(remaining) > 0:
        L1: List[Tuple[Any, float]] = []       # (dest, length_path)
        L2: List[Tuple[Any, Any]] = []         # (node_on_path, dest) für alle Kandidaten

        # For (i = 0; i < T.Length; i++)
        for dest in remaining:
            nodes_path, _ = dijkstra(G, current_S, dest)
            if not nodes_path or len(nodes_path) < 2:
                # Kein Pfad oder trivial – überspringen
                continue

            # length_path: Summe der Kanten-Gewichte entlang dieses Pfades
            length_path = 0.0
            for j in range(len(nodes_path) - 1):
                u = nodes_path[j]
                v = nodes_path[j + 1]
                w = float(G[u][v].get("weight", 1.0))
                length_path += w
                # Add L2->col1 := nodes_path[j], L2->col2 := T[i]
                L2.append((u, dest))
            # Letzten Knoten des Pfades noch hinzufügen, damit der Pfad vollständig ist
            L2.append((nodes_path[-1], dest))

            # Add L1->col1 := T[i], L1->col2 := length_path
            L1.append((dest, length_path))

        if not L1:
            # keine erreichbaren Ziele
            return [], math.inf

        # L1 sorting according to length_path
        L1.sort(key=lambda x: x[1])

        # e_Dest_Node := L1->col1 (mit minimaler length_path)
        e_Dest_Node, chosen_length = L1[0]

        # For (m = 0; m < L2.Length; m++)
        #   IF L2[m]->col2 == e_Dest_Node
        #       Add L3->col := L2[m]->col1
        #   End IF
        segment_nodes: List[Any] = [
            node for (node, dest) in L2 if dest == e_Dest_Node
        ]

        if not segment_nodes:
            # failsafe: sollte theoretisch nicht passieren
            return [], math.inf

        # Segment an L3 anhängen
        if first_segment:
            L3.extend(segment_nodes)
            first_segment = False
        else:
            # Ersten Knoten weglassen, falls er identisch mit letztem in L3 ist
            if segment_nodes[0] == L3[-1]:
                L3.extend(segment_nodes[1:])
            else:
                L3.extend(segment_nodes)

        # Distanz aufsummieren
        total_distance += chosen_length

        # S := e_Dest_Node
        current_S = e_Dest_Node
        # Remove the e_Dest_Node value from T
        remaining.remove(e_Dest_Node)
        # L1, L2 new initialize → erledigt, da wir sie in der Schleife neu anlegen

    return L3, float(total_distance)


# -------------------------------------------------------------
# run_algorithm mit gewohnter Schnittstelle
# -------------------------------------------------------------
def run_algorithm(
    G: nx.Graph,
    entry: str,
    items: List[str],
    checkouts: List[str],
):
    """
    Standard-Schnittstelle wie bei deinen anderen Algorithmen.

    Strategie:
      1. EAMDSP (Pseudocode) über alle Items → L3-Path und Distanz.
      2. Vom letzten Item mit Dijkstra zum nächstgelegenen Checkout.
      3. "order": [entry] + Item-Reihenfolge + Checkout
         "walk": kompletter Knoten-Weg (inkl. Checkout-Segment)
    """
    # Fall: es gibt Items → Algorithmus 3 auf Items
    if items:
        # Pfad vom Entry über alle Items (in EAMDSP-Reihenfolge)
        walk_items, dist_items = eamdsp_from_pseudocode(G, entry, items)

        if not walk_items or not math.isfinite(dist_items):
            return {
                "order": [],
                "walk": [],
                "total_distance": math.inf,
            }

        # Item-Reihenfolge aus dem Pfad extrahieren:
        # alle Knoten aus 'items' in der Reihenfolge ihres ersten Auftretens
        seen = set()
        item_order: List[str] = []
        for node in walk_items:
            if node in items and node not in seen:
                seen.add(node)
                item_order.append(node)

        if not item_order:
            # Falls der Pfad keine Items enthält (sollte nicht vorkommen)
            return {
                "order": [],
                "walk": [],
                "total_distance": math.inf,
            }

        last_node = item_order[-1]

        # Nächstgelegenen Checkout von diesem letzten Item suchen
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

        # Gesamtreihenfolge: Entry + Items (in berechneter Reihenfolge) + Checkout
        full_order = [entry] + item_order + [best_checkout]

        # Gesamt-Walk: EAMDSP-Weg + Checkout-Segment (ohne doppelten Startknoten)
        walk = list(walk_items)
        if best_path_to_checkout[0] == walk[-1]:
            walk.extend(best_path_to_checkout[1:])
        else:
            walk.extend(best_path_to_checkout)

        total_dist = dist_items + best_d

    # Fall: keine Items → direkt zum besten Checkout
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
