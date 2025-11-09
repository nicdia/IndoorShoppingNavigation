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

    # TODO: Hier muss dann einfach eine DB Abfrage hin um alle Produkte zu bekommen
    #       Das muss dann einfach nur als JSON formatiert werden
    return {
        "items": [
            {"id": "41", "name": "Kiwi"},
            {"id": "61", "name": "Apple"},
            {"id": "126", "name": "Sausage"},
            {"id": "139", "name": "Peanut"},
            {"id": "142", "name": "Almond"},
        ]
    }


@app.post("/route")
def calculate_route():
    # TODO: Das hier ist dann im wesentlichen das Ergebnis aus dem Algorithmus
    # Also in diesem Script die Funktion importieren, in dieser Funktion aufrufen, wobei man 
    #  bei dem Endpunkt dann einmal die Produkte hinschickt die im Frontend ausgewählt wurden.
    # Das muss dann nochmal mit Daten aus einer Weiteren DB Abfrage kombiniert werden, die zu den 
    # Produkten immer das Level ausgibt. Alternativ könnte das auch in dem Skript vom Algorithmus gemacht werden.
    # Bei der Arbeit haben wir in einem Projekt noch so "Services" dazwischen gestellt. Dann hätte
    # man eine Klasse Routing_Service oder so und würde die dann hier nur aufrufen. Das wäre wohl 
    # am saubersten. Man könnte es aber auch einfach hier machen oder halt die Funktion einfach aufrufen.      

    """Return a mock route response that mirrors the expected pathfinding output."""
    return {
        "order": [
            {"nodeId": "21", "type": "entry"},
            {"nodeId": "41", "type": "item", "productId": "41", "productName": "Kiwi", "level": 1},
            {"nodeId": "61", "type": "item", "productId": "61", "productName": "Apple", "level": 1},
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
