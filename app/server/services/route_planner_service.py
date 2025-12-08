# services/route_planner_service.py
from typing import List, Dict, Any, Optional, Tuple
import math
import os
import networkx as nx
from math import hypot
from db.db import fetch_edges, fetch_product_nodes_by_names, fetch_node_coordinates_by_ids

_GRAPH: Optional[nx.DiGraph] = None

ENTRY_NODE_ID = os.environ.get("ENTRY_NODE_ID", "21").strip() or None
_CHECKOUT_RAW = os.environ.get("CHECKOUT_NODE_IDS", "14,15")
CHECKOUT_NODE_IDS = [n.strip() for n in _CHECKOUT_RAW.split(",") if n.strip()]


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


def plan_route_by_names(product_names: List[str], start_node_id: Optional[str] = None) -> Dict[str, Any]:
    """Plane eine Route, die beim gewählten Startknoten beginnt und an einer Kasse endet."""
    rows = fetch_product_nodes_by_names(product_names)
    products: List[Dict[str, Any]] = []
    for r in rows:
        products.append({
            "product_id": r["product_id"],
            "name": r["product_name"],
            "node_id": str(r["node_id"]),
            "node_x": float(r["node_x"]),
            "node_y": float(r["node_y"]),
        })

    # Map: node_id -> Produkt / Knoten Infos
    node_info: Dict[str, Dict[str, Any]] = {p["node_id"]: dict(p) for p in products}

    entry_override = None
    if start_node_id is not None:
        entry_override = str(start_node_id).strip()
        if entry_override == "":
            entry_override = None

    entry_node = entry_override or ENTRY_NODE_ID
    checkout_nodes = CHECKOUT_NODE_IDS[:]

    extra_nodes = [n for n in [entry_node, *checkout_nodes] if n and n not in node_info]
    if extra_nodes:
        coords = fetch_node_coordinates_by_ids(extra_nodes)
        for node_id, xy in coords.items():
            node_info[node_id] = {
                "product_id": None,
                "name": None,
                "node_id": node_id,
                "node_x": xy["x"],
                "node_y": xy["y"],
            }

    product_nodes_order = [p["node_id"] for p in products]
    unique_product_nodes = _unique_order_preserving(product_nodes_order)

    G = get_graph()
    relevant_nodes: List[str] = _unique_order_preserving(
        [entry_node] + unique_product_nodes + checkout_nodes if entry_node else unique_product_nodes + checkout_nodes
    )

    dist_cache, path_cache = _compute_pairwise_shortest_paths(G, relevant_nodes)

    route_nodes: List[str] = []
    planned_cost = math.inf

    if entry_node and (unique_product_nodes or checkout_nodes):
        route_nodes, planned_cost = _build_entry_to_checkout_sequence(
            entry_node, unique_product_nodes, checkout_nodes, dist_cache
        )

    if not route_nodes:
        # Fallback: verwende Produkte in Eingabereihenfolge und hänge erste Kasse an
        fallback_nodes = []
        if entry_node:
            fallback_nodes.append(entry_node)
        fallback_nodes += unique_product_nodes
        if checkout_nodes:
            fallback_nodes.append(checkout_nodes[0])
        route_nodes = _unique_adjacent_preserving(fallback_nodes) if fallback_nodes else unique_product_nodes[:]

    segments, way_nodes, total_cost = _build_segments(
        route_nodes, path_cache, dist_cache, node_info
    )

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


def _unique_order_preserving(seq: List[Optional[str]]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in seq:
        if not item:
            continue
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _unique_adjacent_preserving(seq: List[str]) -> List[str]:
    """Entfernt nur direkt aufeinanderfolgende Duplikate, damit Entry==erstes Produkt sauber bleibt."""
    if not seq:
        return []
    cleaned = [seq[0]]
    for node in seq[1:]:
        if node != cleaned[-1]:
            cleaned.append(node)
    return cleaned


def _build_entry_to_checkout_sequence(
    entry: str,
    items: List[str],
    checkouts: List[str],
    dist: Dict[str, Dict[str, float]],
) -> Tuple[List[str], float]:
    if not items:
        return _best_entry_checkout_only(entry, checkouts, dist)

    best_order, best_cost = _bnb(
        current=entry,
        remaining=items,
        cost=0.0,
        order_prefix=[entry],
        dist=dist,
        checkouts=checkouts,
        best=(None, math.inf),
    )
    if best_order:
        return best_order, best_cost

    fallback = [entry] + items + ([checkouts[0]] if checkouts else [])
    return _unique_adjacent_preserving(fallback), math.inf


def _best_entry_checkout_only(
    entry: str,
    checkouts: List[str],
    dist: Dict[str, Dict[str, float]],
) -> Tuple[List[str], float]:
    best_checkout = None
    best_cost = math.inf
    for checkout in checkouts:
        d = dist.get(entry, {}).get(checkout, math.inf)
        if math.isfinite(d) and d < best_cost:
            best_checkout = checkout
            best_cost = d
    if best_checkout:
        return [entry, best_checkout], best_cost
    if checkouts:
        return _unique_adjacent_preserving([entry, checkouts[0]]), math.inf
    return [entry], 0.0


def _bnb(
    current: str,
    remaining: List[str],
    cost: float,
    order_prefix: List[str],
    dist: Dict[str, Dict[str, float]],
    checkouts: List[str],
    best: Tuple[Optional[List[str]], float],
) -> Tuple[Optional[List[str]], float]:
    best_order, best_cost = best
    if cost >= best_cost:
        return best_order, best_cost

    if not remaining:
        for checkout in checkouts:
            d = dist.get(current, {}).get(checkout, math.inf)
            total = cost + d
            if math.isfinite(total) and total < best_cost:
                best_order = order_prefix + [checkout]
                best_cost = total
        return best_order, best_cost

    sorted_remaining = sorted(
        remaining,
        key=lambda node: dist.get(current, {}).get(node, math.inf)
    )
    for nxt in sorted_remaining:
        d = dist.get(current, {}).get(nxt, math.inf)
        if not math.isfinite(d):
            continue
        new_remaining = [r for r in remaining if r != nxt]
        best_order, best_cost = _bnb(
            nxt,
            new_remaining,
            cost + d,
            order_prefix + [nxt],
            dist,
            checkouts,
            (best_order, best_cost),
        )
    return best_order, best_cost


def _compute_pairwise_shortest_paths(
    graph: nx.DiGraph,
    nodes: List[str],
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, List[str]]]]:
    dist: Dict[str, Dict[str, float]] = {n: {} for n in nodes}
    spath: Dict[str, Dict[str, List[str]]] = {n: {} for n in nodes}
    for source in nodes:
        if source not in graph:
            continue
        try:
            lengths, paths = nx.single_source_dijkstra(graph, source, weight="weight")
        except Exception as exc:
            print(f"[route_planner] single_source_dijkstra failed for {source}: {exc}")
            continue
        for target in nodes:
            if target == source:
                continue
            if target in lengths:
                dist[source][target] = lengths[target]
                spath[source][target] = [str(nid) for nid in paths[target]]
            else:
                dist[source][target] = math.inf
                spath[source][target] = []
    return dist, spath


def _build_segments(
    route_nodes: List[str],
    path_cache: Dict[str, Dict[str, List[str]]],
    dist_cache: Dict[str, Dict[str, float]],
    node_info: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str], float]:
    segments: List[Dict[str, Any]] = []
    way_nodes: List[str] = []
    total_cost = 0.0

    for a, b in zip(route_nodes[:-1], route_nodes[1:]):
        path_nodes = list(path_cache.get(a, {}).get(b, []))
        cost = dist_cache.get(a, {}).get(b, math.inf)
        disconnected = not path_nodes or not math.isfinite(cost)

        if disconnected:
            base = node_info.get(a)
            target = node_info.get(b)
            if base and target:
                cost = _euclid(base, target)
            else:
                cost = 0.0
            path_nodes = [a, b]

        total_cost += cost

        if way_nodes and path_nodes and way_nodes[-1] == path_nodes[0]:
            way_nodes += path_nodes[1:]
        else:
            way_nodes += path_nodes

        segments.append({
            "from": a,
            "to": b,
            "cost": cost,
            "path": path_nodes,
            "disconnected": disconnected,
        })

    return segments, way_nodes, total_cost
