# db/db.py
import sqlite3
from flask import g
import os

DB_PATH = os.environ.get("DB_PATH", "app.db")

def get_conn():
    if "db_conn" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db_conn = conn
    return g.db_conn

def close_conn(_exc=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()

def fetch_product_nodes_by_names(product_names):
    """
    Holt zu Produktnamen (case-insensitive) die Knoten aus v_product_map.
    Rückgabe: [{product_id, product_name, node_id, node_x, node_y}, ...]
    """
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
    """
    Liest Kanten aus edges und aliasiert Spalten so, dass der Service sie versteht.
    """
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