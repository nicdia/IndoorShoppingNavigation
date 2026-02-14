-- import_products.sql
PRAGMA foreign_keys = ON;

-- Temporary staging table (matches CSV structure exactly)
DROP TABLE IF EXISTS products_staging;
CREATE TABLE products_staging (
  id      INTEGER,
  product TEXT,
  level   INTEGER
);

-- Import CSV (path adjusted)
.mode csv
.headers on
.import resources/id_products.csv products_staging

-- Copy into final table
INSERT INTO products (product_code, product_name, product_level)
SELECT id, product, level
FROM products_staging;

-- Cleanup
DROP TABLE products_staging;

-- Verification output
SELECT COUNT(*) AS rows_in_products FROM products;