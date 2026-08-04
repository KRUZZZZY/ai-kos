import random
import argparse
import matplotlib.pyplot as plt
import networkx as nx

def watts_strogatz(n, k, p):
    # make the graph thing
    if k % 2 != 0:
        raise ValueError("k must be even")
    if k >= n:
        raise ValueError("k must be less than n")
    
    G = nx.Graph()
    nodes = list(range(n))
    G.add_nodes_from(nodes)
    
    # connect nodes in circle
    for i in range(n):
        for j in range(1, k // 2 + 1):
            right = (i + j) % n
            G.add_edge(i, right)
    
    # rewire stuff
    edges = list(G.edges())
    for u, v in edges:
        if random.random() < p:
            G.remove_edge(u, v)
            
            # pick new node to connect to
            possible_targets = [x for x in nodes if x != u and not G.has_edge(u, x)]
            
            if possible_targets:
                w = random.choice(possible_targets)
                G.add_edge(u, w)
    
    return G

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate and visualize a Watts-Strogatz small-world network")
    parser.add_argument("--n", type=int, default=30, help="number of nodes")
    parser.add_argument("--k", type=int, default=4, help="neighbors")
    parser.add_argument("--p", type=float, default=0.3, help="probability")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--save", type=str, default=None, help="save file")
    parser.add_argument("--no-show", action="store_true", help="dont show plot")
    
    args = parser.parse_args(argv)
    
    if args.seed is not None:
        random.seed(args.seed)
    
    G = watts_strogatz(n=args.n, k=args.k, p=args.p)
    
    plt.figure(figsize=(10, 10))
    pos = nx.circular_layout(G)
    nx.draw(G, pos, node_color='lightblue',
            node_size=500, with_labels=True,
            font_size=10, edge_color='gray')
    plt.title(f"Watts-Strogatz Network (n={args.n}, k={args.k}, p={args.p})")
    plt.axis('equal')
    plt.tight_layout()
    
    if args.save:
        plt.savefig(args.save, dpi=200)
        print(f"Saved to {args.save}")
    
    if not args.no_show:
        plt.show()
    
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    print(f"Clustering: {nx.average_clustering(G):.3f}")
    
    if nx.is_connected(G):
        print(f"Path length: {nx.average_shortest_path_length(G):.3f}")
    else:
        largest_cc = max(nx.connected_components(G), key=len)
        H = G.subgraph(largest_cc)
        print("disconnected graph, using biggest component")
        print(f"Component size: {H.number_of_nodes()}")
        if H.number_of_nodes() > 1:
            print(f"Path length: {nx.average_shortest_path_length(H):.3f}")

if __name__ == "__main__":
    main()