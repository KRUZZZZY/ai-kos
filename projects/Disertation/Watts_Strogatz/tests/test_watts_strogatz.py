import networkx as nx
from watts_Strogatz_Manual import watts_strogatz


def test_node_and_edge_counts():
    n = 50
    k = 6
    p = 0.1
    G = watts_strogatz(n=n, k=k, p=p)
    assert G.number_of_nodes() == n
    # Each node starts with k/2 edges on each side -> n*k/2 total edges in ring lattice
    assert G.number_of_edges() >= n * k // 2


def test_clustering_range():
    G = watts_strogatz(n=30, k=4, p=0.5)
    c = nx.average_clustering(G)
    assert 0.0 <= c <= 1.0


def test_largest_component_nonempty():
    G = watts_strogatz(n=20, k=2, p=1.0)
    comps = list(nx.connected_components(G))
    assert len(comps) >= 1
    largest = max(comps, key=len)
    assert len(largest) >= 1
