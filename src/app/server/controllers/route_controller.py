from flask import request, jsonify
from services.route_planner_service import plan_route_by_names
from db.db import get_conn

def compute_route():
    """
    Erwartet Body:
      {
        "productCodes": [2, 3, 4]
      }
    oder alternativ:
      {
        "product_names": ["Kiwi","Apple","Banana"]
      }
    """
    data = request.get_json(silent=True) or {}

    # Prüfe, ob IDs oder Namen übergeben wurden
    product_codes = data.get("productCodes")
    product_names = data.get("product_names")

    # Wenn nur Codes kommen, hole die Namen aus DB
    if product_codes and not product_names:
        conn = get_conn()
        placeholders = ",".join(["?"] * len(product_codes))
        sql = f"SELECT product_name FROM v_product_map WHERE product_id IN ({placeholders})"
        cur = conn.execute(sql, product_codes)
        rows = [r[0] for r in cur.fetchall()]
        cur.close()
        product_names = rows

    if not product_names:
        return jsonify({"error": "No product names or codes provided"}), 400

    try:
        res = plan_route_by_names(product_names)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": "route planning failed", "detail": str(e)}), 500
