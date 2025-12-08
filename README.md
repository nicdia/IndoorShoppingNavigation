# Indoor Shopping Navigation

Indoor navigation prototype developed within the "Location Based Services" master course. The project consists of a FastAPI backend that currently serves mock data and a React (Vite + TypeScript) frontend that visualises the store layout, route, and shopping checklist.

---

## Prerequisites

- Python 3.10 or newer (tested with 3.11)
- Node.js 18 or newer (enables Vite and modern tooling)
- npm (ships with Node.js)

All commands below assume a Windows PowerShell shell. Adapt paths if your workspace differs.

---

<!-- ## Backend (FastAPI)

The backend serves mock responses for `/products` and `/route`. It is meant to mirror the structure of the future pathfinding service while the database integration is under development.

1. Change into the backend folder:
	```powershell
	cd .\backend
	```
2. (Recommended) Create and activate a virtual environment:
	```powershell
	python -m venv .venv
	.\.venv\Scripts\Activate.ps1
	```
3. Install dependencies:
	```powershell
	pip install fastapi uvicorn
	```
4. Start the development server:
	```powershell
	uvicorn main:app --reload --host 127.0.0.1 --port 8000
	```

The API will be available at `http://127.0.0.1:8000`. CORS is fully open for development so the frontend can talk to it without additional configuration.

### Endpoints

- `GET /products` – returns a list of mock products with ids, names, categories, and level metadata.
- `POST /route` – returns a static route payload (order, path geometry, segments, total distance, and metadata).

You can inspect these responses in a browser or via Swagger UI at `http://127.0.0.1:8000/docs` once the server is running.

--- -->

## Frontend (React + Vite)

The frontend lives in `app/frontend/` and visualises the store map, the current route, and the selected checklist items.

1. Change into the frontend folder:
	```powershell
  cd .\app\frontend
	```
2. Install dependencies (only needed once or whenever `package.json` changes):
	```powershell
	npm install
	```
3. Start the Vite dev server:
	```powershell
	npm run dev
	```
4. Open the local development URL printed by Vite (typically `http://127.0.0.1:5173`).

The frontend expects the backend at `http://127.0.0.1:8000` by default. To target another API base URL, create a `.env` file in `frontend/` and set `VITE_API_BASE_URL` (trailing slash optional):

```dotenv
VITE_API_BASE_URL=http://localhost:9000
```

### Static Layout Data

`app/frontend/public/layout.json` provides polygon data for drawing the store map. Adjust this file if the store layout changes; the frontend fetches it automatically on load.

### UX Behaviour

- The red marker represents the current shopper position. When an item is checked off in the checklist, the current position snaps to that item.
- The blue marker shows the next target.
- Route segments already travelled or still upcoming remain visible in light red, while the active leg is highlighted in solid red.

---

## Working on Both Services

Run backend and frontend in separate terminals for the best developer experience:

```powershell
# Terminal 1 (backend)
cd .\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload

# Terminal 2 (frontend)
cd .\app\frontend
npm run dev
```

The frontend fetches product lists and new routes from the backend automatically when the user moves between selection and route views. Ensure the backend endpoints return real data; there are no longer any frontend mock fallbacks.

---

## Troubleshooting

- **`npm run dev` fails immediately**: ensure dependencies are installed with `npm install` and that no other service uses port 5173.
- **Backend 404 or refused connections**: confirm `uvicorn` is running on port 8000 and the firewall allows local traffic.
- **Layout not rendered**: verify `frontend/public/layout.json` exists and contains valid JSON with a `polygons` array.

Feel free to extend both README instructions and mock payloads as the project evolves towards real indoor routing.



to do -- graph muss die exge tabelle erreichen + curl aufruf muss funktionieren 
curl -X POST http://localhost:3001/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"product_names":["Kiwi","Apple","Banana"]}'  

  Endpoints
  # Backend
Starten vom Hauptverzeichnis aus: python3 src/app/server/app.py  # → läuft auf http://127.0.0.1:8000

# Tests
curl http://127.0.0.1:8000/api/health

{
  "status": "ok",
  "timestamp": "2025-11-10T18:14:04.283608"
}



curl http://127.0.0.1:8000/products

{
  "items": [
    {
      "id": 2,
      "level": 99,
      "name": "Kiwi",
      "nodeId": 41
    },
    {
      "id": 3,
      "level": 99,
      "name": "Apple",
      "nodeId": 61
    },
    {
      "id": 4,
      "level": 99,
      "name": "Banana",
      "nodeId": 59
    },
    {
      "id": 5,
      "level": 99,
      "name": "Orange",
      "nodeId": 57
    },

curl -X POST http://127.0.0.1:8000/route -H "Content-Type: application/json" \
  -d '{"productCodes":[2,3,4]}'


  {
  "order": [
    "41",
    "61",
    "59"
  ],
  "products": [
    {
      "name": "Kiwi",
      "node_id": "41",
      "product_id": 2
    },
    {
      "name": "Apple",
      "node_id": "61",
      "product_id": 3
    },
    {
      "name": "Banana",
      "node_id": "59",
      "product_id": 4
    }
  ],
  "segments": [
    {
      "cost": 3.0,
      "disconnected": true,
      "from": "41",
      "path": [
        "41",
        "61"
      ],
      "to": "61"
    },
    {
      "cost": 4.0,
      "disconnected": true,
      "from": "61",
      "path": [
        "61",
        "59"
      ],
      "to": "59"
    }
  ],
  "total_cost": 7.0,
  "way_nodes": [
    "41",
    "61",
    "59"
  ]
}





MERMAID SEQUENZDIAGRAMM UML CODE 
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as Backend API (Flask)
    participant Controller as Route Controller
    participant Service as Route Planner Service

    User->>Frontend: Eingabe Route
    Frontend->>API: POST / (JSON-Routenanfrage)
    API->>Controller: compute_route()
    Controller->>Service: berechne Route
    Service-->>Controller: Routen-Ergebnis
    Controller-->>API: HTTP Response (Route)
    API-->>Frontend: JSON mit Route
    Frontend-->>User: Zeige Route auf UI
