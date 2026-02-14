# test.py


import os 

# """
# # TK/TCL Fix (Windows) - comment out or edit lib path
# os.environ['TCL_LIBRARY'] = r'C:\Users\nikla\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
# os.environ['TK_LIBRARY']  = r'C:\Users\nikla\AppData\Local\Programs\Python\Python313\tcl\tk8.6'
# """

import networkx as nx
import matplotlib.pyplot as plt

from criteria.metrics_wrapper import evaluate_all_criteria
# from algorithms.bnb_dijkstra import run_algorithm
# from algorithms.bnb_a_star import run_algorithm
#from algorithms.CDSSSD import run_algorithm
#from algorithms.MDMSMD import run_algorithm
#from algorithms.EAMDSP import run_algorithm
#from algorithms.nn_dijkstra import run_algorithm
# from algorithms.nn_a_star import run_algorithm
# from algorithms.bnb_a_star_modified_lowerbound import run_algorithm
# from algorithms.bnb_a_star_modified_lowerbound_preload_astar import run_algorithm
from algorithms.bnb_a_star_modified_mstbound import run_algorithm
def load_graph(path: str) -> nx.Graph:
    """
    Loads the graph and ensures that every edge has a 'weight' attribute.
    """
    G = nx.read_graphml(path)
    for u, v, d in G.edges(data=True):
        d["weight"] = float(d.get("weight", d.get("length", 1.0)))
    return G


def get_positions(G: nx.Graph):
    """
    Returns a position dict for visualization.
    Uses node attributes 'x'/'y' (or 'lon'/'lat') if available,
    otherwise falls back to a NetworkX spring layout.
    """
    pos = {}
    # Try: x/y
    if all(("x" in data and "y" in data) for _, data in G.nodes(data=True)):
        for n, data in G.nodes(data=True):
            pos[n] = (float(data["x"]), float(data["y"]))
        return pos

    # Try: lon/lat
    if all(("lon" in data and "lat" in data) for _, data in G.nodes(data=True)):
        for n, data in G.nodes(data=True):
            pos[n] = (float(data["lon"]), float(data["lat"]))
        return pos

    # Fallback: spring_layout
    return nx.spring_layout(G, seed=42)


def visualize_route(G, pos, ENTRY, items, CHECKOUTS, walk, title="Route on edges",
                    runtime=None, distance=None, turns=None):
    plt.figure(figsize=(12, 9))

    # Full graph
    nx.draw(
        G, pos,
        node_color="#e0e0e0",
        node_size=120,
        edge_color="#d0d0d0",
        with_labels=True,
        font_size=7,
    )

    # Highlight special nodes
    nx.draw_networkx_nodes(G, pos, nodelist=[ENTRY],     node_color="green", label="Entry",     node_size=300)
    nx.draw_networkx_nodes(G, pos, nodelist=items,       node_color="orange", label="Items",    node_size=300)
    nx.draw_networkx_nodes(G, pos, nodelist=CHECKOUTS,   node_color="red",    label="Checkouts",node_size=300)

    if walk and len(walk) > 1:
        route_edges = list(zip(walk[:-1], walk[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=route_edges, edge_color="blue", width=2.8)

    plt.legend(loc="lower right")
    plt.gca().set_aspect("equal")
    plt.title(title)

    # ============================
    #   INFO BOX (top left)
    # ============================
    info_lines = []

    if runtime is not None:
        info_lines.append(f"Runtime: {runtime:.4f} s")

    if distance is not None:
        info_lines.append(f"Distance: {distance:.2f}")

    if turns is not None:
        info_lines.append(f"Turns: {turns}")

    if info_lines:
        txt = "\n".join(info_lines)

        plt.text(
            0.01, 0.99,                # Position (relative to the plot area)
            txt,
            transform=plt.gca().transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor="white",
                alpha=0.85,
                edgecolor="gray"
            )
        )

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # --- Default test setup for all algorithms ---
    GRAPH_PATH = "resources/graph.graphml"

    ENTRY = "21"
    CHECKOUTS = ["14", "15"]
    # Fixed item list so algorithms are comparable
    ITEMS = ["41", "61", "59", "78", "86", "112", "143", "3", "149", "135", "139"]  # example IDs, adjust as needed

    # Load graph
    G = load_graph(GRAPH_PATH)

    # Run all metrics for the algorithm
    results = evaluate_all_criteria(
        algorithm_fn=run_algorithm,
        G=G,
        entry=ENTRY,
        items=ITEMS,
        checkouts=CHECKOUTS,
        runtime_repeats=5,  # multiple runs for stable runtime measurement
    )

    route = results["route_result"]

    print("=== Algorithm Evaluation ===")
    print(f"Entry:       {ENTRY}")
    print(f"Items:       {ITEMS}")
    print(f"Checkouts:   {CHECKOUTS}")
    print()
    print(f"Runtime (s):    {results['runtime_seconds']:.6f}")
    print(f"Distance:       {results['distance']:.2f}")
    print(f"No. of Turns:   {results['turns']}")
    print()
    print("Route order: ", " -> ".join(route["order"]))
    print("Walk length: ", len(route["walk"]), "nodes")

    # Visualization
    pos = get_positions(G)
    visualize_route(
        G,
        pos,
        ENTRY=ENTRY,
        items=ITEMS,
        CHECKOUTS=CHECKOUTS,
        walk=route["walk"],
        title="Computed Route",
        runtime=results["runtime_seconds"],
        distance=results["distance"],
        turns=results["turns"],
    )
