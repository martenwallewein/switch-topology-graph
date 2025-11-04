import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import defaultdict

def plot_scion_topology(file_path='scion_topology.graphml'):
    """
    Loads a SCION topology from a GraphML file and plots it,
    correctly visualizing parallel edges (multi-graph) as arcs.

    Args:
        file_path (str): The path to the GraphML file.
    """
    try:
        # Loading a GraphML with parallel edges automatically creates a NetworkX MultiDiGraph
        G = nx.read_graphml(file_path)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        print("Please save the final GraphML content to this file and place it in the same directory.")
        return

    # --- 1. Prepare Node Attributes for Plotting ---
    node_colors = {node: 'skyblue' if G.nodes[node].get('as_type') == 'Core' else 'lightgreen' for node in G.nodes()}
    labels = {node: node for node in G.nodes()}

    # --- 2. Set Up the Plot ---
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(22, 18))
    # Use a spring layout with more iterations for better node separation
    pos = nx.spring_layout(G, seed=42, k=1.1, iterations=100)

    # --- 3. Draw Nodes and Labels ---
    nx.draw_networkx_nodes(G, pos, node_color=list(node_colors.values()), node_size=3000, ax=ax)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10, font_weight='bold', ax=ax)

    # --- 4. Draw Edges with Logic for Multi-Graph Visualization ---
    # Group edges by their source and target nodes to handle drawing logic
    edge_groups = defaultdict(list)
    for u, v, data in G.edges(data=True):
        edge_groups[(u, v)].append(data)

    for (u, v), all_data in edge_groups.items():
        num_edges = len(all_data)
        for i, data in enumerate(all_data):
            relation = data.get('relation')
            is_directed = relation == 'Parent-Child'

            # Define default styles
            style = 'solid'
            color = 'black'
            width = 2.5
            
            # Customize styles based on the link relation
            if relation == 'Parent-Child':
                color = 'dimgray'
                width = 1.0
            elif relation == 'Peering':
                style = 'dotted'
                color = 'blue'
                width = 1.5
            elif relation == 'Under Construction':
                style = 'dashed'
                color = 'red'
                width = 1.5
            
            # Calculate curvature for the arc.
            # A single edge will have rad=0 (a straight line).
            # Multiple edges will get varying positive/negative rads to create visible arcs.
            rad = 0.15 * (i - (num_edges - 1) / 2) if num_edges > 1 else 0
            connectionstyle = f'arc3,rad={rad}'
            
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)],
                connectionstyle=connectionstyle,
                style=style, edge_color=color, width=width,
                arrows=is_directed, arrowstyle='->', arrowsize=20,
                ax=ax
            )

    # --- 5. Create a Legend ---
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Core AS', markerfacecolor='skyblue', markersize=15),
        Line2D([0], [0], marker='o', color='w', label='Non-Core AS', markerfacecolor='lightgreen', markersize=15),
        Line2D([0], [0], color='black', lw=2.5, label='Core Link (can be redundant)'),
        Line2D([0], [0], color='dimgray', lw=1, label='Parent-Child Link (Directed)'),
        Line2D([0], [0], color='blue', lw=1.5, linestyle=':', label='Peering Link'),
        Line2D([0], [0], color='red', lw=1.5, linestyle='--', label='Under Construction'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize='x-large')

    # --- 6. Finalize and Show Plot ---
    ax.set_title('SCION Network Topology Visualization (Multi-Graph)', fontsize=22, fontweight='bold')
    plt.box(False)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    plot_scion_topology()