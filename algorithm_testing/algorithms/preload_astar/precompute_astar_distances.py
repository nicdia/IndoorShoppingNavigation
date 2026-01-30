# precompute_astar_distances.py
"""
Berechnet paarweise A*-Distanzen für alle Produktknoten, Entry und Checkouts.
Speichert das Ergebnis in einer CSV-Datei.
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
# Precompute und Speichern
# -------------------------------------------------------------
def load_product_nodes(csv_path: str) -> list[str]:
    """Lädt alle einzigartigen Produkt-Node-IDs aus der CSV."""
    nodes = set()
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nodes.add(row["id"])
    return list(nodes)


def precompute_all_distances(G: nx.Graph, nodes: list[str]) -> dict:
    """Berechnet paarweise A*-Distanzen für alle Knoten."""
    dist = {}
    total = len(nodes) * (len(nodes) - 1)
    count = 0

    for u, v in itertools.permutations(nodes, 2):
        _, d = astar(G, u, v)
        if u not in dist:
            dist[u] = {}
        dist[u][v] = d
        count += 1
        if count % 1000 == 0:
            print(f"  {count}/{total} Paare berechnet...")

    return dist


def save_distances_csv(dist: dict, output_path: str):
    """Speichert Distanzmatrix als CSV (from, to, distance)."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["from", "to", "distance"])
        for u in dist:
            for v in dist[u]:
                writer.writerow([u, v, dist[u][v]])
    print(f"Distanzen gespeichert: {output_path}")


def load_distances_csv(csv_path: str) -> dict:
    """Lädt Distanzmatrix aus CSV."""
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
# Main
# -------------------------------------------------------------
def main():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Pfade
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    graph_path = os.path.join(base_dir, "..", "resources", "graph.graphml")
    products_csv = os.path.join(base_dir, "..", "resources", "id_products.csv")
    output_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precomputed_distances.csv")

    # Graph laden
    print("Lade Graph...")
    G = nx.read_graphml(graph_path)

    # Produktknoten laden
    print("Lade Produktknoten...")
    product_nodes = load_product_nodes(products_csv)

    # Entry und Checkout hinzufügen (anpassen falls andere IDs)
    entry = "1"
    checkouts = ["2"]

    all_nodes = list(set([entry] + product_nodes + checkouts))
    print(f"Anzahl relevanter Knoten: {len(all_nodes)}")

    # Distanzen berechnen
    print("Berechne paarweise A*-Distanzen...")
    dist = precompute_all_distances(G, all_nodes)

    # Speichern
    save_distances_csv(dist, output_csv)
    print("Fertig!")


if __name__ == "__main__":
    main()
