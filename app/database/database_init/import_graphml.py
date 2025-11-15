#!/usr/bin/env python3
import sqlite3, xml.etree.ElementTree as ET

DB = "indoor_shopping_nav.db"
GRAPHML = "resources/graph.graphml"
NS = {"g": "http://graphml.graphdrawing.org/xmlns"}

def to_int(v):
    try: return int(float(v))
    except: return None

def to_float(v):
    try: return float(v)
    except: return None

# GraphML parsen
tree = ET.parse(GRAPHML)
root = tree.getroot()

# key-id -> attr.name
key_map = {}
for k in root.findall("g:key", NS):
    key_map[k.get("id")] = k.get("attr.name")

nodes, edges = [], []

for n in root.findall(".//g:node", NS):
    data = {"id": n.get("id")}
    for d in n.findall("g:data", NS):
        name = key_map.get(d.get("key")) or d.get("key")
        data[name] = (d.text or "").strip()
    nodes.append(data)

for e in root.findall(".//g:edge", NS):
    data = {"source": e.get("source"), "target": e.get("target")}
    for d in e.findall("g:data", NS):
        name = key_map.get(d.get("key")) or d.get("key")
        data[name] = (d.text or "").strip()
    edges.append(data)

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON;")

with con:
    # nodes: (node_id, node_x, node_y)
    con.executemany(
        "INSERT OR REPLACE INTO nodes (node_id, node_x, node_y) VALUES (?,?,?)",
        [(to_int(n.get("id")), to_float(n.get("x")), to_float(n.get("y"))) for n in nodes]
    )

    # edges: (node_source, node_target, edge_weight)
    con.executemany(
        "INSERT INTO edges (node_source, node_target, edge_weight) VALUES (?,?,?)",
        [(to_int(e.get("source")), to_int(e.get("target")), float(e.get("weight") or 1.0)) for e in edges]
    )

cur = con.cursor()
print("nodes:", cur.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
print("edges:", cur.execute("SELECT COUNT(*) FROM edges").fetchone()[0])
con.close()