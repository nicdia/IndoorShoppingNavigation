# test.py

"""
This is a small script to test algorithms individually
The wanted algorithms has to be selected by uncommenting the specific algorithm in the import. 
The results are printed in the terminal:
 -> Runtime
 -> Distance
 -> Turns
 -> Route
 -> Nodes walked
"""
import networkx as nx

from criteria.metrics_wrapper import evaluate_all_criteria
# from algorithms.bnb_dijkstra import run_algorithm
# from algorithms.bnb_a_star import run_algorithm
# from algorithms.CDSSSD import run_algorithm
# from algorithms.MDMSMD import run_algorithm
# from algorithms.EAMDSP import run_algorithm
# from algorithms.nn_dijkstra import run_algorithm
# from algorithms.nn_a_star import run_algorithm
# from algorithms.bnb_a_star_modified_lowerbound import run_algorithm
# from algorithms.bnb_a_star_modified_lowerbound_preload_astar import run_algorithm
from algorithms.bnb_a_star_modified_mstbound import run_algorithm

def load_graph(path: str) -> nx.Graph:
    """
    Loads the graph and weights
    """
    G = nx.read_graphml(path)
    for u, v, d in G.edges(data=True):
        d["weight"] = float(d.get("weight", d.get("length", 1.0)))
    return G


if __name__ == "__main__":
    GRAPH_PATH = "resources/graph.graphml"

    ENTRY = "21"
    CHECKOUTS = ["14", "15"]
    # Fixed node list to compare the graphs, spread throughout the store
    ITEMS = ["41", "61", "59", "78", "86", "112", "143", "3"]

    G = load_graph(GRAPH_PATH)

    results = evaluate_all_criteria(
        algorithm_fn=run_algorithm,
        G=G,
        entry=ENTRY,
        items=ITEMS,
        checkouts=CHECKOUTS,
        runtime_repeats=5,
    )

    route = results["route_result"]

    print("=== Algorithm evaulation ===")
    print(f"Entry:       {ENTRY}")
    print(f"Items:       {ITEMS}")
    print(f"Checkouts:   {CHECKOUTS}")
    print()
    print(f"Runtime (s):    {results['runtime_seconds']:.6f}")
    print(f"Distance (m):   {results['distance']:.2f}")
    print(f"No. of Turns:   {results['turns']}")
    print()
    print("Route-order: ", " -> ".join(route['order']))
    print("Nodes walked::  ", len(route['walk']), "nodes")