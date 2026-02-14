from flask import Flask, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from dotenv import load_dotenv
from routes.route import route_bp
from db.db import close_conn, get_conn
from pathlib import Path

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../<repo-root>/
DEFAULT_DB_PATH = PROJECT_ROOT / "indoor_shopping_nav.db"
DB_PATH = os.environ.get("DB_PATH", str(DEFAULT_DB_PATH))

print("Using database:", Path(DB_PATH).expanduser().resolve())

app = Flask(__name__)
# CORS: allow requests from the frontend port
CORS(
    app,
    resources={r"/*": {"origins": [
        "http://localhost:5173", "http://127.0.0.1:5173"
    ]}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"],
)
# Optional: no 308 redirect on missing trailing slash
app.url_map.strict_slashes = False
PORT = int(os.environ.get("PORT", 3001))


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.teardown_appcontext
def _close_db(exception):
    close_conn(exception)


@app.route("/api/dbtest")
def db_test():
    """Tests whether the view v_product_map is readable"""
    from db.db import fetch_product_nodes_by_names
    rows = fetch_product_nodes_by_names(["Kiwi", "Apple", "Banana"])
    return {"rows": rows}

@app.route("/products", methods=["GET"])
def list_products():
    conn = get_conn()
    sql = "SELECT product_id AS id, product_name AS name, product_level AS level, node_node_id AS nodeId FROM v_product_map"
    cur = conn.execute(sql)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    return jsonify({"items": rows})



# Register blueprint with all routing functions
app.register_blueprint(route_bp, url_prefix="/route")


if __name__ == "__main__":
    print(f"Server running at http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True) 