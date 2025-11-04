import sys
import networkx as nx
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
import itertools
import json
import argparse
import random

# --- Constants for the growth simulation ---
LEAF_CHUNK_SIZE = 5  # Max number of leaf nodes to add in a single step

def parse_scion_graph(graphml_string):
    # ... (rest of the functions are identical to the previous version)
    # ... (parse_scion_graph, get_detailed_path_from_nodes, find_path_segments, etc.)
    # ... (No changes needed in the core logic functions)
    graph = nx.MultiDiGraph()
    node_attributes = {}
    
    ET.register_namespace('', "http://graphml.graphdrawing.org/xmlns")
    root = ET.fromstring(graphml_string.strip())
    
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    key_map = {key.get('id'): key.get('attr.name') for key in root.findall('.//g:key', ns)}

    for node in root.findall('.//g:node', ns):
        node_id = node.get('id')
        attributes = {}
        for data in node.findall('g:data', ns):
            attr_name = key_map.get(data.get('key'))
            if attr_name:
                attributes[attr_name] = data.text
        graph.add_node(node_id, **attributes)
        node_attributes[node_id] = attributes

    for edge in root.findall('.//g:edge', ns):
        source, target = edge.get('source'), edge.get('target')
        edge_id = edge.get('id', f'edge_{source}_{target}') 
        relation = 'N/A'
        for data in edge.findall('g:data', ns):
            if key_map.get(data.get('key')) == 'relation':
                relation = data.text
        
        graph.add_edge(source, target, key=edge_id, id=edge_id, relation=relation)
        if relation in ['Core', 'Peering', 'Under Construction']:
            reverse_edge_id = f"{edge_id}_rev"
            graph.add_edge(target, source, key=reverse_edge_id, id=edge_id, relation=relation)

    return graph, node_attributes

def get_detailed_path_from_nodes(graph, node_path):
    if not node_path or len(node_path) < 2: return node_path
    detailed_path = [node_path[0]]
    for i in range(len(node_path) - 1):
        u, v = node_path[i], node_path[i+1]
        edge_data_dict = graph.get_edge_data(u, v)
        if edge_data_dict:
            first_key = list(edge_data_dict.keys())[0]
            detailed_path.extend([edge_data_dict[first_key].get('id', 'N/A'), v])
        else:
            detailed_path.extend(['unknown_edge', v])
    return detailed_path

def find_path_segments(graph, node_attrs):
    core_ases = {n for n, attr in node_attrs.items() if attr.get('as_type') == 'Core'}
    non_core_ases = {n for n, attr in node_attrs.items() if attr.get('as_type') == 'Non-Core'}
    up_segments, core_segments = defaultdict(list), defaultdict(list)
    hierarchy_graph = nx.Graph((u, v) for u, v, data in graph.edges(data=True) if data.get('relation') in ['Parent-Child', 'Under Construction'])

    for nc_as in non_core_ases:
        for c_as in core_ases:
            if nc_as in hierarchy_graph and c_as in hierarchy_graph and node_attrs[nc_as].get('isd') == node_attrs[c_as].get('isd') and nx.has_path(hierarchy_graph, nc_as, c_as):
                for node_path in nx.all_simple_paths(hierarchy_graph, source=nc_as, target=c_as):
                    if not any(node in core_ases for node in node_path[1:-1]):
                        up_segments[nc_as].append(get_detailed_path_from_nodes(graph, node_path))
    core_graph = graph.subgraph(core_ases)
    for source_core, target_core in itertools.permutations(core_ases, 2):
        if nx.has_path(core_graph, source_core, target_core):
            for node_path in nx.all_simple_paths(core_graph, source=source_core, target=target_core):
                core_segments[source_core].append(get_detailed_path_from_nodes(graph, node_path))
    return up_segments, core_segments

def combine_all_paths(graph, node_attrs, up_segments, core_segments):
    all_paths = defaultdict(lambda: defaultdict(list))
    nodes = list(graph.nodes)
    core_ases = {n for n, attr in node_attrs.items() if attr.get('as_type') == 'Core'}
    for start_node, end_node in itertools.permutations(nodes, 2):
        paths = set()
        start_is_core, end_is_core = start_node in core_ases, end_node in core_ases
        if not start_is_core and not end_is_core:
            for up1 in up_segments.get(start_node, []):
                for up2 in up_segments.get(end_node, []):
                    core1, core2 = up1[-1], up2[-1]
                    down2 = up2[::-1]
                    if core1 == core2: paths.add(tuple(up1 + down2[1:]))
                    for core_path in core_segments.get(core1, []):
                        if core_path and core_path[-1] == core2: paths.add(tuple(up1 + core_path[1:] + down2[1:]))
        elif not start_is_core and end_is_core:
            for up in up_segments.get(start_node, []):
                if up[-1] == end_node: paths.add(tuple(up))
                for core_path in core_segments.get(up[-1], []):
                    if core_path and core_path[-1] == end_node: paths.add(tuple(up + core_path[1:]))
        elif start_is_core and not end_is_core:
            for up in up_segments.get(end_node, []):
                down = up[::-1]
                if down[0] == start_node: paths.add(tuple(down))
                for core_path in core_segments.get(start_node, []):
                    if core_path and core_path[-1] == down[0]: paths.add(tuple(core_path + down[1:]))
        elif start_is_core and end_is_core:
            for core_path in core_segments.get(start_node, []):
                if core_path and core_path[-1] == end_node: paths.add(tuple(core_path))
        if paths:
            all_paths[start_node][end_node] = sorted([list(p) for p in paths])
    return dict(all_paths)

def analyze_subgraph_paths(subgraph, subgraph_node_attrs, results_list, step):
    """
    Analyzes a given subgraph and appends the results to the results list.
    """
    print(f"  Analysing {len(subgraph.nodes())}-node subgraph...")
    up_segments, core_segments = find_path_segments(subgraph, subgraph_node_attrs)
    all_end_to_end_paths = combine_all_paths(subgraph, subgraph_node_attrs, up_segments, core_segments)
    
    total_paths = sum(len(dest_paths) for destinations in all_end_to_end_paths.values() for dest_paths in destinations.values())
    
    num_nodes = len(subgraph.nodes())
    num_possible_pairs = num_nodes * (num_nodes - 1)
    average_per_pair = total_paths / num_possible_pairs if num_possible_pairs > 0 else 0.0

    results_list.append({
        "step": step,
        "subgraph_size": num_nodes,
        "average_paths_per_node_pair": average_per_pair,
        "nodes_in_subgraph": list(subgraph.nodes())
    })
    print(f"  -> Average paths per node pair: {average_per_pair:.4f}")

def main():
    parser = argparse.ArgumentParser(description="Simulate the natural growth of a SCION network and analyze path availability.")
    parser.add_argument("graphml_file", help="Path to the SCION topology GraphML file.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    # --- THIS IS THE ONLY ADDITION ---
    parser.add_argument("-o", "--output", default="natural_growth_results.json", help="Path to save the output JSON file.")
    # ---------------------------------
    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed)

    try:
        with open(args.graphml_file, 'r', encoding='utf-8') as f:
            graphml_data = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at '{args.graphml_file}'")
        sys.exit(1)
        
    # ... (Rest of main function is identical) ...
    full_graph, full_node_attributes = parse_scion_graph(graphml_data)
    all_nodes = list(full_graph.nodes())
    
    core_ases = {n for n, attr in full_node_attributes.items() if attr.get('as_type') == 'Core'}
    non_core_ases = set(all_nodes) - core_ases
    
    if len(core_ases) < 2:
        print("Error: The graph must contain at least two Core ASes to start the simulation.")
        sys.exit(1)

    print("--- Starting Natural Growth Simulation ---")

    shuffled_cores = random.sample(list(core_ases), len(core_ases))
    start_node = shuffled_cores.pop(0)
    second_node = next((core for core in shuffled_cores if full_graph.has_edge(start_node, core)), None)
    
    if second_node is None:
        print("Error: Could not find two connected Core ASes to start the simulation.")
        sys.exit(1)
    
    shuffled_cores.remove(second_node)
    
    current_subgraph_nodes = {start_node, second_node}
    remaining_core_ases = deque(shuffled_cores)
    remaining_non_core_ases = non_core_ases.copy()
    
    results = []
    step_counter = 0

    print(f"Step {step_counter}: Initializing with 2 Core ASes: {start_node}, {second_node}")
    subgraph = full_graph.subgraph(current_subgraph_nodes)
    subgraph_attrs = {n: full_node_attributes[n] for n in current_subgraph_nodes}
    analyze_subgraph_paths(subgraph, subgraph_attrs, results, step_counter)

    add_core_next = False
    while len(current_subgraph_nodes) < len(all_nodes):
        step_counter += 1
        nodes_added_this_turn = False
        
        if add_core_next and remaining_core_ases:
            core_to_add = next((core for core in list(remaining_core_ases) if any(full_graph.has_edge(core, n) or full_graph.has_edge(n, core) for n in current_subgraph_nodes)), None)
            if core_to_add:
                print(f"\nStep {step_counter}: Adding Core AS '{core_to_add}'")
                current_subgraph_nodes.add(core_to_add)
                remaining_core_ases.remove(core_to_add)
                nodes_added_this_turn = True
        else:
            candidate_leafs = [leaf for leaf in remaining_non_core_ases if any(full_graph.has_edge(leaf, n) or full_graph.has_edge(n, leaf) for n in current_subgraph_nodes)]
            if candidate_leafs:
                num_to_add = min(len(candidate_leafs), random.randint(1, LEAF_CHUNK_SIZE))
                leafs_to_add = random.sample(candidate_leafs, num_to_add)
                print(f"\nStep {step_counter}: Adding {len(leafs_to_add)} leaf ASes (e.g., '{leafs_to_add[0]}')")
                current_subgraph_nodes.update(leafs_to_add)
                remaining_non_core_ases.difference_update(leafs_to_add)
                nodes_added_this_turn = True

        if nodes_added_this_turn:
            subgraph = full_graph.subgraph(current_subgraph_nodes)
            subgraph_attrs = {n: full_node_attributes[n] for n in current_subgraph_nodes}
            analyze_subgraph_paths(subgraph, subgraph_attrs, results, step_counter)
        else:
            print("\nNo more nodes can be connected. Halting.")
            break
        add_core_next = not add_core_next

    # --- Use the new output argument ---
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"\n--- Simulation Run Complete ---")
    print(f"Results from {step_counter+1} growth steps saved to '{args.output}'")


if __name__ == "__main__":
    main()