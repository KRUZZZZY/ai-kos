import networkx as nx
import matplotlib.pyplot as plt

# G(n, p) model
G = nx.erdos_renyi_graph(n=10, p=0.3)
print("G(n, p) model:")
print("Nodes:", G.nodes())
print("Edges:", G.edges())
plt.figure(figsize=(6,4))
nx.draw(G, with_labels=True)
plt.title("Erdos-Renyi G(n, p) Random Graph")
plt.show()

# G(n, m) model
G2 = nx.gnm_random_graph(n=10, m=15)
print("\nG(n, m) model:")
print("Nodes:", G2.nodes())
print("Edges:", G2.edges())
plt.figure(figsize=(6,4))
nx.draw(G2, with_labels=True)
plt.title("Erdos-Renyi G(n, m) Random Graph")
plt.show()