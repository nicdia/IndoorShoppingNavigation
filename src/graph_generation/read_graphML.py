import os
import networkx as nx
from itertools import islice


def main():
	base = os.path.dirname(__file__) or '.'
	path = os.path.join(base, 'graph.graphml')
	if not os.path.exists(path):
		print(f"Fehler: '{path}' nicht gefunden. Stelle sicher, dass die Datei im gleichen Ordner liegt.")
		return

	G = nx.read_graphml(path)
	print(f"Graph geladen: {G.number_of_nodes()} Knoten, {G.number_of_edges()} Kanten")

	# sammle Attribut-Namen (Spalten) für Knoten und Kanten
	node_keys = set()
	for _, data in G.nodes(data=True):
		node_keys.update(data.keys())

	edge_keys = set()
	for _, _, data in G.edges(data=True):
		edge_keys.update(data.keys())

	print('\nKnoten-Attribute (Spalten):')
	if node_keys:
		for k in sorted(node_keys):
			print(' -', k)
	else:
		print(' (keine Knotendaten)')

	print('\nKanten-Attribute (Spalten):')
	if edge_keys:
		for k in sorted(edge_keys):
			print(' -', k)
	else:
		print(' (keine Kantendaten)')

	# Beispiele ausgeben
	print('\nErste 10 Knoten (id, attributes):')
	for n, data in islice(G.nodes(data=True), 10):
		print(n, data)

	print('\nErste 10 Kanten (u, v, attributes):')
	for u, v, data in islice(G.edges(data=True), 10):
		print(u, v, data)


if __name__ == '__main__':
	main()

