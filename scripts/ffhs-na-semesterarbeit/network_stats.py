import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages
from networkx import Graph
import matplotlib.pyplot as plt

graph: Graph = nx.read_gexf('network.gexf')

degrees = list(dict(graph.degree).values())
fig = plt.figure()
print(max(degrees))
plt.hist(degrees, bins=max(degrees) - min(degrees))
plt.xlabel('Grad')
plt.ylabel('Anzahl')
pp = PdfPages('multipage.pdf')

fig.savefig("test.pdf")

print(len([comp for comp in nx.connected_component_subgraphs(graph.to_undirected())]))
for node in list(graph.nodes())[:int(len(graph.nodes())*0.7)]:
    graph.remove_node(node)

print(len([comp for comp in nx.connected_component_subgraphs(graph.to_undirected())]))