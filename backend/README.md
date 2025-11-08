# Backend Overview

This backend is intended to run on FastAPI. The core service exposes an HTTP endpoint that takes a list of product or node identifiers, runs the indoor navigation route calculation, and returns the result as JSON.

## Proposed API

- `GET /products` returns the full product catalog with ids, names, and shelf levels.
- `POST /route` accepts the selected product ids plus optional entry / checkout nodes and responds with:
  - the ordered stop sequence (entry, items, checkout),
  - the expanded node-by-node path with coordinates,
  - distance metadata for each segment and the total route length.

The JSON contract keeps the frontend decoupled from graph internals and allows other clients to reuse the routing logic.

## Running the API

1. Optional, but recommended: create and activate a Python virtual environment.
2. Install the dependencies: `pip install fastapi uvicorn networkx`.
3. Start the development server from the `backend` directory with:
  `uvicorn main:app --reload`
4. The API will be available at `http://127.0.0.1:8000/` and the interactive docs at `/docs`.

## Database Setup

1. From the project root, run `python src/database_init/setup_database.py`.
   - The script creates `backend/shopping.db`, creates all tables, imports the graph structure from `resources/shop_graph.graphml`,
     and loads the product catalog from `resources/id_products.csv`.
2. You can rerun the script at any time; it truncates and refreshes the data.
3. After the database exists, the API endpoints will read live data instead of mock responses.
