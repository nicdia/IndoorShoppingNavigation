CREATE VIEW IF NOT EXISTS v_product_map AS
SELECT
  p.product_id,
  p.product_name,
  p.product_level,
  pl.node_node_id                 
  n.node_x,
  n.node_y
FROM products p
LEFT JOIN product_locations pl ON pl.product_product_id = p.product_id
LEFT JOIN nodes n              ON n.node_id            = pl.node_node_id;