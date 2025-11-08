import networkx as nx
from typing import List, Dict, Any
from db.db import fetch_edges, fetch_product_nodes_by_names

_GRAPH = None

def get_graph() -> nx.DiGraph:
    """
    Baue einen gerichteten Graphen.
    Bei bidirektionalen Kanten (edge_bidirectional=1) fügen wir die Gegenrichtung ebenfalls hinzu.
    """
    global _GRAPH
    if _GRAPH is None:
        G = nx.DiGraph()
        for e in fetch_edges():
            u = str(e["source_node"])
            v = str(e["target_node"])
            w = float(e["weight"])
            bidir = int(e.get("bidirectional", 1)) == 1

            G.add_edge(u, v, weight=w)
            if bidir:
                G.add_edge(v, u, weight=w)
        _GRAPH = G
    return _GRAPH

def dijkstra_distance(G: nx.DiGraph, a: str, b: str) -> float:
    return nx.dijkstra_path_length(G, a, b, weight="weight")

def dijkstra_path(G: nx.DiGraph, a: str, b: str) -> List[str]:
    return nx.dijkstra_path(G, a, b, weight="weight")

def greedy_order(G: nx.DiGraph, start: str, targets: List[str]) -> List[str]:
    remaining = set(targets)
    order = []
    current = start
    while remaining:
        nearest = min(remaining, key=lambda t: dijkstra_distance(G, current, t))
        order.append(nearest)
        remaining.remove(nearest)
        current = nearest
    return order

def plan_route_by_names(product_names: List[str]) -> Dict[str, Any]:
    """
    Startpunkt = erster Produktknoten. Route via Dijkstra über echte edges.
    """
    G = get_graph()

    rows = fetch_product_nodes_by_names(product_names)
    if not rows:
        return {"total_cost": 0.0, "segments": [], "order": [], "way_nodes": [], "products": []}

    products = [
        {
            "product_id": r["product_id"],
            "name": r["product_name"],
            "node_id": str(r["node_id"]),
        }
        for r in rows
    ]

    # Start = erster Produktknoten
    route_nodes = [products[0]["node_id"]]
    remaining_nodes = [p["node_id"] for p in products[1:]]

    # greedy über Dijkstra-Distanzen
    if remaining_nodes:
        route_nodes += greedy_order(G, route_nodes[0], remaining_nodes)

    # Segmente und Kosten
    segments: List[Dict[str, Any]] = []
    way_nodes: List[str] = []
    total_cost = 0.0
    curr = route_nodes[0]

    for nxt in route_nodes[1:]:
        path_nodes = dijkstra_path(G, curr, nxt)
        cost = dijkstra_distance(G, curr, nxt)
        total_cost += cost

        if way_nodes and path_nodes and way_nodes[-1] == path_nodes[0]:
            way_nodes += path_nodes[1:]
        else:
            way_nodes += path_nodes

        segments.append({"from": curr, "to": nxt, "cost": cost, "path": path_nodes})
        curr = nxt

    # Produkte in Besuchsreihenfolge (per node_id mappen)
    node_to_products: Dict[str, List[Dict[str, Any]]] = {}
    for p in products:
        node_to_products.setdefault(p["node_id"], []).append(p)

    ordered_products: List[Dict[str, Any]] = []
    for n in route_nodes:
        ordered_products += node_to_products.get(n, [])

    return {
        "total_cost": total_cost,
        "segments": segments,
        "order": route_nodes,
        "way_nodes": way_nodes,
        "products": ordered_products,
    } 