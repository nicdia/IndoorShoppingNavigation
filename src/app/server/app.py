from flask import Flask, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from dotenv import load_dotenv

from routes.route import route_bp      # ← dein echtes File
from db.db import close_conn

load_dotenv()
DB_PATH = os.environ.get("DB_PATH", "app.db")
print("📁 Verwende Datenbank:", os.path.abspath(DB_PATH))

app = Flask(__name__)
CORS(app)
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
    """Testet, ob die View v_product_map lesbar ist"""
    from db.db import fetch_product_nodes_by_names
    rows = fetch_product_nodes_by_names(["Kiwi", "Apple", "Banana"])
    return {"rows": rows}


# Blueprint mit allen Routing-Funktionen registrieren
app.register_blueprint(route_bp, url_prefix="/api/route")


if __name__ == "__main__":
    print(f"✅ Server läuft unter http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True) 