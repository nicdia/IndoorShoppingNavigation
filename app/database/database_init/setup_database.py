#!/usr/bin/env python3
"""Create and populate the SQLite database for the indoor shopping navigation backend."""
from __future__ import annotations

import csv
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
RESOURCES_DIR = ROOT_DIR / "resources"

DATABASE_PATH = BACKEND_DIR / "shopping.db"
SCHEMA_SQL = Path(__file__).with_name("create_queries.sql")
PRODUCTS_CSV = RESOURCES_DIR / "id_products.csv"
GRAPHML = RESOURCES_DIR / "shop_graph.graphml"
GRAPH_NS = {"g": "http://graphml.graphdrawing.org/xmlns"}


def read_schema() -> str:
    return SCHEMA_SQL.read_text(encoding="utf-8")


def parse_graphml(path: Path) -> Tuple[List[Tuple[int, float, float]], List[Tuple[int, int, float]]]:
    tree = ET.parse(path)
    root = tree.getroot()

    key_map: Dict[str, str] = {elem.get("id"): elem.get("attr.name") for elem in root.findall("g:key", GRAPH_NS)}

    def get_attr(data_elements, key: str, default: str = "") -> str:
        for elem in data_elements:
            name = key_map.get(elem.get("key")) or elem.get("key")
            if name == key:
                return (elem.text or "").strip()
        return default

    nodes: List[Tuple[int, float, float]] = []
    for node in root.findall(".//g:node", GRAPH_NS):
        node_id = int(float(node.get("id")))
        data = node.findall("g:data", GRAPH_NS)
        x = float(get_attr(data, "x", "0"))
        y = float(get_attr(data, "y", "0"))
        nodes.append((node_id, x, y))

    edges: List[Tuple[int, int, float]] = []
    for edge in root.findall(".//g:edge", GRAPH_NS):
        source = int(float(edge.get("source")))
        target = int(float(edge.get("target")))
        data = edge.findall("g:data", GRAPH_NS)
        weight_raw = get_attr(data, "weight", get_attr(data, "length", "1"))
        try:
            weight = float(weight_raw)
        except ValueError:
            weight = 1.0
        edges.append((source, target, weight))

    return nodes, edges


def load_products(path: Path) -> List[Tuple[int, str, int]]:
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: List[Tuple[int, str, int]] = []
        for row in reader:
            try:
                code = int(row["id"])
            except (KeyError, TypeError, ValueError):
                continue
            name = row.get("product", "").strip()
            level_raw = row.get("level")
            level = int(level_raw) if level_raw not in (None, "") else None
            rows.append((code, name, level if level is not None else None))
    return rows


def main() -> None:
    BACKEND_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")

    print(f"Using database at {DATABASE_PATH}")
    with conn:
        conn.executescript(read_schema())

        nodes, edges = parse_graphml(GRAPHML)
        print(f"Parsed {len(nodes)} nodes and {len(edges)} edges from {GRAPHML.name}")

        conn.execute("DELETE FROM edges")
        conn.execute("DELETE FROM nodes")
        conn.executemany(
            "INSERT OR REPLACE INTO nodes (node_id, node_x, node_y) VALUES (?, ?, ?)",
            nodes,
        )
        conn.executemany(
            "INSERT INTO edges (node_source, node_target, edge_weight) VALUES (?, ?, ?)",
            edges,
        )

        products = load_products(PRODUCTS_CSV)
        print(f"Loaded {len(products)} products from {PRODUCTS_CSV.name}")

        conn.execute("DELETE FROM product_locations")
        conn.execute("DELETE FROM products")
        conn.executemany(
            "INSERT INTO products (product_code, product_name, product_level) VALUES (?, ?, ?)",
            products,
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO product_locations (product_product_id, node_node_id)
            SELECT p.product_id, p.product_code
            FROM products p
            JOIN nodes n ON n.node_id = p.product_code
            """
        )

    with conn:
        counts = {
            "nodes": conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
            "edges": conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
            "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "linked": conn.execute("SELECT COUNT(*) FROM product_locations WHERE node_node_id IS NOT NULL").fetchone()[0],
        }
    conn.close()

    print(
        "Database ready:",
        f"nodes={counts['nodes']}",
        f"edges={counts['edges']}",
        f"products={counts['products']}",
        f"linked_products={counts['linked']}",
    )


if __name__ == "__main__":
    main()
