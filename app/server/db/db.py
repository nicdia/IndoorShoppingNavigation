# db/db.py
import sqlite3
from flask import g
import os
from pathlib import Path

# __file__ = .../app/server/db/db.py
# parents[0] = db/, parents[1] = server/, parents[2] = app/, parents[3] = <repo-root>/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "indoor_shopping_nav.db"

DB_PATH = Path(os.environ.get("DB_PATH", str(DEFAULT_DB_PATH))).expanduser().resolve()

def get_conn():
    if "db_conn" not in g:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        g.db_conn = conn
        print("Using DB:", DB_PATH)
    return g.db_conn

def close_conn(_exc=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()

def fetch_product_nodes_by_names(product_names):
    if not product_names:
        return []

    lowered = [str(n).lower().strip() for n in product_names if str(n).strip()]
    if not lowered:
        return []

    placeholders = ",".join(["?"] * len(lowered))
    sql = f"""
        SELECT
            product_id,
            product_name,
            node_node_id AS node_id,
            node_x,
            node_y
        FROM v_product_map
        WHERE LOWER(product_name) IN ({placeholders})
    """
    cur = get_conn().execute(sql, lowered)
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]

def fetch_edges():
    sql = """
        SELECT
          node_source       AS source_node,
          node_target       AS target_node,
          edge_weight       AS weight,
          COALESCE(edge_bidirectional, 1) AS bidirectional
        FROM edges
    """
    cur = get_conn().execute(sql)
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]

def fetch_node_coordinates_by_ids(node_ids):
    if not node_ids:
        return {}

    cleaned = [str(node_id).strip() for node_id in node_ids if str(node_id).strip()]
    if not cleaned:
        return {}

    placeholders = ",".join(["?"] * len(cleaned))
    sql = f"""
        SELECT
            node_id,
            node_x,
            node_y
        FROM nodes
        WHERE node_id IN ({placeholders})
    """
    cur = get_conn().execute(sql, cleaned)
    rows = cur.fetchall()
    cur.close()
    return {
        str(row["node_id"]): {"x": float(row["node_x"]), "y": float(row["node_y"])}
        for row in rows
    }