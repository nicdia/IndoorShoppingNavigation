from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Indoor Shopping Navigation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/products")
def get_products():
    """Return a mock catalog of products."""
    return {
        "items": [
            {"id": "41", "name": "Kiwi", "level": 99, "category": "Fruit"},
            {"id": "61", "name": "Apple", "level": 99, "category": "Fruit"},
            {"id": "126", "name": "Sausage", "level": 1, "category": "Meat"},
            {"id": "139", "name": "Peanut", "level": 1, "category": "Snacks"},
        ]
    }


@app.post("/route")
def calculate_route():
    """Return a mock route response that mirrors the expected pathfinding output."""
    return {
        "order": [
            {"nodeId": "21", "type": "entry"},
            {"nodeId": "41", "type": "item", "productId": "41", "productName": "Kiwi"},
            {"nodeId": "61", "type": "item", "productId": "61", "productName": "Apple"},
            {"nodeId": "14", "type": "checkout"},
        ],
        "path": [
            {"nodeId": "21", "x": 2.0, "y": 2.0},
            {"nodeId": "1", "x": 2.0, "y": 4.0},
            {"nodeId": "41", "x": 1.0, "y": 6.0},
            {"nodeId": "2", "x": 2.0, "y": 20.0},
            {"nodeId": "3", "x": 2.0, "y": 7.0},
            {"nodeId": "61", "x": 11.0, "y": 20.0},
            {"nodeId": "14", "x": 15.0, "y": 6.0},
        ],
        "segments": [
            {
                "from": "21",
                "to": "41",
                "distance": 4.2,
                "path": ["21", "1", "41"],
            },
            {
                "from": "41",
                "to": "61",
                "distance": 16.8,
                "path": ["41", "1", "2", "37", "38", "61"],
            },
            {
                "from": "61",
                "to": "14",
                "distance": 11.4,
                "path": ["61", "12", "13", "14"],
            },
        ],
        "totalDistance": 32.4,
        "metadata": {
            "entry": "21",
            "checkout": "14",
            "selectedProducts": ["41", "61"],
            "units": "meters",
        },
    }
