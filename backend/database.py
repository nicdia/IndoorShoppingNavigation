from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List

BACKEND_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BACKEND_DIR / "shopping.db"


class DatabaseNotReadyError(RuntimeError):
    """Raised when the SQLite database file is missing."""


def _ensure_database_exists() -> None:
    if not DATABASE_PATH.exists():
        raise DatabaseNotReadyError(
            "SQLite database not found. Run `python src/database_init/setup_database.py` "
            "from the project root to create backend/shopping.db."
        )


@contextmanager
def get_connection():
    _ensure_database_exists()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def fetch_all_products() -> List[Dict[str, object]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                p.product_code AS code,
                p.product_name AS name,
                p.product_level AS level,
                pl.node_node_id AS node_id
            FROM products p
            LEFT JOIN product_locations pl ON pl.product_product_id = p.product_id
            ORDER BY p.product_name COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_products_by_codes(codes: Iterable[int]) -> List[Dict[str, object]]:
    code_list = list(dict.fromkeys(codes))  # remove duplicates, preserve order
    if not code_list:
        return []
    placeholders = ",".join(["?"] * len(code_list))
    query = f"""
        SELECT
            p.product_code AS code,
            p.product_name AS name,
            p.product_level AS level,
            pl.node_node_id AS node_id
        FROM products p
        LEFT JOIN product_locations pl ON pl.product_product_id = p.product_id
        WHERE p.product_code IN ({placeholders})
    """
    with get_connection() as conn:
        rows = conn.execute(query, code_list).fetchall()
    return [dict(row) for row in rows]
