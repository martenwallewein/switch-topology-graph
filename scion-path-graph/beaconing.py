import sys
import networkx as nx
import xml.etree.ElementTree as ET
from collections import defaultdict

def parse_scion_graph(graphml_string):
    """
    Parses the GraphML XML string into a NetworkX MultiDiGraph,
    including custom edge IDs.
    """
    graph = nx.MultiDiGraph()
    node_attributes = {}
    
    ET.register_namespace('', "http://graphml.graphdrawing.org/xmlns")
    root = ET.fromstring(graphml_string.strip())
    
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    key_map = {key.get('id'): key.get('attr.name') for key in root.findall('.//g:key', ns)}

    # Parse nodes
    for node in root.findall('.//g:node', ns):
        node_id = node.get('id')
        attributes = {}
        for data in node.findall('g:data', ns):
            attr_name = key_map.get(data.get('key'))
            if attr_name:
                attributes[attr_name] = data.text
        graph.add_node(node_id, **attributes)
        node_attributes[node_id] = attributes

    # Parse edges
    for edge in root.findall('.//g:edge', ns):
        source, target = edge.get('source'), edge.get('target')
        # Use the edge's 'id' attribute from the GraphML as a key attribute in NetworkX
        edge_id = edge.get('id', f'edge_{source}_{target}') 
        relation = 'N/A'
        for data in edge.findall('g:data', ns):
            if key_map.get(data.get('key')) == 'relation':
                relation = data.text
        
        # Add the edge with its ID and relation
        graph.add_edge(source, target, key=edge_id, id=edge_id, relation=relation)
        if relation in ['Core', 'Peering', 'Under Construction']:
            # For bidirectional links, add the reverse edge with the same ID
            reverse_edge_id = f"{edge_id}_rev"
            graph.add_edge(target, source, key=reverse_edge_id, id=edge_id, relation=relation)

    return graph, node_attributes

def get_detailed_path_from_nodes(graph, node_path):
    """
    Converts a list of nodes (a path) into a detailed list including edge IDs.
    Example: ['A', 'B', 'C'] -> ['A', 'edge_ab', 'B', 'edge_bc', 'C']
    """
    if not node_path or len(node_path) < 2:
        return node_path
    
    detailed_path = [node_path[0]]
    for i in range(len(node_path) - 1):
        u, v = node_path[i], node_path[i+1]
        
        # In a MultiGraph, get all edges between u and v
        edge_data_dict = graph.get_edge_data(u, v)
        if edge_data_dict:
            # Take the first available edge's ID for this path segment
            first_key = list(edge_data_dict.keys())[0]
            edge_id = edge_data_dict[first_key].get('id', 'N/A')
            detailed_path.extend([edge_id, v])
        else:
            print(f"Warning: No edge found between {u} and {v}")
            print(detailed_path)
            # This case should not happen in a connected path
            detailed_path.extend(['unknown_edge', v])
            
    return detailed_path

def find_path_segments(graph, node_attrs):
    """
    Finds all up-segments and core-segments, returning paths with edge IDs.
    """
    core_ases = {n for n, attr in node_attrs.items() if attr.get('as_type') == 'Core'}
    non_core_ases = {n for n, attr in node_attrs.items() if attr.get('as_type') == 'Non-Core'}
    
    up_segments = defaultdict(list)
    core_segments = defaultdict(list)

    # 1. Discover Up-Segments
    hierarchy_graph = nx.Graph() 
    for u, v, data in graph.edges(data=True):
        if data.get('relation') in ['Parent-Child', 'Under Construction']:
            hierarchy_graph.add_edge(u, v)

    for nc_as in non_core_ases:
        nc_isd = node_attrs[nc_as].get('isd')
        for c_as in core_ases:
            if node_attrs[c_as].get('isd') == nc_isd and nx.has_path(hierarchy_graph, nc_as, c_as):
                for node_path in nx.all_simple_paths(hierarchy_graph, source=nc_as, target=c_as):
                    if not any(node in core_ases for node in node_path[1:-1]):
                        detailed_path = get_detailed_path_from_nodes(graph, node_path)
                        up_segments[nc_as].append(detailed_path)

    # 2. Discover Core-Segments
    core_graph = graph.subgraph(core_ases).copy()
    for source_core in core_ases:
        for target_core in core_ases:
            if source_core != target_core and nx.has_path(core_graph, source_core, target_core):
                for node_path in nx.all_simple_paths(core_graph, source=source_core, target=target_core):
                    detailed_path = get_detailed_path_from_nodes(graph, node_path)
                    core_segments[source_core].append(detailed_path)
                        
    return up_segments, core_segments

def combine_all_paths(graph, node_attrs, up_segments, core_segments):
    """
    Combines segments to find all end-to-end paths, preserving edge IDs.
    """
    all_paths = defaultdict(lambda: defaultdict(list))
    nodes = list(graph.nodes)
    core_ases = {n for n, attr in node_attrs.items() if attr.get('as_type') == 'Core'}

    for start_node in nodes:
        for end_node in nodes:
            if start_node == end_node: continue

            paths = set()
            start_is_core, end_is_core = start_node in core_ases, end_node in core_ases

            if not start_is_core and not end_is_core:
                for up1 in up_segments.get(start_node, []):
                    for up2 in up_segments.get(end_node, []):
                        core1, core2 = up1[-1], up2[-1]
                        down2 = up2[::-1]
                        if core1 == core2:
                            paths.add(tuple(up1 + down2[1:]))
                        for core_path in core_segments.get(core1, []):
                            if core_path and core_path[-1] == core2:
                                paths.add(tuple(up1 + core_path[1:]))
            elif not start_is_core and end_is_core:
                for up in up_segments.get(start_node, []):
                    if up[-1] == end_node: paths.add(tuple(up))
                    for core_path in core_segments.get(up[-1], []):
                        if core_path and core_path[-1] == end_node:
                            paths.add(tuple(up + core_path[1:]))
            elif start_is_core and not end_is_core:
                for up in up_segments.get(end_node, []):
                    down = up[::-1]
                    if down[0] == start_node: paths.add(tuple(down))
                    for core_path in core_segments.get(start_node, []):
                        if core_path and core_path[-1] == down[0]:
                            paths.add(tuple(core_path + down[1:]))
            elif start_is_core and end_is_core:
                for core_path in core_segments.get(start_node, []):
                    if core_path and core_path[-1] == end_node:
                        paths.add(tuple(core_path))

            if paths:
                all_paths[start_node][end_node] = sorted([list(p) for p in paths])

    return dict(all_paths)

def run_beaconing_simulation(graphml_data):
    scion_graph, node_attributes = parse_scion_graph(graphml_data)
    up_segments, core_segments = find_path_segments(scion_graph, node_attributes)
    all_end_to_end_paths = combine_all_paths(scion_graph, node_attributes, up_segments, core_segments)
    return all_end_to_end_paths

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <path_to_graphml_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            graphml_data = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at '{filepath}'")
        sys.exit(1)
        
    final_paths = run_beaconing_simulation(graphml_data)

    sample_source, sample_destination = 'UVa', 'GEANT'
    print("--- Beaconing Simulation Complete ---")
    print(f"\nFound {sum(len(d) for d in final_paths.values())} source-destination pairs with valid paths.")

    if final_paths.get(sample_source, {}).get(sample_destination):
        print(f"\nExample Paths from '{sample_source}' to '{sample_destination}':")
        for i, path in enumerate(final_paths[sample_source][sample_destination]):
            path_str_parts = [path[0]]
            for j in range(1, len(path), 2):
                edge_id, next_node = path[j], path[j+1]
                path_str_parts.append(f" --[{edge_id}]--> {next_node}")
            print(f"  Path {i+1}: {''.join(path_str_parts)}")
    else:
        print(f"\nNo paths found from '{sample_source}' to '{sample_destination}'.")

if __name__ == "__main__":
    main()