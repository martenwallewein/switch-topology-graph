import sys
import networkx as nx
import xml.etree.ElementTree as ET
from collections import defaultdict
import itertools
import json
import argparse
import concurrent.futures
import math
import random
from tqdm import tqdm

def parse_scion_graph(graphml_string):
    """
    Parses the GraphML XML string into a NetworkX MultiDiGraph.
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
    """
    Converts a list of nodes into a detailed list including edge IDs.
    """
    if not node_path or len(node_path) < 2:
        return node_path
    
    detailed_path = [node_path[0]]
    for i in range(len(node_path) - 1):
        u, v = node_path[i], node_path[i+1]
        edge_data_dict = graph.get_edge_data(u, v)
        if edge_data_dict:
            first_key = list(edge_data_dict.keys())[0]
            edge_id = edge_data_dict[first_key].get('id', 'N/A')
            detailed_path.extend([edge_id, v])
        else:
            detailed_path.extend(['unknown_edge', v])
            
    return detailed_path

def find_path_segments(graph, node_attrs):
    """
    Finds all up-segments and core-segments in the graph.
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
            if (nc_as in hierarchy_graph and c_as in hierarchy_graph and
                    node_attrs[c_as].get('isd') == nc_isd and
                    nx.has_path(hierarchy_graph, nc_as, c_as)):
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
    Combines segments to find all end-to-end paths.
    """
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

def run_beaconing_on_graph(graph, node_attributes):
    up_segments, core_segments = find_path_segments(graph, node_attributes)
    all_end_to_end_paths = combine_all_paths(graph, node_attributes, up_segments, core_segments)
    return all_end_to_end_paths

def process_combination(node_combo, full_graph, full_node_attributes):
    """
    Runs the simulation on a single node combination if it's connected.
    Returns the average number of paths per node pair, or None if disconnected.
    """
    subgraph = full_graph.subgraph(node_combo).copy()
    
    # --- NEW: Check for graph connectivity ---
    # We check weak connectivity by converting to undirected.
    if not nx.is_connected(subgraph.to_undirected()):
        return None  # Signal that this subgraph was skipped

    subgraph_node_attrs = {node: full_node_attributes[node] for node in node_combo}
    paths_in_subgraph = run_beaconing_on_graph(subgraph, subgraph_node_attrs)
    
    total_paths = sum(len(dest_paths) for destinations in paths_in_subgraph.values() for dest_paths in destinations.values())
    
    # --- NEW: Calculate average per node pair ---
    num_nodes = len(node_combo)
    num_possible_pairs = num_nodes * (num_nodes - 1)
    
    if num_possible_pairs == 0:
        return 0.0

    return total_paths / num_possible_pairs

def main():
    parser = argparse.ArgumentParser(
        description="Run a SCION beaconing simulation on connected graph subgraphs."
    )
    parser.add_argument("graphml_file", help="Path to the SCION topology GraphML file.")
    parser.add_argument("-c", "--max-combinations", type=int, default=100, help="Max node combinations to test per subgraph size (default: 100).")
    parser.add_argument("-t", "--threads", type=int, default=None, help="Number of worker threads (default: CPU cores).")
    args = parser.parse_args()

    try:
        with open(args.graphml_file, 'r', encoding='utf-8') as f:
            graphml_data = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at '{args.graphml_file}'")
        sys.exit(1)
        
    full_graph, full_node_attributes = parse_scion_graph(graphml_data)
    all_nodes = list(full_graph.nodes())
    num_total_nodes = len(all_nodes)
    
    results_database = {}

    print("--- Starting Beaconing Simulation on Connected Subgraphs ---")
    print(f"Using up to {args.max_combinations} combinations per subgraph size.")
    print(f"Using up to {args.threads or 'default'} worker threads.")

    for size in range(2, num_total_nodes + 1):
        subgraph_averages = []
        disconnected_skipped_count = 0
        
        total_combinations_for_size = math.comb(num_total_nodes, size)
        combinations_to_process_count = min(total_combinations_for_size, args.max_combinations)

        print(f"\n--- Processing Subgraph Size: {size} ---")
        if combinations_to_process_count == 0:
            print("No combinations to process.")
            continue
        
        print(f"({combinations_to_process_count} of {total_combinations_for_size} total combinations will be sampled)")

        # Efficiently sample combinations to test
        if total_combinations_for_size > args.max_combinations:
            indices = sorted(random.sample(range(total_combinations_for_size), combinations_to_process_count))
            all_combos_gen = itertools.combinations(all_nodes, size)
            
            combinations_to_process = []
            current_index = 0
            next_sample_index = 0
            for combo in all_combos_gen:
                if current_index == indices[next_sample_index]:
                    combinations_to_process.append(combo)
                    next_sample_index += 1
                    if next_sample_index == len(indices): break
                current_index += 1
        else:
            combinations_to_process = list(itertools.combinations(all_nodes, size))

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [executor.submit(process_combination, combo, full_graph, full_node_attributes) for combo in combinations_to_process]
            
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(combinations_to_process), desc=f"Size {size}"):
                try:
                    result = future.result()
                    if result is not None:
                        subgraph_averages.append(result)
                    else:
                        disconnected_skipped_count += 1
                except Exception as e:
                    print(f"\nAn error occurred in a worker thread: {e}")

        # Final average is the average of the per-subgraph averages
        final_average_for_size = sum(subgraph_averages) / len(subgraph_averages) if subgraph_averages else 0
            
        print(f"  - Subgraph Size: {size} -> Average paths per node pair: {final_average_for_size:.4f}")
        if disconnected_skipped_count > 0:
            print(f"    ({disconnected_skipped_count} disconnected subgraphs were skipped)")

        results_database[size] = {
            "subgraph_size": size,
            "average_paths_per_node_pair": final_average_for_size,
            "connected_subgraphs_processed": len(subgraph_averages),
            "disconnected_subgraphs_skipped": disconnected_skipped_count,
            "combinations_sampled": combinations_to_process_count
        }

    output_filename = "beaconing_simulation_results.json"
    with open(output_filename, 'w') as f:
        json.dump(results_database, f, indent=4)
        
    print(f"\n--- Simulation Complete ---")
    print(f"Results have been saved to '{output_filename}'")

if __name__ == "__main__":
    main()