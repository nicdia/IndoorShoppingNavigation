# algorithm_custom_matrix_dijkstra.py
import math
import networkx as nx
from typing import Any, List, Tuple, Dict


# ------------------------------------------------------------
# Adjazenzmatrix aus NetworkX-Graph aufbauen
# ------------------------------------------------------------
def build_adjacency_matrix(G: nx.Graph, nodes: list[Any]) -> list[list[float]]:
    """
    G_mat[i][j] = weight, falls Kante existiert
                  0.0, falls keine Kante existiert
    """
    index = {node: i for i, node in enumerate(nodes)}
    n = len(nodes)
    G_mat = [[0.0 for _ in range(n)] for _ in range(n)]

    for u, v, data in G.edges(data=True):
        i = index[u]
        j = index[v]
        w = float(data.get("weight", 1.0))
        # ungerichtet
        G_mat[i][j] = w
        G_mat[j][i] = w

    return G_mat


# ------------------------------------------------------------
# Direkte Umsetzung deines Pseudocode-Dijkstra
# ------------------------------------------------------------
def multi_target_dijkstra_from_pseudocode(
    G: nx.Graph,
    entry: Any,
    targets: list[Any],
) -> Tuple[list[Any] | None, float]:
    """
    Implementiert deinen C#-ähnlichen Pseudocode exakt:

    S = entry
    für jedes T[i] in targets:
        führe Dijkstra auf Matrix aus
        rekonstruiere Pfad
        füge Pfad an L an
        S = T[i]

    Rückgabe:
        (L als NodeListe, Gesamtdistanz)
        oder (None, inf), falls ein Ziel unerreichbar ist
    """
    if not targets:
        return [entry], 0.0

    # fixe Node-Reihenfolge
    nodes = list(G.nodes())
    index = {node: i for i, node in enumerate(nodes)}

    G_mat = build_adjacency_matrix(G, nodes)
    n = len(G_mat)

    L_indices: list[int] = []
    total_distance = 0.0

    # S = entry
    S_idx = index[entry]

    for t in targets:
        T_idx = index[t]

        # ----------------------------
        # dein Dijkstra aus Pseudocode
        # ----------------------------
        distance = [math.inf] * n
        used = [False] * n
        previous: list[int | None] = [None] * n

        distance[S_idx] = 0.0

        while True:
            minDistance = math.inf
            minNode = -1

            # finde unbesuchten Knoten mit minimaler Entfernung
            for m in range(n):
                if (not used[m]) and (distance[m] < minDistance):
                    minDistance = distance[m]
                    minNode = m

            if minNode == -1 or minDistance == math.inf:
                break

            used[minNode] = True

            # relaxiere alle möglichen l
            for l in range(n):
                if G_mat[minNode][l] > 0:
                    shortestToMin = distance[minNode]
                    distToNext = G_mat[minNode][l]
                    totalDist = shortestToMin + distToNext
                    if totalDist < distance[l]:
                        distance[l] = totalDist
                        previous[l] = minNode

        # wenn unerreichbar → Algorithmus endet
        if distance[T_idx] == math.inf:
            return None, math.inf

        # Pfad Rückverfolgung
        nodes_path: list[int] = []
        current = T_idx
        while current is not None:
            nodes_path.append(current)
            current = previous[current]
        nodes_path.reverse()

        # Pfad in L einfügen
        if not L_indices:
            L_indices.extend(nodes_path)
        else:
            # Startknoten doppelt vermeiden
            L_indices.extend(nodes_path[1:])

        total_distance += distance[T_idx]

        # S = T[i]
        S_idx = T_idx

    # Indices → Node-IDs
    walk = [nodes[i] for i in L_indices]
    return walk, total_distance


# ------------------------------------------------------------
# Testbench-kompatible run_algorithm()-Schnittstelle
# ------------------------------------------------------------
def run_algorithm(
    G: nx.Graph,
    entry: str,
    items: list[str],
    checkouts: list[str],
) -> Dict[str, Any]:
    """
    Gleiche Schnittstelle wie algorithm_bnb.run_algorithm.

    Verhalten:
      - Items werden GENAU in gegebener Reihenfolge abgearbeitet
      - danach wird der beste Checkout mittels demselben Algorithmus gefunden
    """
    # Spezialfall: nichts zu tun
    if not items and not checkouts:
        return {
            "order": [entry],
            "walk": [entry],
            "total_distance": 0.0,
        }

    # 1) Entry → Items in Reihenfolge
    walk_items, dist_items = multi_target_dijkstra_from_pseudocode(G, entry, items)
    if walk_items is None or math.isinf(dist_items):
        return {
            "order": [],
            "walk": [],
            "total_distance": math.inf,
        }

    current = items[-1] if items else entry

    # 2) Bester Checkout
    best_checkout = None
    best_dist = math.inf
    best_walk_checkout: list[Any] | None = None

    if checkouts:
        for c in checkouts:
            w_c, d_c = multi_target_dijkstra_from_pseudocode(G, current, [c])
            if w_c is not None and d_c < best_dist:
                best_checkout = c
                best_dist = d_c
                best_walk_checkout = w_c

    # Wenn kein Checkout erreichbar ist → nur Items-Pfad
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
