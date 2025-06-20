import osmnx as ox
import matplotlib.pyplot as plt
import networkx as nx
from typing import Optional, List, Tuple, Dict, Any

def get_largest_scc(G_input: nx.MultiDiGraph) -> nx.MultiDiGraph:
    if not G_input or G_input.number_of_nodes() == 0:
        return G_input.__class__()
    try:
        largest_scc_nodes = max(nx.strongly_connected_components(G_input), key=len)
        return G_input.subgraph(largest_scc_nodes).copy()
    except (ValueError, TypeError):
        return G_input.__class__()

def detection_oneway_cut(G: nx.MultiDiGraph) -> List[Dict[str, Any]]:
    hasil = []
    for node in G.nodes:
        in_arcs = [(u, v) for u, v, data in G.in_edges(node, data=True) if data.get("oneway")]
        out_arcs = [(u, v) for u, v, data in G.out_edges(node, data=True) if data.get("oneway")]
        
        two_way_neighbor = False
        for neighbor in G.neighbors(node):
            if G.has_edge(node, neighbor) and G.has_edge(neighbor, node):
                 two_way_neighbor = True
                 break
        
        if in_arcs and not out_arcs and not two_way_neighbor:
            hasil.append({"node": node, "direction": "all in"})
        elif out_arcs and not in_arcs and not two_way_neighbor:
            hasil.append({"node": node, "direction": "all out"})        
    return hasil

def _is_still_strongly_connected(nodes: List, oriented_arcs: List[Tuple], undecided_edges: List[Tuple]) -> bool:
    '''Cek graf strongly connected.'''
    temp_graph = nx.DiGraph()
    temp_graph.add_nodes_from(nodes)
    temp_graph.add_edges_from(oriented_arcs)
    for u, v in undecided_edges:
        temp_graph.add_edge(u, v)
        temp_graph.add_edge(v, u)
    return nx.is_strongly_connected(temp_graph)

def create_custom_orientation(G_raw: nx.MultiDiGraph) -> Optional[nx.MultiDiGraph]:

    G = G_raw.copy()
    print(f"Initial Graph: {G.number_of_nodes()} node, {G.number_of_edges()} edge.")

    for u, v, data in G.edges(data=True):
        if not data.get("oneway", False):
            G.edges[u, v, 0]['flexible'] = True

    print("\n--- STEP 1: Checking 2-Edge Connectivity ---")
    G_undirected = nx.Graph(G)
    bridges = list(nx.bridges(G_undirected))
    if bridges:
        print(f"{len(bridges)} bridge founded. Erasing...")
        for u, v in bridges:
            if G.has_edge(u, v): G.remove_edge(u, v)
            if G.has_edge(v, u): G.remove_edge(v, u)
        
        largest_component_nodes = max(nx.connected_components(nx.Graph(G)), key=len)
        G = G.subgraph(largest_component_nodes).copy()
        print(f"Main component have {G.number_of_nodes()} node.")
    else:
        print("Graph 2-edge-connected.")

    print("\n--- STEP 2: Checking & Erasing One-Way Cut Node ---")
    one_way_cuts = detection_oneway_cut(G)
    if one_way_cuts:
        print(f"{len(one_way_cuts)} candidate of one-way cut node founded. Erasing...")
        nodes_to_remove = [item['node'] for item in one_way_cuts]
        G.remove_nodes_from(nodes_to_remove)
        G = get_largest_scc(G) # Ambil SCC terbesar setelah menghapus node
        print(f"{G.number_of_nodes()} node remaining.")
    else:
        print("One-way cut node not found.")

    print("\n--- STEP 3: Give Direction to Flexible Edges ---")
    fixed_arcs = set()
    edges_to_decide_set = set()
    for u, v, data in G.edges(data=True):
        if data.get('flexible', False):
            edges_to_decide_set.add(frozenset([u, v]))
        else:
            fixed_arcs.add((u, v))
            
    undecided_edges = [tuple(edge) for edge in edges_to_decide_set]
    oriented_arcs = list(fixed_arcs)
    nodes = list(G.nodes())

    print(f"Orientation started, {len(undecided_edges)} Flexible Edges...")
    for i, edge in enumerate(undecided_edges):
        u, v = edge[0], edge[1]
        remaining_undecided = undecided_edges[i+1:]
        
        if _is_still_strongly_connected(nodes, oriented_arcs + [(u, v)], remaining_undecided):
            oriented_arcs.append((u, v))
        else:
            oriented_arcs.append((v, u))
    
    print("\n--- STEP 4: Building Final Graph ---")
    final_graph = nx.MultiDiGraph()
    final_graph.add_nodes_from(G.nodes(data=True))
    final_graph.add_edges_from(oriented_arcs)
    
    if nx.is_strongly_connected(final_graph):
        print("Verification Success! The Final Graph is strong orientation.")
        return final_graph
    else:
        print("Verification Fail. Final Graph not Strongly Connected.")
        return get_largest_scc(final_graph)

# ============ MAIN ============= #
place = "Tanjung Priok, North Jakarta, Indonesia"
custom_filter = '["highway"~"primary|secondary|tertiary"]'
G_raw = ox.graph_from_place(place, custom_filter=custom_filter)

print(f"Projecting Map {place}")
G_to_plot = create_custom_orientation(G_raw)

if G_to_plot and G_to_plot.number_of_nodes() > 0:
    print("\n--- Preparing Visualization ---")

    for i, node in enumerate(G_to_plot.nodes()):
        G_to_plot.nodes[node]["label"] = f"{i}"

    fig, ax = plt.subplots(figsize=(15, 15), facecolor='black')
    ax.set_facecolor('black')

    node_positions = {node: (G_raw.nodes[node]["x"], G_raw.nodes[node]["y"]) for node in G_to_plot.nodes() if node in G_raw.nodes}

    for u, v in G_to_plot.edges():
        is_original_oneway = (G_raw.has_edge(u,v) and G_raw.get_edge_data(u,v,0).get('oneway', False)) or \
                             (G_raw.has_edge(v,u) and G_raw.get_edge_data(v,u,0).get('oneway', False))

        color = "red" if is_original_oneway else "yellow"
        
        nx.draw_networkx_edges(
            G_to_plot,
            pos=node_positions,
            edgelist=[(u, v)],
            ax=ax,
            edge_color=color,
            width=1.5,
            arrows=True,
            arrowsize=12,
            arrowstyle="->",
            connectionstyle="arc3,rad=0.05"
        )

    nx.draw_networkx_nodes(
        G_to_plot, pos=node_positions,
        ax=ax, node_size=100,
        node_color="lightblue", alpha=0.9,
        edgecolors="white", linewidths=0.5
    )

    for node, pos in node_positions.items():
        label = G_to_plot.nodes[node].get("label", node)
        ax.text(
            pos[0], pos[1],
            str(label),
            fontsize=5,
            color="black",
            fontweight='bold',
            ha="center",
            va="center",
        )

    ax.text(0.01, 0.99, 'Red: Original One Way Road\nYellow: Two Way Road (Given New Direction)',
            transform=ax.transAxes, fontsize=10, color='white',
            verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='black', ec='gray', alpha=0.8))

    ax.set_title(f"\n{place}", fontsize=16, color='white')
    plt.tight_layout()
    plt.show()

else:
    print("No Valid Graph.")