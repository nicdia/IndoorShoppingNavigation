# Script to convert DXF file to a NetworkX graph 

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point
import matplotlib.pyplot as plt
import csv

# read the DXF file
edges_gdf = gpd.read_file(r"drawing_supermarket.dxf")

# Print the head of the graph file
print(edges_gdf.head())


# Identify the layer column 
layer_col = None
for c in edges_gdf.columns:
    if 'layer' in c.lower():
        layer_col = c
        break

# Filter the walkway from the walls and shelves

mask = edges_gdf[layer_col].astype(str).str.lower() == 'graph'
edges_in_graph = edges_gdf[mask].copy()
edges_gdf = edges_in_graph

# Create an empty graph
G = nx.Graph()

# Fill the graph with the edges from the DXF
for idx, row in edges_gdf.iterrows():
    geom = row.geometry
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        for a, b in zip(coords[:-1], coords[1:]):
            p1, p2 = tuple(a), tuple(b)
            G.add_node(p1, x=p1[0], y=p1[1])
            G.add_node(p2, x=p2[0], y=p2[1])
            G.add_edge(p1, p2, weight=Point(p1).distance(Point(p2)))

    elif geom.geom_type == "MultiLineString":
        for line in geom.geoms:
            coords = list(line.coords)
            for a, b in zip(coords[:-1], coords[1:]):
                p1, p2 = tuple(a), tuple(b)
                G.add_node(p1, x=p1[0], y=p1[1])
                G.add_node(p2, x=p2[0], y=p2[1])
                G.add_edge(p1, p2, weight=Point(p1).distance(Point(p2)))

# Split edges at nodes if nodes lie on edge without sharing a node
def point_on_segment(a, b, c, tol=1e-6):
    """
    Small Function to check if point c lies on segment ab within tolerance tol.
    """
    ax, ay = a
    bx, by = b
    cx, cy = c
    
    abx, aby = bx-ax, by-ay
    acx, acy = cx-ax, cy-ay
    
    cross = abx*acy - aby*acx
    if abs(cross) > tol:
        return False
    
    dot = abx*acx + aby*acy
    if dot < -tol:
        return False
    ab2 = abx*abx + aby*aby
    ac2 = acx*acx + acy*acy
    if ac2 - ab2 > tol:
        return False
    return True

# Function to split edges at nodes
def split_edges_at_nodes(G, tol=1e-6):
    """
    Splits edges in graph G at nodes that lie on the edge but are not endpoints.
    """

    edges_to_split = []
    for u, v in G.edges():
        # Check all other nodes
        for c in G.nodes():
            if c == u or c == v:
                continue
            if point_on_segment(u, v, c, tol):
                edges_to_split.append((u, v, c))
    # Split edges
    for u, v, c in edges_to_split:
        # Remove old edge
        if G.has_edge(u, v):
            G.remove_edge(u, v)
        # Add new edges
        G.add_edge(u, c, weight=Point(u).distance(Point(c)))
        G.add_edge(c, v, weight=Point(c).distance(Point(v)))
    print(f"Split: {len(edges_to_split)} edges split at nodes.")


split_edges_at_nodes(G)
print(f"Graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")



# remove any self-loop edges if errors in DXF
G.remove_edges_from(list(nx.selfloop_edges(G)))
# assign integer IDs to nodes and store as node attribute
for i, node in enumerate(G.nodes(), start=1):
    G.nodes[node]['id'] = i

# Create a new graph with integer node IDs 
H = nx.Graph()
for node in G.nodes():
    nid = G.nodes[node]['id']
    H.add_node(nid, x=G.nodes[node].get('x'), y=G.nodes[node].get('y'))
for u, v, edata in G.edges(data=True):
    uid = G.nodes[u]['id']
    vid = G.nodes[v]['id']
    attrs = dict(edata)
    H.add_edge(uid, vid, **attrs)


# Split edges at nodes for integer-ID 
def point_on_segment_xy(a, b, c, tol=1e-6):
    # a, b, c are tuples (x, y)
    ax, ay = a
    bx, by = b
    cx, cy = c
    abx, aby = bx-ax, by-ay
    acx, acy = cx-ax, cy-ay
    cross = abx*acy - aby*acx
    if abs(cross) > tol:
        return False
    dot = abx*acx + aby*acy
    if dot < -tol:
        return False
    ab2 = abx*abx + aby*aby
    ac2 = acx*acx + acy*acy
    if ac2 - ab2 > tol:
        return False
    return True

def split_edges_at_nodes_idgraph(H, tol=1e-6):
    next_id = max(H.nodes) + 1 if H.nodes else 1
    edges_to_split = []
    # Build lookup: id -> (x,y)
    id2xy = {nid: (data['x'], data['y']) for nid, data in H.nodes(data=True)}
    for u, v in list(H.edges()):
        a = id2xy[u]
        b = id2xy[v]
        for c_id, c_xy in id2xy.items():
            if c_id == u or c_id == v:
                continue
            if point_on_segment_xy(a, b, c_xy, tol):
                edges_to_split.append((u, v, c_id, c_xy))
    # For each split, remove edge and add two new edges
    for u, v, c_id, c_xy in edges_to_split:
        # Remove old edge
        if H.has_edge(u, v):
            w_uv = H[u][v].get('weight', 1.0)
            H.remove_edge(u, v)
        # If c_id already exists, use it. Else create new node
        if not H.has_node(c_id):
            H.add_node(next_id, x=c_xy[0], y=c_xy[1])
            c_id = next_id
            next_id += 1
        # Add new edges
        H.add_edge(u, c_id, weight=Point(id2xy[u]).distance(Point(c_xy)))
        H.add_edge(c_id, v, weight=Point(c_xy).distance(Point(id2xy[v])))
    print(f"Split (ID graph): {len(edges_to_split)} edges split at nodes.")

split_edges_at_nodes_idgraph(H)

# Add new edge because it was missing in first DXF
u_extra, v_extra = 113, 117
# calculate the weight (length) based on coordinates
x1, y1 = H.nodes[u_extra].get('x'), H.nodes[u_extra].get('y')
x2, y2 = H.nodes[v_extra].get('x'), H.nodes[v_extra].get('y')
try:
    w = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
except Exception:
    w = 1.0
H.add_edge(u_extra, v_extra, weight=w)


# Save the nodes ans edges to CSV files
nodes_csv = r'nodes.csv'
edges_csv = r'edges.csv'
with open(nodes_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'x', 'y'])
    for nid, data in H.nodes(data=True):
        writer.writerow([nid, data.get('x'), data.get('y')])

with open(edges_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['source', 'target', 'weight'])
    for u, v, data in H.edges(data=True):
        writer.writerow([u, v, data.get('weight')])

# Save as GraphML and GEXF files
try:
    nx.write_graphml(H, r'graph.graphml')
    nx.write_gexf(H, r'graph.gexf')
    print('Export: nodes.csv, edges.csv, graph.graphml, graph.gexf geschrieben.')
except Exception as e:
    print('Warnung: Konnte GraphML/GEXF nicht schreiben:', e)


# Show the graph
labels = {node: G.nodes[node]['id'] for node in G.nodes()}
pos = {node: (data['x'], data['y']) for node, data in G.nodes(data=True)}
nx.draw(G, pos, labels=labels, with_labels=True, node_size=50)
plt.show()
