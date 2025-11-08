# Backend Overview

This backend is intended to run on FastAPI. The core service exposes an HTTP endpoint that takes a list of product or node identifiers, runs the indoor navigation route calculation, and returns the result as JSON.

## Proposed API

- `GET /products` returns the full product catalog with ids, names, and shelf levels.
- `POST /route` accepts the selected product ids plus optional entry / checkout nodes and responds with:
  - the ordered stop sequence (entry, items, checkout),
  - the expanded node-by-node path with coordinates,
  - distance metadata for each segment and the total route length.

The JSON contract keeps the frontend decoupled from graph internals and allows other clients to reuse the routing logic.

## Next Steps

1. Wrap the existing `pathfinding` logic in FastAPI endpoints.
2. Document environment setup (virtual environment, required packages) once the first implementation is committed.
