import os
import networkx as nx
import matplotlib.pyplot as plt
import heapq, math, itertools
import sqlite3

# TK/TCL Fix (Windows) - comment out or edit lib path
# os.environ['TCL_LIBRARY'] = r'C:\Users\nikla\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
# os.environ['TK_LIBRARY']  = r'C:\Users\nikla\AppData\Local\Programs\Python\Python313\tcl\tk8.6'

def db_query(product_name):
    #connect to the db
    dbfile = './shop_nav.db'
    con = sqlite3.connect(dbfile)
    cur = con.cursor()

    for row in cur.execute(f"SELECT node_id FROM v_product_map WHERE product_name = '{product_name}'"):
        print(row[0])
        return(str(row[0]))

    con.close()


def select_items():
    # Interactively ask for item IDs
    items = []
    while True:
        s = db_query(input("Enter Item: "))
        if s == None:
            return items
        #if not s.isdigit() or s not in G.nodes or s in [ENTRY, *CHECKOUTS]:
        #    print("Item does not exist.")
        #    continue
        if s in items:
            print("Already in list.")
            continue
        items.append(s)
        print(items)


def dijkstra(graph: nx.Graph, origin: str, destination: str):
    # Compute shortest path between two nodes using Dijkstra
    if origin == destination:
        return [origin], 0.0
    infinity = math.inf
    dist = {origin: 0.0}
    prev = {}
    pq = [(0.0, origin)]

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, infinity):
            continue
        if u == destination:
            break
        for v, attrs in graph[u].items():
            w = float(attrs.get("weight", 1.0))
            nd = d + w
            if nd < dist.get(v, infinity):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    if destination not in dist:
        return [], math.inf
    
    path = []
    cur = destination
    while cur != origin:
        path.append(cur)
        cur = prev.get(cur)
        if cur is None:
            return [], math.inf
    path.append(origin)
    path.reverse()
    return path, dist[destination]


def compute_pairwise_dijkstra(G, relevant):
    # Compute all shortest paths and distances between relevant nodes
    dist = {u: {} for u in relevant}
    spath = {u: {} for u in relevant}
    for u, v in itertools.permutations(relevant, 2):
        p, d = dijkstra(G, u, v)
        dist[u][v] = d
        spath[u][v] = p
    return dist, spath


def bnb(current, remaining, cost, order_prefix, dist, CHECKOUTS, best):
    # Branch and Bound to find optimal item visiting order
    best_order, best_cost = best
    if cost >= best_cost:
        return best
    if not remaining:
        # choose nearest checkout
        for c in CHECKOUTS:
            d = dist[current][c]
            total = cost + d
            if math.isfinite(total) and total < best_cost:
                best_order = order_prefix + [c]
                best_cost = total
        return best_order, best_cost
    # recursion for remaining items
    for nxt in sorted(remaining, key=lambda x: dist[current][x]):
        d = dist[current][nxt]
        if not math.isfinite(d):
            continue
        best_order, best_cost = bnb(
            nxt, [r for r in remaining if r != nxt],
            cost + d, order_prefix + [nxt],
            dist, CHECKOUTS, (best_order, best_cost)
        )
    return best_order, best_cost


def visualize_route(G, pos, ENTRY, items, CHECKOUTS, walk, title="Optimal route over edges"):
    # Draw the full graph and highlight the optimal route
    plt.figure(figsize=(12, 9))
    nx.draw(G, pos, node_color="#e0e0e0", node_size=120,
            edge_color="#d0d0d0", with_labels=True, font_size=7)
    nx.draw_networkx_nodes(G, pos, nodelist=[ENTRY], node_color="green", label="Entry", node_size=300)
    nx.draw_networkx_nodes(G, pos, nodelist=items, node_color="orange", label="Items", node_size=300)
    nx.draw_networkx_nodes(G, pos, nodelist=CHECKOUTS, node_color="red", label="Checkouts", node_size=300)
    nx.draw_networkx_edges(G, pos, edgelist=list(zip(walk[:-1], walk[1:])),
                           edge_color="blue", width=2.8)
    plt.legend(loc="lower right")
    plt.gca().set_aspect("equal")
    plt.title(title)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Load graph
    G = nx.read_graphml("./graph_connected.graphml")

    # Ensure weights exist
    for u, v, d in G.edges(data=True):
        d["weight"] = float(d.get("weight", d.get("length", 1.0)))

    ENTRY = "21"
    CHECKOUTS = ["14", "15"]

    # Select items
    items = select_items(G, ENTRY, CHECKOUTS)

    # Compute all pairwise shortest paths
    relevant = [ENTRY] + items + CHECKOUTS
    dist, spath = compute_pairwise_dijkstra(G, relevant)

    # Branch & Bound or direct checkout
    if items:
        best_order, best_cost = bnb(ENTRY, items, 0.0, [ENTRY], dist, CHECKOUTS, (None, math.inf))
    else:
        best_order = [ENTRY] + [min(CHECKOUTS, key=lambda c: dist[ENTRY][c])]
        best_cost = dist[ENTRY][best_order[-1]]

    # Output
    if not best_order:
        print("No route found.")
        exit()

    print("Best route:", " → ".join(best_order))
    print("Total distance:", round(best_cost, 2))

    # Combine full edge path
    walk = []
    for a, b in zip(best_order[:-1], best_order[1:]):
        seg = spath[a][b]
        walk.extend(seg if not walk else seg[1:])

    # Position dictionary
    pos = {n: (float(G.nodes[n]["x"]), float(G.nodes[n]["y"])) for n in G.nodes()}

    # Visualize
    visualize_route(G, pos, ENTRY, items, CHECKOUTS, walk)
