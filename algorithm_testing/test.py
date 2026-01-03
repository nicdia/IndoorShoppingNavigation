# test.py
import networkx as nx

from criteria.metrics_wrapper import evaluate_all_criteria
from algorithms.bnb_dijkstra import run_algorithm
#from algorithms.bnb_a_star import run_algorithm
#from algorithms.CDSSSD import run_algorithm
#from algorithms.MDMSMD import run_algorithm
#from algorithms.EAMDSP import run_algorithm
#from algorithms.nn_dijkstra import run_algorithm
#from algorithms.nn_a_star import run_algorithm

def load_graph(path: str) -> nx.Graph:
    """
    Lädt den Graphen und stellt sicher, dass jede Kante ein 'weight'-Attribut hat.
    """
    G = nx.read_graphml(path)
    for u, v, d in G.edges(data=True):
        d["weight"] = float(d.get("weight", d.get("length", 1.0)))
    return G


if __name__ == "__main__":
    # --- Standard-Testsetting für alle Algorithmen ---
    GRAPH_PATH = "resources/graph.graphml"

    ENTRY = "21"
    CHECKOUTS = ["14", "15"]
    # Fixe Itemliste, damit Algorithmen vergleichbar sind
    ITEMS = ["41", "61", "59", "78", "86", "112", "143", "3"]  # Beispiel-IDs, anpassen wie gewünscht

    # Graph laden
    G = load_graph(GRAPH_PATH)

    # Alle Metriken auf den Algorithmus laufen lassen
    results = evaluate_all_criteria(
        algorithm_fn=run_algorithm,
        G=G,
        entry=ENTRY,
        items=ITEMS,
        checkouts=CHECKOUTS,
        runtime_repeats=5,  # mehrere Runs für stabilere Laufzeit
    )

    route = results["route_result"]

    print("=== Algorithmus-Bewertung (BnB) ===")
    print(f"Entry:       {ENTRY}")
    print(f"Items:       {ITEMS}")
    print(f"Checkouts:   {CHECKOUTS}")
    print()
    print(f"Laufzeit (s):        {results['runtime_seconds']:.6f}")
    print(f"Distanz (Gewicht):   {results['distance']:.2f}")
    print(f"Anzahl Abbiegen:     {results['turns']}")
    print()
    print("Route-Order: ", " -> ".join(route['order']))
    print("Walk-Länge:  ", len(route['walk']), "Knoten")