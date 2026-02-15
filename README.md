# Indoor Shopping Navigation

Indoor navigation prototype developed within the **Location Based Services** master course.

Indoor Shopping Navigation is a prototype for routing shoppers through an indoor store layout. The project consists of a **Flask backend** for route calculation and product data, and a **React frontend (Vite + TypeScript)** for visualizing the floor plan, route, and shopping list. A SQLite database was configured as well as a separate, independent algorithm evaluation pipeline to determine the best algorithm for the backend.

---

## Prerequisites

- Python 3.10 or newer  
- Node.js 18 or newer  
- npm (ships with Node.js)

The following commands are for **Windows PowerShell**. Adjust paths as needed.

---

## Contents

- [Project goals](#project-goals)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
  - [Backend (Flask)](#backend-flask)
  - [Frontend (React + Vite)](#frontend-react--vite)
- [Configuration](#configuration)
- [Development workflow (best practices)](#development-workflow-best-practices)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Project Goals

- Provide an API that returns products and optimized routes through the store graph  
- Render the store layout, shopping list, and computed route in a web UI  
- Keep the system modular and easy to extend with new layouts or routing logic
- Evaluate different algorithms to determine the one most suitable for the project constraint

---

## Architecture

- **Backend**
  - Flask application located in `app/server/`
  - Endpoints:
    - `GET /api/health`
    - `GET /products`
    - `POST /route`

- **Frontend**
  - React application using Vite and TypeScript in `app/frontend/`
  - Uses layout data from `app/frontend/public/layout.json`
  - API base URL defaults to `http://127.0.0.1:8000` (overridable via `VITE_API_BASE_URL`)

- **Database**
  - SQLite database file `indoor_shopping_nav.db` at the repository root

- **Algorithm experiments**
  - Prototypes and benchmarking in `algorithm_testing/`

---

## Repository Layout

```
app/
  frontend/          # React + Vite app
  server/            # Flask backend
  database/          # Database-related resources
resources/           # Supporting assets
algorithm_testing/   # Algorithm experiments + benchmarks
```

---

## Getting Started

### Backend (Flask)

1. Change into the backend folder:

```powershell
cd .\app\server
```

2. Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies (the `requirements.txt` is in the repository root):

```powershell
pip install -r ..\..\requirements.txt
```

4. Start the server:

```powershell
python app.py
```

The API is available at http://127.0.0.1:8000 by default (set `PORT` in a `.env` file to change).

---

### Frontend (React + Vite)

1. Change into the frontend folder:

```powershell
cd .\app\frontend
```

2. Install dependencies:

```powershell
npm install
```

3. Start the development server:

```powershell
npm run dev
```

4. Open the displayed URL in the browser (default):

- http://127.0.0.1:5173

---

## Configuration

Start backend and frontend in separate terminals.

| Setting | Purpose | Default |
|--------|--------|--------|
| `PORT` | API server port | `3001` |
| `DB_PATH` | SQLite file path | `<repo>/indoor_shopping_nav.db` |
| `VITE_API_BASE_URL` | Frontend API base URL | `http://127.0.0.1:8000` |

### Backend Environment File (optional)

The backend reads a `.env` file in `app/server/` via `python-dotenv`.  
Create the file only if you need to override defaults:

```
app/server/.env
```

Example content:

```
PORT=8000
DB_PATH=/absolute/path/to/indoor_shopping_nav.db
```

<!-- > **Note:** The frontend does not require a `.env` file. It falls back to  
> `http://127.0.0.1:8000` when `VITE_API_BASE_URL` is not set. -->

---

## Layout Data

The store layout is defined in:

```
app/frontend/public/layout.json
```

This file contains polygon and node data for the floor plan. Adjust this file if the layout changes.

---

## Usage

- The red marker shows the current position
- The blue marker shows the next target
- When checking off a product, the position jumps to that product
- Completed and upcoming segments are displayed in light red
- The active segment is highlighted in red

---


## UML Sequence Diagram (Mermaid) Web App

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as Backend API (Flask)
    participant Controller as Route Controller
    participant Service as Route Planner Service

    User->>Frontend: Enter route request
    Frontend->>API: POST /route (JSON)
    API->>Controller: compute_route()
    Controller->>Service: calculate route
    Service-->>Controller: route result
    Controller-->>API: HTTP response
    API-->>Frontend: JSON route
    Frontend-->>User: Display route
```

---

## Pipeline Workflow for Algorithm Evaluations

```mermaid
flowchart TB

%% --------------------------
%% Benchmark: produces metrics DataFrame
%% --------------------------
subgraph Benchmark[Algorithm Benchmark Flow]
    B_Start["Start benchmark run"]

    %% Configurations & Scenarios
    B_Configs["Define algorithm CONFIGS (multiple setups incl. bnb_*, nn_*, EAMDSP, MDMSMD; each with runtime_repeats)"]
    B_Scenarios["Define SCENARIOS (graph_path, entry, items, checkouts)"]

    %% Quality Benchmark: run_experiments()
    B_RunExp["run_experiments() over all (scenario × algorithm)"]
    B_LoadGraph["Load GraphML and ensure each edge has a numeric 'weight' attribute"]
    B_Eval["evaluate_all_criteria() -> route_result(order, walk, total_distance), runtime_seconds, distance, turns"]
    B_Row["Build metrics row for each setup = scenario__algorithm"]
    B_DF["Benchmark DataFrame (indexed by setup)"]

    %% Main flow: Quality Benchmark
    B_Start --> B_Configs
    B_Configs --> B_Scenarios
    B_Scenarios --> B_RunExp
    B_RunExp --> B_LoadGraph
    B_LoadGraph --> B_Eval
    B_Eval --> B_Row
    B_Row --> B_DF
end

%% --------------------------
%% Criteria Diagrams
%% --------------------------
subgraph CriteriaDiagrams[Criteria Diagrams Flow]
    C_Start["Start criteria_diagrams main()"]

    %% Input & raw export
    C_InDF["Take benchmark DataFrame (one row per setup)"]
    C_RawCSV["Save criteria_raw_metrics_per_setup.csv (full metrics per setup)"]

    %% Aggregation per algorithm
    C_Agg["Group by algorithm_setup and compute mean(runtime_seconds, distance, turns)"]
    C_AggCSV["Save criteria_metrics_per_algorithm.csv (aggregated per algorithm)"]

    %% Visualization
    C_CategoryLoop["Iterate over categories: distance, turns, runtime_seconds"]
    C_Plot["Generate bar chart PNG for each category (absolute values per algorithm)"]
end

%% Connect Benchmark -> Criteria Diagrams
B_DF --> C_InDF
C_Start --> C_InDF
C_InDF --> C_RawCSV
C_InDF --> C_Agg
C_Agg --> C_AggCSV
C_AggCSV --> C_CategoryLoop --> C_Plot

%% --------------------------
%% Heatmap (full workflow: normalize, aggregate, visualize)
%% --------------------------
subgraph Heatmap[Heatmap Flow]
    H_Start["Start heatmap main()"]

    %% Input
    H_InDF["Take benchmark DataFrame (distance, turns, runtime_seconds per setup)"]

    %% Step 1: Scenario-specific normalization
    H_GroupScenario["Group rows by scenario"]
    H_NormMetrics["Within each scenario: min–max normalize distance/turns/runtime_seconds to 0–100 (invert: smaller is better)"]
    H_OverallIndex["Compute Overall per setup (mean of normalized metrics)"]
    H_PerSetup["Assemble per_setup_index: scenario, algorithm_setup, normalized metrics, Overall"]

    %% Step 2: Aggregate across scenarios
    H_PerAlgo["Group per_setup_index by algorithm_setup and average normalized scores -> per_algorithm_index"]

    %% Step 3: Export & Visualization
    H_SetupCSV["Save per_setup_index -> heatmap_index_per_setup.csv"]
    H_AlgoCSV["Save per_algorithm_index -> heatmap_index_per_algorithm.csv"]
    H_SavePNG["Render per_algorithm_index as heatmap_index_per_algorithm.png (rows = algorithms, columns = categories)"]
end

%% Connect Benchmark -> Heatmap
B_DF --> H_InDF
H_Start --> H_InDF
H_InDF --> H_GroupScenario
H_GroupScenario --> H_NormMetrics --> H_OverallIndex --> H_PerSetup
H_PerSetup --> H_PerAlgo
H_PerSetup --> H_SetupCSV
H_PerAlgo --> H_AlgoCSV --> H_SavePNG
```