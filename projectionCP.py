import osmnx as ox
import matplotlib.pyplot as plt
import networkx as nx

place = "Cipayung, East Jakarta, Indonesia"
custom_filter = '["highway"~"primary|secondary|tertiary"]'
G = ox.graph_from_place(place, custom_filter=custom_filter, network_type="drive", simplify=True)
fig, ax = ox.plot_graph(G, edge_color="gray", edge_linewidth=1.5, node_size=20,
                        node_color="lightblue", node_zorder=2,
                        show=False, close=False, bgcolor='black')
plt.savefig("cipayung_graph.png", dpi=300, bbox_inches="tight")
plt.show()