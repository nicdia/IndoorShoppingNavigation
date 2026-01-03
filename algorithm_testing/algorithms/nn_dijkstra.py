# algorithm_bnb.py
import math
import heapq
import itertools
import networkx as nx


def dijkstra(graph: nx.Graph, origin: str, destination: str):
    """
    Kürzester Pfad zwischen zwei Knoten mit Dijkstra.
    Gibt (path, distance) zurück.
    """
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


def compute_pairwise_dijkstra(G: nx.Graph, relevant: list[str]):
    """
    Berechnet für alle geordneten Paare (u, v) in 'relevant'
    die kürzesten Pfade und Distanzen.
    """
    dist = {u: {} for u in relevant}
    spath = {u: {} for u in relevant}

    for u, v in itertools.permutations(relevant, 2):
        p, d = dijkstra(G, u, v)
        dist[u][v] = d
        spath[u][v] = p

    return dist, spath


def bnb(current, remaining, cost, order_prefix, dist, checkouts, best):
    """
    Branch-and-Bound zur Bestimmung der optimalen Besuchsreihenfolge.
    (Wird aktuell nicht mehr benutzt – nur noch für Referenz da.)
    """
    best_order, best_cost = best

    # Pruning
    if cost >= best_cost:
        return best

    # Wenn keine Items mehr offen sind: besten Checkout anhängen
    if not remaining:
        for c in checkouts:
            d = dist[current][c]
            total = cost + d
            if math.isfinite(total) and total < best_cost:
                best_order = order_prefix + [c]
                best_cost = total
        return best_order, best_cost

    # Rekursion über verbleibende Items (sortiert nach Entfernung)
    for nxt in sorted(remaining, key=lambda x: dist[current][x]):
        d = dist[current][nxt]
        if not math.isfinite(d):
            continue

        best_order, best_cost = bnb(
            nxt,
            [r for r in remaining if r != nxt],
            cost + d,
            order_prefix + [nxt],
            dist,
            checkouts,
            (best_order, best_cost),
        )

    return best_order, best_cost


def nearest_neighbour(entry: str, items: list[str], dist: dict, checkouts: list[str]):
    """
    Nearest-Neighbour-Heuristik:
    - Start bei 'entry'
    - wiederholt das nächstgelegene noch nicht besuchte Item wählen
    - am Ende den nächstgelegenen Checkout wählen
    Gibt (order, total_cost) zurück.
    """
    order: list[str] = [entry]
    current = entry
    remaining = set(items)
    total_cost = 0.0
    infinity = math.inf

    # Alle Items per Nearest Neighbour ablaufen
    while remaining:
        # Nächstes Item nach aktueller Position suchen
        nxt = min(remaining, key=lambda x: dist[current].get(x, infinity))
        d = dist[current].get(nxt, infinity)

        if not math.isfinite(d):
            return [], math.inf

        total_cost += d
        order.append(nxt)
        current = nxt
        remaining.remove(nxt)

    # Besten Checkout von der letzten Position wählen
    best_checkout = None
    best_d = infinity
    for c in checkouts:
        d = dist[current].get(c, infinity)
        if d < best_d:
            best_d = d
            best_checkout = c

    if best_checkout is None or not math.isfinite(best_d):
        return [], math.inf

    order.append(best_checkout)
    total_cost += best_d

    return order, total_cost


def run_algorithm(G: nx.Graph, entry: str, items: list[str], checkouts: list[str]):
    """
    Standard-Schnittstelle für die Testbench / Metrics.

    Input:
        G         - NetworkX-Graph mit 'weight' auf den Kanten
        entry     - Entry-Node-ID (str)
        items     - Liste von Item-Node-IDs (str)
        checkouts - Liste von Checkout-Node-IDs (str)

    Output (Dict):
        {
            "order": [...],          # z.B. ["21", "41", "61", "14"]
            "walk": [...],           # komplette Knotenfolge im Graphen
            "total_distance": float  # Gesamtdistanz entlang 'order'
        }
    """
    relevant = [entry] + items + checkouts
    dist, spath = compute_pairwise_dijkstra(G, relevant)

    # Nearest Neighbour statt Branch & Bound
    if items:
        best_order, best_cost = nearest_neighbour(
            entry,
            items,
            dist,
            checkouts,
        )
    else:
        best_order = [entry] + [min(checkouts, key=lambda c: dist[entry][c])]
        best_cost = dist[entry][best_order[-1]]

    # Kein Pfad gefunden
    if not best_order:
        return {
            "order": [],
            "walk": [],
            "total_distance": math.inf,
        }

    # Walk aus Teilpfaden zusammensetzen
    walk: list[str] = []
    for a, b in zip(best_order[:-1], best_order[1:]):
        seg = spath[a][b]
        walk.extend(seg if not walk else seg[1:])

    return {
        "order": best_order,
        "walk": walk,
        "total_distance": float(best_cost),
    }
