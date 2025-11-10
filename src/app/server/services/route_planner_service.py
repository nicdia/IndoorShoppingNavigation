# services/route_planner_service.py
from typing import List, Dict, Any, Optional
import networkx as nx
from math import hypot
from db.db import fetch_edges, fetch_product_nodes_by_names

_GRAPH: Optional[nx.DiGraph] = None


def get_graph() -> nx.DiGraph:
    """
    Gerichteter Graph aus edges:
    - edge_bidirectional = 1 → beide Richtungen
    - edge_bidirectional = 0/NULL → nur source→target
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


def _euclid(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    return hypot(float(a["node_x"]) - float(b["node_x"]),
                 float(a["node_y"]) - float(b["node_y"]))


def plan_route_by_names(product_names: List[str]) -> Dict[str, Any]:
    """
    Route über echte Kanten (Dijkstra). Wenn ein Node vom aktuellen aus nicht erreichbar ist,
    wird ein neuer Teilpfad gestartet. Die Lücke wird als Segment mit `disconnected: true`
    und euklidischer Distanz markiert, damit Frontend/Debugging trotzdem eine komplette Reihenfolge sieht.
    Start: erster Produktknoten.
    """
    rows = fetch_product_nodes_by_names(product_names)
    if not rows:
        return {"total_cost": 0.0, "segments": [], "order": [], "way_nodes": [], "products": []}

    # Normalisiere Produkt-Daten
    products = [
        {
            "product_id": r["product_id"],
            "name": r["product_name"],
            "node_id": str(r["node_id"]),
            "node_x": r["node_x"],
            "node_y": r["node_y"],
        }
        for r in rows
    ]

    # Map: node_id -> full product dict (für schnelle Koordinatenlookups)
    node_info = {p["node_id"]: p for p in products}

    # Start = erster Produktknoten
    remaining = [p["node_id"] for p in products]
    route_nodes: List[str] = []
    segments: List[Dict[str, Any]] = []
    way_nodes: List[str] = []
    total_cost = 0.0

    if not remaining:
        return {"total_cost": 0.0, "segments": [], "order": [], "way_nodes": [], "products": []}

    G = get_graph()

    # Seed mit erstem Knoten
    current = remaining.pop(0)
    route_nodes.append(current)
    # way_nodes startet noch leer; füllen wir während der Segmente

    while remaining:
        # Kandidaten, die von 'current' erreichbar sind
        reachable = []
        for n in remaining:
            if current in G and n in G and nx.has_path(G, current, n):
                # sichere Länge via Dijkstra
                dist = nx.dijkstra_path_length(G, current, n, weight="weight")
                reachable.append((n, dist))

        if reachable:
            # Nächster via Graph-Distanz
            nxt = min(reachable, key=lambda x: x[1])[0]
            path_nodes = nx.dijkstra_path(G, current, nxt, weight="weight")
            cost = nx.dijkstra_path_length(G, current, nxt, weight="weight")
            total_cost += cost

            # way_nodes verketten ohne Doppelung
            if way_nodes and path_nodes and way_nodes[-1] == path_nodes[0]:
                way_nodes += path_nodes[1:]
            else:
                way_nodes += path_nodes

            segments.append({
                "from": current,
                "to": nxt,
                "cost": cost,
                "path": path_nodes,
                "disconnected": False
            })

            route_nodes.append(nxt)
            remaining.remove(nxt)
            current = nxt
        else:
            # Kein erreichbarer Kandidat → neue Komponente.
            # Wähle den nächstgelegenen (euklidisch) als neuen Start, markiere Segment als 'disconnected'.
            # (So siehst du die Lücke, bis Edges ergänzt/gerichtet sind.)
            if not remaining:
                break
            # wähle per Euklid von current zu jedem remaining (falls current nicht im node_info ist, nimm einfach remaining[0])
            if current in node_info:
                nxt = min(remaining, key=lambda n: _euclid(node_info[current], node_info[n]))
                eu_cost = _euclid(node_info[current], node_info[nxt])
            else:
                nxt = remaining[0]
                eu_cost = 0.0  # keine Koordinaten für current vorhanden

            # "teleport"-Segment rein, damit die Reihenfolge sichtbar bleibt
            segments.append({
                "from": current,
                "to": nxt,
                "cost": eu_cost,
                "path": [current, nxt],
                "disconnected": True
            })
            total_cost += eu_cost

            # neuer Start
            route_nodes.append(nxt)
            # way_nodes nur minimal erweitern (wir haben keinen echten Pfad)
            if way_nodes and way_nodes[-1] == current:
                way_nodes.append(nxt)
            else:
                way_nodes += [current, nxt]
            remaining.remove(nxt)
            current = nxt

    # Produkte in Besuchsreihenfolge
    node_to_products: Dict[str, List[Dict[str, Any]]] = {}
    for p in products:
        node_to_products.setdefault(p["node_id"], []).append({
            "product_id": p["product_id"],
            "name": p["name"],
            "node_id": p["node_id"]
        })
    ordered_products: List[Dict[str, Any]] = []
    for node in route_nodes:
        ordered_products += node_to_products.get(node, [])

    return {
        "total_cost": total_cost,
        "segments": segments,
        "order": route_nodes,
        "way_nodes": way_nodes,
        "products": ordered_products,
    }
