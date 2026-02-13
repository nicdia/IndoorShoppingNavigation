# services/route_planner_service.py
from typing import List, Dict, Any, Optional, Tuple
import csv
import math
import os
from pathlib import Path

import networkx as nx
from math import hypot
import heapq

from db.db import fetch_edges, fetch_product_nodes_by_names, fetch_node_coordinates_by_ids

_GRAPH: Optional[nx.DiGraph] = None
_SHELF_SEGMENTS: Optional[Dict[Tuple[str, str], Dict[str, Optional[str]]]] = None

_ENTRY_COORDS_LOADED: bool = False  # print-diagnose: nur einmal loggen
_ASTARP_CACHE_DIAG_PRINTED: bool = False  # print-diagnose: nur einmal loggen

ENTRY_NODE_ID = os.environ.get("ENTRY_NODE_ID", "21").strip() or None
_CHECKOUT_RAW = os.environ.get("CHECKOUT_NODE_IDS", "14,15")
CHECKOUT_NODE_IDS = [n.strip() for n in _CHECKOUT_RAW.split(",") if n.strip()]


def _resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_shelf_segments_path() -> Path:
    override = os.environ.get("SHELF_SEGMENTS_PATH")
    if override:
        return Path(override)
    return _resolve_project_root() / "resources" / "shelf_segments.csv"


def _sanitize_shelf_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _load_shelf_segments() -> Dict[Tuple[str, str], Dict[str, Optional[str]]]:
    global _SHELF_SEGMENTS
    if _SHELF_SEGMENTS is not None:
        return _SHELF_SEGMENTS

    mapping: Dict[Tuple[str, str], Dict[str, Optional[str]]] = {}
    path = _resolve_shelf_segments_path()

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                source_raw = row.get("node_source")
                target_raw = row.get("node_target")
                source = str(source_raw).strip() if source_raw is not None else ""
                target = str(target_raw).strip() if target_raw is not None else ""
                if not source or not target:
                    continue
                left = _sanitize_shelf_id(row.get("left_shelf"))
                right = _sanitize_shelf_id(row.get("right_shelf"))
                mapping[(source, target)] = {"left": left, "right": right}
    except FileNotFoundError:
        print(f"[route_planner] shelf segment file not found at {path}. Continuing without shelf metadata.")
    except Exception as exc:
        print(f"[route_planner] failed to load shelf segments: {exc}")

    _SHELF_SEGMENTS = mapping
    return mapping


def _resolve_edge_shelves(
    source: str,
    target: str,
    shelf_segments: Dict[Tuple[str, str], Dict[str, Optional[str]]],
) -> Dict[str, Optional[str]]:
    if not shelf_segments:
        return {"left": None, "right": None}

    key = (source, target)
    if key in shelf_segments:
        entry = shelf_segments[key]
        return {"left": entry.get("left"), "right": entry.get("right")}

    reverse = (target, source)
    if reverse in shelf_segments:
        entry = shelf_segments[reverse]
        return {"left": entry.get("right"), "right": entry.get("left")}

    return {"left": None, "right": None}


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

    # NEW: A* pairwise
    dist_cache, path_cache = _compute_pairwise_astar_paths(G, relevant_nodes)

    route_nodes: List[str] = []
    planned_cost = math.inf

    if entry_node and (unique_product_nodes or checkout_nodes):
        if len(unique_product_nodes) > 20:
            route_nodes, planned_cost = _build_entry_to_checkout_sequence_eamdsp(
                entry_node, unique_product_nodes, checkout_nodes, dist_cache, path_cache
            )
        else:
            route_nodes, planned_cost = _build_entry_to_checkout_sequence_astar_bnb(
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

    shelf_segments = _load_shelf_segments()

    segments_with_coords: List[Dict[str, Any]] = []
    for segment in segments:
        path_ids = list(segment["path"]) if "path" in segment and isinstance(segment["path"], (list, tuple)) else []
        if not path_ids and segment.get("from") and segment.get("to"):
            path_ids = [str(segment["from"]), str(segment["to"])]

        path_coordinates = []
        for node_id in path_ids:
            coords = coordinate_sources.get(str(node_id))
            if coords:
                path_coordinates.append({"node_id": str(node_id), "x": coords["x"], "y": coords["y"]})
            else:
                path_coordinates.append({"node_id": str(node_id), "x": 0.0, "y": 0.0})

        edge_annotations: List[Dict[str, Any]] = []
        for source, target in zip(path_ids, path_ids[1:]):
            source_id = str(source)
            target_id = str(target)

            if G.has_edge(source_id, target_id):
                edge_length = float(G[source_id][target_id].get("weight", 0.0) or 0.0)
            else:
                coords_a = coordinate_sources.get(source_id)
                coords_b = coordinate_sources.get(target_id)
                if coords_a and coords_b:
                    edge_length = hypot(coords_b["x"] - coords_a["x"], coords_b["y"] - coords_a["y"])
                else:
                    base = node_info.get(source_id)
                    dest = node_info.get(target_id)
                    if base and dest:
                        edge_length = _euclid(base, dest)
                    else:
                        edge_length = 0.0

            shelf_info = _resolve_edge_shelves(source_id, target_id, shelf_segments)
            edge_annotations.append({
                "from": source_id,
                "to": target_id,
                "length": edge_length,
                "left_shelf": shelf_info.get("left"),
                "right_shelf": shelf_info.get("right"),
            })

        enriched_segment = dict(segment)
        enriched_segment["path"] = path_ids
        enriched_segment["path_coordinates"] = path_coordinates
        enriched_segment["path_edges"] = edge_annotations
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
        "planned_cost": planned_cost,  # diagnose: cost from BnB (should match total_cost for connected)
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


# ======================================================================
#  Branch & Bound + A*
# ======================================================================

def _node_coord(graph: nx.Graph, node: str) -> Optional[Tuple[float, float]]:
    data = graph.nodes.get(node, {})
    if "x" in data and "y" in data:
        return float(data["x"]), float(data["y"])
    return None


def _heuristic(graph: nx.Graph, u: str, v: str) -> float:
    cu = _node_coord(graph, u)
    cv = _node_coord(graph, v)
    if cu is None or cv is None:
        return 0.0
    x1, y1 = cu
    x2, y2 = cv
    return math.hypot(x2 - x1, y2 - y1)


def _astar(graph: nx.Graph, origin: str, destination: str) -> Tuple[List[str], float]:
    if origin == destination:
        return [origin], 0.0

    infinity = math.inf
    g_score: Dict[str, float] = {origin: 0.0}
    f_score: Dict[str, float] = {origin: _heuristic(graph, origin, destination)}
    came_from: Dict[str, str] = {}

    open_heap: List[Tuple[float, str]] = [(f_score[origin], origin)]

    while open_heap:
        current_f, u = heapq.heappop(open_heap)
        if current_f > f_score.get(u, infinity):
            continue

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

    path: List[str] = []
    cur = destination
    while cur != origin:
        path.append(cur)
        cur = came_from.get(cur)
        if cur is None:
            return [], math.inf
    path.append(origin)
    path.reverse()

    return path, float(g_score[destination])


def _compute_pairwise_astar_paths(
    graph: nx.DiGraph,
    nodes: List[str],
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, List[str]]]]:
    global _ENTRY_COORDS_LOADED, _ASTARP_CACHE_DIAG_PRINTED

    # Ensure coords exist for nodes used in A*
    missing_xy = [n for n in nodes if "x" not in graph.nodes.get(n, {}) or "y" not in graph.nodes.get(n, {})]
    coords_added = 0

    if missing_xy:
        coords = fetch_node_coordinates_by_ids(missing_xy)
        for node_id, xy in coords.items():
            if node_id in graph:
                graph.nodes[node_id]["x"] = float(xy["x"])
                graph.nodes[node_id]["y"] = float(xy["y"])
                coords_added += 1

    if not _ASTARP_CACHE_DIAG_PRINTED:
        present_xy = sum(
            1 for n in nodes
            if "x" in graph.nodes.get(n, {}) and "y" in graph.nodes.get(n, {})
        )
        print(
            "[route_planner][A* DIAG] relevant_nodes=",
            len(nodes),
            " coords_present=",
            present_xy,
            " coords_missing_before=",
            len(missing_xy),
            " coords_fetched=",
            coords_added,
        )
        _ASTARP_CACHE_DIAG_PRINTED = True

    dist: Dict[str, Dict[str, float]] = {n: {} for n in nodes}
    spath: Dict[str, Dict[str, List[str]]] = {n: {} for n in nodes}

    for u in nodes:
        for v in nodes:
            if u == v:
                continue
            if u not in graph or v not in graph:
                dist[u][v] = math.inf
                spath[u][v] = []
                continue
            p, d = _astar(graph, u, v)
            dist[u][v] = d
            spath[u][v] = p

    return dist, spath


def _bnb_astar(
    current: str,
    remaining: List[str],
    cost: float,
    order_prefix: List[str],
    dist: Dict[str, Dict[str, float]],
    checkouts: List[str],
    best: Tuple[Optional[List[str]], float],
) -> Tuple[Optional[List[str]], float]:
    best_order, best_cost = best

    lb = _compute_mst_lower_bound(current, remaining, checkouts, dist)
    if cost + lb >= best_cost:

        return best_order, best_cost

    if not remaining:
        for c in checkouts:
            d = dist.get(current, {}).get(c, math.inf)
            total = cost + d
            if math.isfinite(total) and total < best_cost:
                best_order = order_prefix + [c]
                best_cost = total
        return best_order, best_cost

    for nxt in sorted(remaining, key=lambda x: dist.get(current, {}).get(x, math.inf)):
        d = dist.get(current, {}).get(nxt, math.inf)
        if not math.isfinite(d):
            continue
        new_remaining = [r for r in remaining if r != nxt]
        best_order, best_cost = _bnb_astar(
            nxt,
            new_remaining,
            cost + d,
            order_prefix + [nxt],
            dist,
            checkouts,
            (best_order, best_cost),
        )

    return best_order, best_cost

def _compute_mst_cost(nodes: List[str], dist: Dict[str, Dict[str, float]]) -> float:
    if len(nodes) <= 1:
        return 0.0

    in_tree = {nodes[0]}
    mst_cost = 0.0

    while len(in_tree) < len(nodes):
        best_distance = math.inf
        best_node = None

        for u in in_tree:
            for v in nodes:
                if v in in_tree:
                    continue
                d = dist.get(u, {}).get(v, math.inf)
                if d < best_distance:
                    best_distance = d
                    best_node = v

        if best_node is None:
            return math.inf

        in_tree.add(best_node)
        mst_cost += best_distance

    return mst_cost


def _compute_mst_lower_bound(
    current: str,
    remaining: List[str],
    checkouts: List[str],
    dist: Dict[str, Dict[str, float]],
) -> float:
    if not remaining:
        return 0.0

    min_to_remaining = min((dist.get(current, {}).get(r, math.inf) for r in remaining), default=math.inf)
    if not math.isfinite(min_to_remaining):
        return math.inf

    mst_cost = _compute_mst_cost(remaining, dist)
    if not math.isfinite(mst_cost):
        return math.inf

    min_to_checkout = min(
        (dist.get(r, {}).get(c, math.inf) for r in remaining for c in checkouts),
        default=math.inf,
    )
    if not math.isfinite(min_to_checkout):
        return math.inf

    return min_to_remaining + mst_cost + min_to_checkout


def _build_entry_to_checkout_sequence_astar_bnb(
    entry: str,
    items: List[str],
    checkouts: List[str],
    dist: Dict[str, Dict[str, float]],
) -> Tuple[List[str], float]:
    if not items:
        return _best_entry_checkout_only(entry, checkouts, dist)

    best_order, best_cost = _bnb_astar(
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


def _build_entry_to_checkout_sequence_eamdsp(
    entry: str,
    items: List[str],
    checkouts: List[str],
    dist: Dict[str, Dict[str, float]],
    path: Dict[str, Dict[str, List[str]]],
) -> Tuple[List[str], float]:
    if not items:
        return _best_entry_checkout_only(entry, checkouts, dist)

    remaining = list(items)
    current = entry
    item_order: List[str] = []
    walk: List[str] = [entry]
    total_cost = 0.0

    while remaining:
        reachable = [n for n in remaining if math.isfinite(dist.get(current, {}).get(n, math.inf))]
        if not reachable:
            return [], math.inf

        next_item = min(reachable, key=lambda n: dist.get(current, {}).get(n, math.inf))
        segment = list(path.get(current, {}).get(next_item, []))
        segment_cost = dist.get(current, {}).get(next_item, math.inf)

        if not segment or not math.isfinite(segment_cost):
            return [], math.inf

        if walk and segment[0] == walk[-1]:
            walk.extend(segment[1:])
        else:
            walk.extend(segment)

        total_cost += segment_cost
        item_order.append(next_item)
        remaining.remove(next_item)
        current = next_item

    best_checkout = None
    best_checkout_cost = math.inf
    for checkout in checkouts:
        checkout_cost = dist.get(current, {}).get(checkout, math.inf)
        if math.isfinite(checkout_cost) and checkout_cost < best_checkout_cost:
            best_checkout = checkout
            best_checkout_cost = checkout_cost

    if best_checkout is None:
        return [], math.inf

    return [entry] + item_order + [best_checkout], total_cost + best_checkout_cost



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