import json
import os

def load_graph(filename):
    """Loads a graph from a JSON file."""
    if not os.path.exists(filename):
        print(f"Error: The file '{filename}' was not found.")
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading {filename}: {e}")
        return None

def aggregate_graphs(graph1, graph2, graph3):
    """
    Aggregates three graphs into one, handling duplicates and ID conflicts.
    """
    aggregated_graph = {"nodes": [], "edges": []}
    node_id_map = {}
    external_nodes_by_label = {}

    # Manual mapping for known aliases among external nodes
    ALIAS_MAPPING = {
        "decix": "de-cix",
        "amsix": "ams-ix",
        "belwue2": "belwü",
        "geant": "g\u00e9ant",
    }

    def get_normalized_label(label):
        """Normalizes a label for matching."""
        normalized = label.lower()
        return ALIAS_MAPPING.get(normalized, normalized)

    # Process Graph 1 (the base graph)
    if graph1:
        for node in graph1['nodes']:
            new_id = node['id']
            aggregated_graph['nodes'].append(node)
            node_id_map[('graph1.json', node['id'])] = new_id
            if node.get('type') == 'external':
                label_key = get_normalized_label(node['label'])
                if label_key not in external_nodes_by_label:
                    external_nodes_by_label[label_key] = new_id

    # Process Graph 2, merging external nodes and prefixing internal nodes
    if graph2:
        for node in graph2['nodes']:
            original_id = node['id']
            if node.get('type') == 'external':
                label_key = get_normalized_label(node['label'])
                if label_key in external_nodes_by_label:
                    # This node is a duplicate of one in graph1, map to the existing ID
                    node_id_map[('graph2.json', original_id)] = external_nodes_by_label[label_key]
                else:
                    # It's a new external node
                    aggregated_graph['nodes'].append(node)
                    node_id_map[('graph2.json', original_id)] = original_id
                    external_nodes_by_label[label_key] = original_id
            else: # Internal node from graph2
                new_id = f"g2_{original_id}"
                new_node = node.copy()
                new_node['id'] = new_id
                aggregated_graph['nodes'].append(new_node)
                node_id_map[('graph2.json', original_id)] = new_id

    # Process Graph 3, prefixing all nodes to avoid conflicts
    if graph3:
        for node in graph3['nodes']:
            original_id = node['id']
            new_id = f"g3_{original_id}"
            new_node = node.copy()
            new_node['id'] = new_id
            # Add a 'type' if it doesn't exist, assuming 'internal' for graph 3
            if 'type' not in new_node:
                new_node['type'] = 'internal'
            aggregated_graph['nodes'].append(new_node)
            node_id_map[('graph3.json', original_id)] = new_id

    # Process edges from all graphs
    all_graphs = {'graph1.json': graph1, 'graph2.json': graph2, 'graph3.json': graph3}
    for graph_name, graph_data in all_graphs.items():
        if not graph_data or 'edges' not in graph_data:
            continue
        for edge in graph_data['edges']:
            original_from = edge['from']
            original_to = edge['to']

            # Find the new mapped IDs
            new_from = node_id_map.get((graph_name, original_from))
            new_to = node_id_map.get((graph_name, original_to))

            if new_from and new_to:
                new_edge = edge.copy()
                new_edge['from'] = new_from
                new_edge['to'] = new_to

                # Determine and mark edge type (internal/external)
                to_node_is_external = any(n.get('type') == 'external' for n in aggregated_graph['nodes'] if n['id'] == new_to)
                from_node_is_external = any(n.get('type') == 'external' for n in aggregated_graph['nodes'] if n['id'] == new_from)

                if to_node_is_external or from_node_is_external:
                    new_edge['edge_type'] = 'external'
                else:
                    new_edge['edge_type'] = 'internal'

                aggregated_graph['edges'].append(new_edge)

    return aggregated_graph

def main():
    """Main function to load, aggregate, and save graphs."""
    graph1 = load_graph('switch_connectivity.json')
    graph2 = load_graph('switch_international.json')
    graph3 = load_graph('switch_swiss.json')

    if graph1 and graph2 and graph3:
        aggregated_graph = aggregate_graphs(graph1, graph2, graph3)
        
        output_filename = 'aggregated_graph_deduplicated.json'
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(aggregated_graph, f, indent=4, ensure_ascii=False)
            
        print(f"Aggregation complete. Deduplicated graph saved to '{output_filename}'")

if __name__ == '__main__':
    main()