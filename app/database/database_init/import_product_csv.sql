-- import_products.sql
PRAGMA foreign_keys = ON;

-- Temporäre Staging-Tabelle (exakt wie CSV)
DROP TABLE IF EXISTS products_staging;
CREATE TABLE products_staging (
  id      INTEGER,
  product TEXT,
  level   INTEGER
);

-- CSV importieren (Pfad angepasst)
.mode csv
.headers on
.import resources/id_products.csv products_staging

-- In finale Tabelle kopieren
INSERT INTO products (product_code, product_name, product_level)
SELECT id, product, level
FROM products_staging;

-- Aufräumen
DROP TABLE products_staging;

-- Kontrollausgabe
SELECT COUNT(*) AS rows_in_products FROM products;