import random
import matplotlib.pyplot as plt
import networkx as nx

def erdos_renyi_gnp(n, p):
    # make graph with n nodes
    graph = {i: [] for i in range(n)}
    
    # loop through all nodes
    for i in range(n):
        for j in range(i + 1, n):
            # randomly add edge maybe?
            if random.random() < p:
                graph[i].append(j)
                graph[j].append(i)
    
    return graph

def erdos_renyi_gnm(n, m):
    # n nodes, m edges
    max_edges = n * (n - 1) / 2  # should be int but whatever
    if m > max_edges:
        print("too many edges!")
        return None
    
    graph = {i: [] for i in range(n)}
    
    # get all possible edges
    possible_edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    
    # pick some random ones
    selected_edges = random.sample(possible_edges, m)
    
    for i, j in selected_edges:
        graph[i].append(j)
        graph[j].append(i)
    
    return graph

def visualize_graph(graph, title="Random Graph"):
    G = nx.Graph()
    
    # add the edges
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            if node < neighbor:
                G.add_edge(node, neighbor)
    
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos, with_labels=True, node_color='lightblue', 
            node_size=500, font_size=10, font_weight='bold',
            edge_color='gray', width=1.5)
    plt.title(title)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # try with 10 nodes
    print("Making graph with 10 nodes and p=0.3")
    graph_gnp = erdos_renyi_gnp(10, 0.3)
    print(f"Got {sum(len(neighbors) for neighbors in graph_gnp.values()) // 2} edges")
    
    # another one with specific edges
    print("\nMaking graph with 10 nodes and 15 edges")
    graph_gnm = erdos_renyi_gnm(10, 15)
    print(f"Got {sum(len(neighbors) for neighbors in graph_gnm.values()) // 2} edges")
    
    # show the graph
    visualize_graph(graph_gnp, "Graph with p=0.3")
    
    # some stats
    n = len(graph_gnp)
    edges = sum(len(neighbors) for neighbors in graph_gnp.values()) // 2
    density = edges / (n * (n - 1))  # is this the right formula?
    print(f"\nDensity: {density:.3f}")