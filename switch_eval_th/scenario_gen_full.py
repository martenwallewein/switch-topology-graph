import json
import argparse
import random
import pandas as pd
from collections import defaultdict, Counter

def parse_capacity(capacity_str):
    """Parses a capacity string (e.g., '100G', '200 Gbps') and returns the value in Gbps."""
    if not isinstance(capacity_str, str):
        return float(capacity_str)
    
    capacity_str = capacity_str.lower().replace(' ', '').replace('b/s', '')
    
    if 'g' in capacity_str:
        return float(capacity_str.replace('g', ''))
    elif 'm' in capacity_str:
        return float(capacity_str.replace('m', '')) / 1000
    elif 'k' in capacity_str:
        return float(capacity_str.replace('k', '')) / 1_000_000
    else:
        return float(capacity_str)

def generate_traffic_scenario(
    graph_data,
    traffic_df,
    traffic_increase_factor=1.0,
    cost_difference_factor=3.5,
    prefer_peering=False,
    transit_base_cost=None,
    peering_base_cost=None,
    peering_variable_cost=None,
    use_worst_case_links=False,
    single_path_per_dest=False
):
    """
    Generates a realistic traffic scenario.
    """

    # 1. Identify network components
    endhosts = [node['id'] for node in graph_data['nodes'] if node['type'] == 'internal']
    egress_interfaces = [edge for edge in graph_data['edges'] if edge.get('edge_type') == 'external']

    transit_links = [iface for iface in egress_interfaces if iface.get('link_type') == 'transit']
    peering_links = [iface for iface in egress_interfaces if iface.get('link_type') == 'peering']

    print("--- Identified Link Types ---")
    print(f"Found {len(transit_links)} transit links.")
    print(f"Found {len(peering_links)} peering links.")
    print("-----------------------------\n")
    
    # 2. Load and scale traffic data
    if 'to' in traffic_df.columns:
        traffic_df.set_index('to', inplace=True)
    traffic_per_destination = (traffic_df['traffic_out_gbps'] * traffic_increase_factor).to_dict()
    destinations = list(traffic_per_destination.keys())

    # 3. Define egress reachability
    GRAPH_TO_CSV_NAME_MAP = {
        "g\u00e9ant": "geant", "ams-ix": "ams-ix", "de-cix": "de-cix", "belw\u00fc": "belwue",
        "cern": "cern", "interxion": "interxion", "swissix": "swissix", "cixp": "cixp",
        "cogent": "cogent", "lumen": "lumen", "level3": "level3", "telia": "telia", "tix": "tix",
        "geant ias": "g\u00e9ant", 
    }

    egress_to_destination_reachability = {}
    peering_destinations = set()

    for iface in peering_links:
        peer_name = iface.get('to')
        mapped_dest_name = GRAPH_TO_CSV_NAME_MAP.get(peer_name, peer_name)
        if mapped_dest_name in destinations:
            peering_destinations.add(mapped_dest_name)

    for iface in egress_interfaces:
        iface_id = iface['id']
        if iface in peering_links:
            peer_name = iface.get('to')
            mapped_dest_name = GRAPH_TO_CSV_NAME_MAP.get(peer_name, peer_name)
            if mapped_dest_name in destinations:
                egress_to_destination_reachability[iface_id] = [mapped_dest_name]
            else:
                egress_to_destination_reachability[iface_id] = []
        else:  # Transit link
            reachable_destinations = list(peering_destinations)
            transit_provider_name = iface.get('to')
            mapped_transit_name = GRAPH_TO_CSV_NAME_MAP.get(transit_provider_name, transit_provider_name)
            
            if mapped_transit_name in destinations and mapped_transit_name not in reachable_destinations:
                reachable_destinations.append(mapped_transit_name)
            
            egress_to_destination_reachability[iface_id] = reachable_destinations

    # 4. Filter peering if preferred
    if prefer_peering:
        print("--- 'prefer_peering' is enabled ---")
        for iface in transit_links:
            iface_id = iface['id']
            original_reachability = egress_to_destination_reachability[iface_id]
            filtered_reachability = [dest for dest in original_reachability if dest not in peering_destinations]
            egress_to_destination_reachability[iface_id] = filtered_reachability
        print(f"Removed peering destinations from transit paths.")
        print("--------------------------------------\n")


    # 5. Assign Costs and Latencies
    egress_latencies = {}
    egress_base_costs = {}
    egress_dynamic_costs = {}
    egress_capacities = {}

    BASE_TRANSIT_COST_10G = 2000
    BASE_TRANSIT_COST_100G = 10000
    BASE_TRANSIT_COST_400G = 30000
    BASE_PEERING_PORT_COST = 500

    print("--- Generating Costs and Latencies ---")
    for iface in egress_interfaces:
        iface_id = iface['id']
        capacity_gbps = parse_capacity(iface.get('capacity') or iface.get('link_capacity', '0'))
        egress_capacities[iface_id] = capacity_gbps
        
        if iface in transit_links:
            egress_latencies[iface_id] = random.uniform(10, 20) # random.uniform(5, 10)
            egress_dynamic_costs[iface_id] = cost_difference_factor * random.uniform(0.9, 1.1)
            
            if transit_base_cost is not None:
                egress_base_costs[iface_id] = transit_base_cost
            else: 
                if capacity_gbps <= 10:
                    egress_base_costs[iface_id] = BASE_TRANSIT_COST_10G
                elif capacity_gbps <= 100:
                    egress_base_costs[iface_id] = BASE_TRANSIT_COST_100G
                else:
                    egress_base_costs[iface_id] = BASE_TRANSIT_COST_400G
            
        else:  # Peering link
            egress_latencies[iface_id] = random.uniform(5, 10) # random.uniform(10, 20)
            egress_dynamic_costs[iface_id] = random.uniform(0.9, 1.1)
            
            if peering_base_cost is not None:
                egress_base_costs[iface_id] = peering_base_cost
            else: 
                egress_base_costs[iface_id] = BASE_PEERING_PORT_COST
    
    # 6. Apply worst-case link logic
    if use_worst_case_links:
        print("--- Applying worst-case link logic ---")
        destination_to_egress_links = {}
        for iface_id, destinations_list in egress_to_destination_reachability.items():
            for dest in destinations_list:
                if dest not in destination_to_egress_links:
                    destination_to_egress_links[dest] = []
                destination_to_egress_links[dest].append(iface_id)

        final_latencies = {}
        for dest, links in destination_to_egress_links.items():
            sorted_links = sorted(links, key=lambda link_id: egress_capacities[link_id], reverse=True)
            for i, link_id in enumerate(sorted_links):
                new_latency = 10.0 + i
                if link_id not in final_latencies or new_latency < final_latencies[link_id]:
                    final_latencies[link_id] = new_latency
        
        for link_id, latency in final_latencies.items():
            egress_latencies[link_id] = latency
        print("Worst-case latencies assigned.")
        print("--------------------------------------\n")

    # --- UPDATED LOGIC: STRICT 1-TO-1 LEAST-USED ASSIGNMENT ---
    final_reachability_map = egress_to_destination_reachability
    
    if single_path_per_dest:
        print("--- Applying Strict 1-Path Per Host/Dest with Global Load Balancing ---")
        
        # 1. Map Destination -> [List of Valid Interfaces]
        dest_to_valid_ifaces = defaultdict(list)
        for iface_id, dests in egress_to_destination_reachability.items():
            for d in dests:
                dest_to_valid_ifaces[d].append(iface_id)
        
        # Sort for determinism
        for d in dest_to_valid_ifaces:
            dest_to_valid_ifaces[d].sort()

        # 2. Track usage of interfaces globally to force distribution
        # This ensures that even if we have 1 host, we rotate through interfaces 
        # as we iterate through destinations.
        interface_usage_counts = Counter({iface['id']: 0 for iface in egress_interfaces})
        
        # 3. Build Path-Specific Reachability
        path_specific_reachability = {}
        # Pre-fill keys
        for host in endhosts:
            for iface in egress_interfaces:
                pid = f"p_{host}_{iface['id']}"
                path_specific_reachability[pid] = []

        # 4. Iterate and Assign
        # We iterate hosts then destinations. For every pair, we pick the interface
        # that is valid for that destination AND has the lowest global usage so far.
        for host in endhosts:
            for dest in destinations:
                valid_ifaces = dest_to_valid_ifaces.get(dest, [])
                
                if not valid_ifaces:
                    continue # No reachability
                
                # GREEDY SELECTION:
                # Filter valid interfaces for this dest, find the one with min usage count.
                # If ties, the sort order (alphabetical) handles it, or we could randomize.
                best_iface_id = min(valid_ifaces, key=lambda x: interface_usage_counts[x])
                
                # Assign
                path_id = f"p_{host}_{best_iface_id}"
                path_specific_reachability[path_id].append(dest)
                
                # Increment usage so next time we might pick a different one
                interface_usage_counts[best_iface_id] += 1
        
        # Override the global map
        final_reachability_map = path_specific_reachability
        
        print("Distribution Complete. Interface Usage Counts (Assignments):")
        for iface_id, count in interface_usage_counts.items():
            print(f"  {iface_id}: {count}")
        print("--------------------------------------\n")
    # -------------------------------------------------------

    # 7. Build final scenario
    scenario = {
        "endhosts": endhosts,
        "egress_interfaces": [iface['id'] for iface in egress_interfaces],
        "destinations": destinations,
        "paths_per_endhost": {host: [f"p_{host}_{iface['id']}" for iface in egress_interfaces] for host in endhosts},
        "path_to_egress_mapping": {f"p_{host}_{iface['id']}": iface['id'] for host in endhosts for iface in egress_interfaces},
        "egress_to_destination_reachability": final_reachability_map,
        "endhost_uplinks": {host: 10000 for host in endhosts},
        "egress_capacities": egress_capacities,
        "egress_costs": egress_dynamic_costs,
        "egress_base_costs": egress_base_costs,
        "egress_latencies": egress_latencies,
        "traffic_per_destination": traffic_per_destination
    }

    return scenario

def main():
    parser = argparse.ArgumentParser(description="Generate a realistic traffic scenario.")
    parser.add_argument("graph_file", help="Path to the graph JSON file.")
    parser.add_argument("traffic_csv_file", help="Path to the traffic data CSV file.")
    parser.add_argument("-o", "--output_file", help="Path to the output JSON file.", default="traffic_scenario.json")
    parser.add_argument("-t", "--traffic_increase_factor", type=float, default=1.0, help="Factor to scale traffic.")
    parser.add_argument("-c", "--cost_difference_factor", type=float, default=3.5, help="Cost factor for dynamic transit.")
    parser.add_argument("--prefer_peering", action="store_true", help="Prefer peering links over transit.")
    
    parser.add_argument("--transit-base-cost", type=float, default=None, help="Override base cost for transit.")
    parser.add_argument("--peering-base-cost", type=float, default=None, help="Override base cost for peering.")
    parser.add_argument("--peering-variable-cost", type=float, default=None, help="Override variable cost for peering.")
    parser.add_argument("--use_worst_case_links", action="store_true", help="Set latency inversely proportional to capacity.")
    
    parser.add_argument("--single-path-per-dest", action="store_true", help="Force 1 path per host/dest, balancing globally to use all paths.")

    args = parser.parse_args()

    try:
        with open(args.graph_file, 'r') as f:
            graph_data = json.load(f)
    except Exception as e:
        print(f"Error reading graph file: {e}")
        return

    try:
        traffic_df = pd.read_csv(args.traffic_csv_file)
    except Exception as e:
        print(f"Error reading traffic CSV: {e}")
        return

    traffic_scenario = generate_traffic_scenario(
        graph_data,
        traffic_df,
        args.traffic_increase_factor,
        args.cost_difference_factor,
        args.prefer_peering,
        args.transit_base_cost,
        args.peering_base_cost,
        args.peering_variable_cost,
        args.use_worst_case_links,
        args.single_path_per_dest
    )

    try:
        with open(args.output_file, 'w') as f:
            json.dump(traffic_scenario, f, indent=4)
        print(f"Success! Saved to '{args.output_file}'")
    except IOError as e:
        print(f"Error writing output: {e}")

if __name__ == "__main__":
    main()