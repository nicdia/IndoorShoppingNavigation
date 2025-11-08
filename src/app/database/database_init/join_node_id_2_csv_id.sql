PRAGMA foreign_keys=ON;

INSERT INTO product_locations (product_product_id, node_node_id)
SELECT p.product_id, p.product_code
FROM products p
JOIN nodes n ON n.node_id = p.product_code
ON CONFLICT(product_product_id) DO UPDATE
SET node_node_id = excluded.node_node_id;

SELECT
  (SELECT COUNT(*) FROM nodes) AS nodes,
  (SELECT COUNT(*) FROM edges) AS edges,
  (SELECT COUNT(*) FROM products) AS products,
  (SELECT COUNT(*) FROM product_locations WHERE node_node_id IS NOT NULL) AS linked_products;