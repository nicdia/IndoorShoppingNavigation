# Indoor Shopping Navigation

Indoor navigation prototype developed within the "Location Based Services" master course. The project consists of a FastAPI backend for route calculation and a React frontend (Vite + TypeScript) for visualizing the floor plan, route, and shopping list.

---

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm (ships with Node.js)

The following commands are for Windows PowerShell. Adjust paths as needed.

---

## Backend (FastAPI)

The backend is located in `app/server/` and provides endpoints for products and route calculation.

1. Change into the backend folder:
	```powershell
	cd .\app\server
	```
2. Create and activate a virtual environment (recommended):
	```powershell
	python -m venv .venv
	.\.venv\Scripts\Activate.ps1
	```
3. Install dependencies:
	```powershell
	pip install fastapi uvicorn networkx
	```
4. Start the server:
	```powershell
	uvicorn app:app --reload --host 127.0.0.1 --port 8000
	```

The API is available at `http://127.0.0.1:8000`. Swagger documentation at `http://127.0.0.1:8000/docs`.

### Endpoints

- `GET /products` - List of all products with ID, name, and associated node ID
- `POST /route` - Calculates an optimized route for the given product IDs

---

## Frontend (React + Vite)

The frontend is located in `app/frontend/` and displays the floor plan, current route, and shopping list.

1. Change into the frontend folder:
	```powershell
	cd .\app\frontend
	```
2. Install dependencies (once or after changes to `package.json`):
	```powershell
	npm install
	```
3. Start the development server:
	```powershell
	npm run dev
	```
4. Open the displayed URL in the browser (default `http://127.0.0.1:5173`).

The frontend expects the backend at `http://127.0.0.1:8000`. A different URL can be set via a `.env` file in the frontend folder:

```dotenv
VITE_API_BASE_URL=http://localhost:9000
```

### Layout Data

`app/frontend/public/layout.json` contains the polygon data for the floor plan. Adjust this file if the layout changes.

### Usage

- The red marker shows the current position. When checking off a product, the position jumps to that product.
- The blue marker shows the next target.
- Completed and upcoming segments are displayed in light red, the active segment is highlighted in red.

---

## Running Both Services

Start backend and frontend in separate terminals:

```powershell
# Terminal 1 (Backend)
cd .\app\server
.\.venv\Scripts\Activate.ps1
uvicorn app:app --reload

# Terminal 2 (Frontend)
cd .\app\frontend
npm run dev
```

---

## Troubleshooting

- `npm run dev` fails: Install dependencies with `npm install`, check if port 5173 is in use.
- Backend not reachable: Verify uvicorn is running on port 8000.
- Layout not displayed: Check `app/frontend/public/layout.json` for valid JSON.
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
