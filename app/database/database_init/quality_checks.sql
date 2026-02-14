-- Products + coordinates
SELECT p.product_name, n.node_x, n.node_y
FROM products p
JOIN product_locations pl ON pl.product_product_id = p.product_id
JOIN nodes n ON n.node_id = pl.node_node_id
LIMIT 10;

-- Isolated nodes (should be empty)
SELECT n.node_id
FROM nodes n
LEFT JOIN edges e ON e.node_source = n.node_id OR e.node_target = n.node_id
WHERE e.edge_id IS NULL;

-- Products per level
SELECT product_level, COUNT(*) FROM products GROUP BY product_level ORDER BY product_level;