import json
import argparse
import random
import pandas as pd

def parse_capacity(capacity_str):
    """Parses a capacity string (e.g., '100G', '200 Gbps') and returns the value in Gbps."""
    if not isinstance(capacity_str, str):
        # Return if it's already a number (float/int)
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

def generate_traffic_scenario(graph_data, traffic_df, traffic_increase_factor=1.0, cost_difference_factor=3.5, prefer_peering=False):
    """
    Generates a realistic traffic scenario with differentiated base and dynamic costs
    for transit vs. peering links.

    Args:
        graph_data (dict): The graph data in the specified format.
        traffic_df (pd.DataFrame): A pandas DataFrame containing the traffic data.
        traffic_increase_factor (float): A factor to scale the traffic volumes.
        cost_difference_factor (float): The multiplier for dynamic transit costs relative to a base cost.
        prefer_peering (bool): If True, do not expose transit paths to destinations reachable via peering.

    Returns:
        dict: The generated traffic scenario.
    """

    # 1. Identify network components from graph data
    endhosts = [node['id'] for node in graph_data['nodes'] if node['type'] == 'internal']
    egress_interfaces = [edge for edge in graph_data['edges'] if edge.get('edge_type') == 'external']

    # Differentiate between transit and peering links for cost assignment
    transit_links = [iface for iface in egress_interfaces if iface.get('link_type') == 'transit']
    peering_links = [iface for iface in egress_interfaces if iface.get('link_type') == 'peering']

    print("--- Identified Link Types ---")
    print(f"Found {len(transit_links)} transit links.")
    print(f"Found {len(peering_links)} peering links.")
    print("-----------------------------\n")
    
    # 2. Load and scale traffic data from the DataFrame
    traffic_df.set_index('to', inplace=True)
    traffic_per_destination = (traffic_df['traffic_out_gbps'] * traffic_increase_factor).to_dict()
    destinations = list(traffic_per_destination.keys())

    # 3. Define egress reachability based on link type
    GRAPH_TO_CSV_NAME_MAP = {
        "g\u00e9ant": "geant", "ams-ix": "amsix", "de-cix": "decix", "belw\u00fc": "belwue2",
        "cern": "cern", "interxion": "interxion", "swissix": "swissix", "cixp": "cixp",
        "cogent": "cogent", "lumen": "lumen", "level3": "level3", "telia": "telia", "tix": "tix"
    }

    egress_to_destination_reachability = {}
    peering_destinations = set()
    for iface in egress_interfaces:
        iface_id = iface['id']
        if iface in transit_links:
            egress_to_destination_reachability[iface_id] = destinations  # Initially, transit reaches all
        else:  # Peering link
            peer_name = iface.get('to')
            mapped_dest_name = GRAPH_TO_CSV_NAME_MAP.get(peer_name, peer_name)
            if mapped_dest_name in destinations:
                egress_to_destination_reachability[iface_id] = [mapped_dest_name]
                peering_destinations.add(mapped_dest_name)
            else:
                egress_to_destination_reachability[iface_id] = []

    # 4. If prefer_peering is True, remove peering destinations from transit reachability
    if prefer_peering:
        print("--- 'prefer_peering' is enabled ---")
        for iface in transit_links:
            iface_id = iface['id']
            original_reachability = egress_to_destination_reachability[iface_id]
            # Filter out destinations that are available via peering
            filtered_reachability = [dest for dest in original_reachability if dest not in peering_destinations]
            egress_to_destination_reachability[iface_id] = filtered_reachability
        print(f"Removed {len(peering_destinations)} peering destinations from all transit link paths.")
        print("--------------------------------------\n")


    # 5. Assign latencies and realistic costs (Base and Dynamic)
    egress_latencies = {}
    egress_base_costs = {}
    egress_dynamic_costs = {}

    # Define cost tiers based on capacity (in Gbps)
    BASE_TRANSIT_COST_10G = 2000    # Monthly base cost for a 10G port
    BASE_TRANSIT_COST_100G = 10000   # Monthly base cost for a 100G port
    BASE_TRANSIT_COST_400G = 30000   # Monthly base cost for a 400G+ port
    BASE_PEERING_PORT_COST = 500    # Flat monthly fee for an IXP port

    BASE_DYNAMIC_COST_UNIT = 1.0    # Base unit for dynamic costs

    print("--- Generating Costs and Latencies ---")
    for iface in egress_interfaces:
        iface_id = iface['id']
        capacity_gbps = parse_capacity(iface.get('capacity') or iface.get('link_capacity', '0'))
        print("Got capacity " + capacity_gbps + " for interface " + iface_id)

        if iface in transit_links:
            # Higher latency for transit
            egress_latencies[iface_id] = random.uniform(50, 70)
            
            # Dynamic cost is higher for transit
            egress_dynamic_costs[iface_id] = BASE_DYNAMIC_COST_UNIT * cost_difference_factor
            
            # Base cost depends on capacity tier
            if capacity_gbps <= 10:
                egress_base_costs[iface_id] = BASE_TRANSIT_COST_10G
            elif capacity_gbps <= 100:
                egress_base_costs[iface_id] = BASE_TRANSIT_COST_100G
            else:
                egress_base_costs[iface_id] = BASE_TRANSIT_COST_400G
            
        else:  # Peering link
            # Lower latency for direct peering
            egress_latencies[iface_id] = random.uniform(10, 20)
            
            # Dynamic cost for peering is 0 (settlement-free)
            egress_dynamic_costs[iface_id] = 0
            
            # Base cost is a low, flat port fee
            egress_base_costs[iface_id] = BASE_PEERING_PORT_COST
    
    print("Example Costs Generated:")
    if transit_links:
        ex_tr = transit_links[0]['id']
        print(f" - Transit Link '{ex_tr}': Base Cost = ${egress_base_costs[ex_tr]}, Dynamic Cost = {egress_dynamic_costs[ex_tr]}/Gbps")
    if peering_links:
        ex_pr = peering_links[0]['id']
        print(f" - Peering Link '{ex_pr}': Base Cost = ${egress_base_costs[ex_pr]}, Dynamic Cost = {egress_dynamic_costs[ex_pr]}/Gbps")
    print("--------------------------------------\n")


    # 6. Build the final scenario dictionary
    scenario = {
        "endhosts": endhosts,
        "egress_interfaces": [iface['id'] for iface in egress_interfaces],
        "destinations": destinations,
        "paths_per_endhost": {host: [f"p_{host}_{iface['id']}" for iface in egress_interfaces] for host in endhosts},
        "path_to_egress_mapping": {f"p_{host}_{iface['id']}": iface['id'] for host in endhosts for iface in egress_interfaces},
        "egress_to_destination_reachability": egress_to_destination_reachability,
        "endhost_uplinks": {host: 100 for host in endhosts},
        "egress_capacities": {iface['id']: capacity_gbps for iface in egress_interfaces},
        "egress_costs": egress_dynamic_costs,      # Dynamic (per-Gbps) costs
        "egress_base_costs": egress_base_costs,    # NEW: Fixed (monthly) costs
        "egress_latencies": egress_latencies,
        "traffic_per_destination": traffic_per_destination
    }

    return scenario

def main():
    parser = argparse.ArgumentParser(description="Generate a realistic traffic scenario from a graph and a traffic data CSV.")
    parser.add_argument("graph_file", help="Path to the graph JSON file.")
    parser.add_argument("traffic_csv_file", help="Path to the traffic data CSV file.")
    parser.add_argument("-o", "--output_file", help="Path to the output JSON file.", default="traffic_scenario.json")
    parser.add_argument("-t", "--traffic_increase_factor", type=float, default=1.0, help="Factor to scale the traffic loaded from the CSV.")
    parser.add_argument("-c", "--cost_difference_factor", type=float, default=3.5, help="Cost difference factor for dynamic transit link costs.")
    parser.add_argument("--prefer_peering", action="store_true", help="If set, do not use transit links for destinations reachable via peering.")
    args = parser.parse_args()

    try:
        with open(args.graph_file, 'r') as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Graph file '{args.graph_file}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{args.graph_file}'.")
        return

    try:
        traffic_df = pd.read_csv(args.traffic_csv_file)
    except FileNotFoundError:
        print(f"Error: Traffic CSV file '{args.traffic_csv_file}' not found.")
        return

    # Generate the traffic scenario
    traffic_scenario = generate_traffic_scenario(graph_data, traffic_df, args.traffic_increase_factor, args.cost_difference_factor, args.prefer_peering)

    # Write the output to a file
    try:
        with open(args.output_file, 'w') as f:
            json.dump(traffic_scenario, f, indent=4)
        print(f"Success! Traffic scenario generated and saved to '{args.output_file}'")
    except IOError as e:
        print(f"Error: Could not write to output file '{args.output_file}': {e}")


if __name__ == "__main__":
    main()