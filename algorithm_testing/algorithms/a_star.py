from dijkstra_utils import build_graph_from_endpoints, haversine_distance_meters, plot_shortest_path
import osmnx as ox
import networkx as nx
import heapq
import math
from typing import Any, List, Tuple

def a_star(graph, origin, destination):
    """Compute shortest path using A* from scratch.

    Parameters:
    graph: networkx.MultiDiGraph (OSMnx graph)
    origin: node id or (lat, lon)
    destination: node id or (lat, lon)

    Returns:
    (path_nodes: List[node], total_length_meters: float)
    """
    def resolve_point_to_node(g: nx.MultiDiGraph, point: Any):
        if isinstance(point, (int, str)):
            return point
        try:
            lat, lon = point
            return ox.distance.nearest_nodes(g, X=lon, Y=lat)
        except Exception:
            raise ValueError("origin/destination must be a node id or (lat, lon) tuple")

    source_node = resolve_point_to_node(graph, origin)
    target_node = resolve_point_to_node(graph, destination)

    if source_node == target_node:
        return [source_node], 0.0

    # helper to get (lat, lon) of a node
    def node_coord(g: nx.MultiDiGraph, node_id) -> Tuple[float, float]:
        node_data = g.nodes[node_id]
        # OSMnx uses 'y' for lat and 'x' for lon
        return float(node_data.get('y')), float(node_data.get('x'))

    # heuristic: straight-line (haversine) distance from node to target
    target_coord = node_coord(graph, target_node)
    def heuristic(node_id) -> float:
        return haversine_distance_meters(node_coord(graph, node_id), target_coord)

    infinity = math.inf
    g_scores = {source_node: 0.0}  # cost from start to node
    f_scores = {source_node: heuristic(source_node)}  # g + h
    came_from = {}

    open_heap = [(f_scores[source_node], source_node)]

    while open_heap:
        current_f, current_node = heapq.heappop(open_heap)
        # If this f is outdated, skip
        if current_f > f_scores.get(current_node, infinity):
            continue

        if current_node == target_node:
            break

        # explore neighbors
        for neighbor_node, parallel_edges in graph[current_node].items():
            # consider each parallel edge
            for edge_attrs in parallel_edges.values():
                weight = edge_attrs.get('length', 1.0)
                if weight is None:
                    weight = 1.0
                tentative_g = g_scores.get(current_node, infinity) + float(weight)
                if tentative_g < g_scores.get(neighbor_node, infinity):
                    came_from[neighbor_node] = current_node
                    g_scores[neighbor_node] = tentative_g
                    f_scores[neighbor_node] = tentative_g + heuristic(neighbor_node)
                    heapq.heappush(open_heap, (f_scores[neighbor_node], neighbor_node))

    if target_node not in g_scores:
        return [], math.inf

    # reconstruct path
    path_nodes: List = []
    node = target_node
    while node != source_node:
        path_nodes.append(node)
        node = came_from.get(node)
        if node is None:
            return [], math.inf
    path_nodes.append(source_node)
    path_nodes.reverse()

    return path_nodes, g_scores[target_node]


if __name__ == "__main__":
    # Run Function in Alps
    # Region:
    # 46.3361, 11.71587

    # Start:
    # 46.31679104185598, 11.599813838236791

    # End:
    # 46.348286508364296, 11.844630489288898
    lat_start, lon_start = 46.31679104185598, 11.599813838236791
    lat_end, lon_end = 46.348286508364296, 11.844630489288898

    # Build graph using the start and end coordinates so the bounding area is computed
    # from the two points: distance, midpoint and buffer (0.66 * distance) are used.
    start_point = (lat_start, lon_start)
    end_point = (lat_end, lon_end)

    G, center, buffer_meters, straight_line_distance = build_graph_from_endpoints(
        start_point, end_point, buffer_ratio=0.66, network_type='drive')

    path, length = a_star(G, start_point, end_point)


    print(f"A* found path length {length:.1f} m with {len(path)} nodes")
    plot_shortest_path(G, path)