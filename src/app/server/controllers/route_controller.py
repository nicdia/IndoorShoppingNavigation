from flask import request, jsonify
from services.route_planner_service import plan_route_by_names

def compute_route():
    """
    Erwartet:
    {
      "product_names": ["Kiwi", "Apple", "Banana"]
    }
    """
    data = request.get_json(silent=True) or {}
    product_names = data.get("product_names")

    if not isinstance(product_names, list) or not product_names:
        return jsonify({"error": "product_names must be a non-empty list"}), 400

    try:
        res = plan_route_by_names(product_names)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": "route planning failed", "detail": str(e)}), 500