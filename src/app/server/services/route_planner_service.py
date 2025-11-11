# services/route_planner_service.py
from typing import List, Dict, Any, Optional
import networkx as nx
from math import hypot
from db.db import fetch_edges, fetch_product_nodes_by_names, fetch_node_coordinates_by_ids

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
            "node_x": float(r["node_x"]),
            "node_y": float(r["node_y"]),
        }
        for r in rows
    ]

    # Map: node_id -> full product dict (für schnelle Koordinatenlookups)
    node_info = {p["node_id"]: p for p in products}

    # Start = erster Produktknoten
    remaining = [str(p["node_id"]) for p in products]
    route_nodes: List[str] = []
    segments: List[Dict[str, Any]] = []
    way_nodes: List[str] = []
    total_cost = 0.0

    if not remaining:
        return {"total_cost": 0.0, "segments": [], "order": [], "way_nodes": [], "products": []}

    G = get_graph()

    # lightweight debug: show graph size and a sample of nodes (don't spam full list)
    try:
        sample_nodes = list(G.nodes())[:10]
        print(f"[route_planner] loaded graph: nodes={len(G.nodes())}, sample_nodes={sample_nodes}")
    except Exception as _e:
        print("[route_planner] could not inspect graph nodes", _e)

    # Seed mit erstem Knoten
    current = remaining.pop(0)
    route_nodes.append(current)
    # way_nodes startet noch leer; füllen wir während der Segmente

    while remaining:
        # Kandidaten, die von 'current' erreichbar sind
        reachable = []
        for n in remaining:
            n_str = str(n)
            in_graph_current = current in G
            in_graph_n = n_str in G
            path_exists = False
            try:
                path_exists = nx.has_path(G, current, n_str) if in_graph_current and in_graph_n else False
            except Exception as e:
                print(f"[route_planner] nx.has_path raised for {current}->{n_str}:", e)
                path_exists = False
            if path_exists:
                # sichere Länge via Dijkstra
                try:
                    dist = nx.dijkstra_path_length(G, current, n_str, weight="weight")
                    reachable.append((n_str, dist))
                except Exception as e:
                    print(f"[route_planner] dijkstra_path_length failed for {current}->{n_str}:", e)

        # debug summary for this iteration
        print(f"[route_planner] current={current} (in_graph={current in G}), remaining={remaining}")
        print(f"[route_planner] reachable_candidates={reachable}")

        if reachable:
            # Nächster via Graph-Distanz
            nxt = min(reachable, key=lambda x: x[1])[0]
            try:
                path_nodes = nx.dijkstra_path(G, current, nxt, weight="weight")
                cost = nx.dijkstra_path_length(G, current, nxt, weight="weight")
            except Exception as e:
                print(f"[route_planner] dijkstra failed for {current}->{nxt}:", e)
                path_nodes = [current, nxt]
                cost = float('inf')
            total_cost += cost if cost != float('inf') else 0.0

            print(f"[route_planner] chosen next={nxt}, path_nodes={path_nodes}, cost={cost}")

            # way_nodes verketten ohne Doppelung
            if way_nodes and path_nodes and way_nodes[-1] == path_nodes[0]:
                way_nodes += path_nodes[1:]
            else:
                way_nodes += path_nodes

            segments.append({
                "from": current,
                "to": nxt,
                "cost": cost,
                "path": [str(nid) for nid in path_nodes],
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
                print(f"[route_planner] no graph path: teleporting from {current} to {nxt} with euclid cost {eu_cost}")
            else:
                nxt = remaining[0]
                eu_cost = 0.0  # keine Koordinaten für current vorhanden

                print(f"[route_planner] no coords for current {current}, picking {nxt} as next (eu_cost=0)")

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
            "node_id": p["node_id"],
            "node_x": p["node_x"],
            "node_y": p["node_y"],
        })
    ordered_products: List[Dict[str, Any]] = []
    for node in route_nodes:
        ordered_products += node_to_products.get(node, [])

    coordinate_sources: Dict[str, Dict[str, float]] = {
        pid: {"x": float(prod["node_x"]), "y": float(prod["node_y"])}
        for pid, prod in node_info.items()
    }

    all_node_ids = set(way_nodes or []) | set(route_nodes)
    for segment in segments:
        for node_id in segment["path"]:
            all_node_ids.add(node_id)

    missing = [node_id for node_id in all_node_ids if node_id not in coordinate_sources]
    if missing:
        coordinate_sources.update(fetch_node_coordinates_by_ids(missing))

    segments_with_coords: List[Dict[str, Any]] = []
    for segment in segments:
        # Ensure segment['path'] is a list of all node ids along the edge-following path
        # (should already be the case for connected segments, but double-check)
        path_ids = list(segment["path"]) if "path" in segment and isinstance(segment["path"], (list, tuple)) else []
        # Defensive: if path is empty, but from/to exist, fill with [from, to]
        if not path_ids and segment.get("from") and segment.get("to"):
            path_ids = [str(segment["from"]), str(segment["to"])]
        # Build path_coordinates for every node in path
        path_coordinates = []
        for node_id in path_ids:
            coords = coordinate_sources.get(str(node_id))
            if coords:
                path_coordinates.append({"node_id": str(node_id), "x": coords["x"], "y": coords["y"]})
            else:
                path_coordinates.append({"node_id": str(node_id), "x": 0.0, "y": 0.0})
        enriched_segment = dict(segment)
        enriched_segment["path"] = path_ids
        enriched_segment["path_coordinates"] = path_coordinates
        segments_with_coords.append(enriched_segment)

    seen_waypoints = set()
    waypoint_coordinates = []
    for node_id in way_nodes:
        if node_id in coordinate_sources and node_id not in seen_waypoints:
            coords = coordinate_sources[node_id]
            waypoint_coordinates.append({"node_id": node_id, "x": coords["x"], "y": coords["y"]})
            seen_waypoints.add(node_id)

    return {
        "total_cost": total_cost,
        "segments": segments_with_coords,
        "order": route_nodes,
        "way_nodes": way_nodes,
        "products": ordered_products,
        "node_coordinates": coordinate_sources,
        "waypoint_coordinates": waypoint_coordinates,
    }
