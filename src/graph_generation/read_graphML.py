# Script to showcase how to read a GraphML file 

# ------- Not directly necessary for the project -------

import os
import networkx as nx
from itertools import islice


def main():
	base = os.path.dirname(__file__) or '.'
	path = os.path.join(base, 'graph.graphml')
	if not os.path.exists(path):
		print(f"Error: '{path}' not found. Make sure the file is in the same folder.")
		return

	G = nx.read_graphml(path)
	print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

	# Collect attribute names (columns) for nodes and edges
	node_keys = set()
	for _, data in G.nodes(data=True):
		node_keys.update(data.keys())

	edge_keys = set()
	for _, _, data in G.edges(data=True):
		edge_keys.update(data.keys())

	print('\nNode Attributes (Columns):')
	if node_keys:
		for k in sorted(node_keys):
			print(' -', k)
	else:
		print(' (no node data)')

	print('\nEdge Attributes (Columns	):')
	if edge_keys:
		for k in sorted(edge_keys):
			print(' -', k)
	else:
		print(' (no edge data)')

	# Show examples
	print('\nFirst 10 Nodes (id, attributes):')
	for n, data in islice(G.nodes(data=True), 10):
		print(n, data)

	print('\nFirst 10 Edges (u, v, attributes):')
	for u, v, data in islice(G.edges(data=True), 10):
		print(u, v, data)


if __name__ == '__main__':
	main()

