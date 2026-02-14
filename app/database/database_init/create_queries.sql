-- shop_nav_schema.sql
PRAGMA foreign_keys = ON;

-- === GRAPH ===
CREATE TABLE IF NOT EXISTS nodes (
  node_id INTEGER PRIMARY KEY,
  node_x  REAL,
  node_y  REAL
);

CREATE TABLE IF NOT EXISTS edges (
  edge_id           INTEGER PRIMARY KEY AUTOINCREMENT,
  node_source       INTEGER NOT NULL REFERENCES nodes(node_id),
  node_target       INTEGER NOT NULL REFERENCES nodes(node_id),
  edge_weight       REAL NOT NULL,
  edge_bidirectional INTEGER NOT NULL DEFAULT 1
);

-- === PRODUCTS ===
CREATE TABLE IF NOT EXISTS products (
  product_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  product_code   INTEGER,       -- CSV column "id"
  product_name   TEXT NOT NULL, -- CSV column "product"
  product_level  INTEGER        -- CSV column "level"
);

-- === PRODUCT LOCATIONS ===
CREATE TABLE IF NOT EXISTS product_locations (
  product_product_id INTEGER PRIMARY KEY REFERENCES products(product_id) ON DELETE CASCADE,
  node_node_id       INTEGER REFERENCES nodes(node_id)
);

