import json
import argparse
import random
import pandas as pd

def parse_capacity(capacity_str):
    """Parses a capacity string (e.g., '100G', '200 Gb/s') and returns the value in Gbps."""
    if not isinstance(capacity_str, str):
        return float(capacity_str)
    capacity_str = capacity_str.lower().replace(' ', '')
    if 'gb/s' in capacity_str:
        return float(capacity_str.replace('gb/s', ''))
    elif 'g' in capacity_str:
        return float(capacity_str.replace('g', ''))
    elif 'mbps' in capacity_str:
        return float(capacity_str.replace('mbps', '')) / 1000
    elif 'm' in capacity_str:
        return float(capacity_str.replace('m', '')) / 1000
    elif 'kbps' in capacity_str:
        return float(capacity_str.replace('kbps', '')) / 1000000
    elif 'k' in capacity_str:
        return float(capacity_str.replace('k', '')) / 1000000
    else:
        return float(capacity_str)

def generate_traffic_scenario(graph_data, traffic_df, traffic_increase_factor=1.0, cost_difference_factor=3.5):
    """
    Generates a realistic traffic scenario based on graph data and a CSV with traffic information.

    Args:
        graph_data (dict): The graph data in the specified format.
        traffic_df (pd.DataFrame): A pandas DataFrame containing the traffic data from the CSV.
        traffic_increase_factor (float): A factor by which to increase the traffic loaded from the CSV.
        cost_difference_factor (float): The cost difference factor between peering and transit links.
    Returns:
        dict: The generated traffic scenario in the specified format.
    """

    # Identify internal nodes (end hosts) and external links (egress interfaces)
    endhosts = [node['id'] for node in graph_data['nodes'] if node['type'] == 'internal']
    egress_interfaces = [edge for edge in graph_data['edges'] if edge.get('edge_type') == 'external']

    # Differentiate between transit and peering links
    transit_links = [iface for iface in egress_interfaces if iface.get('link_type') == 'transit']
    print("Transit Links:")
    print(transit_links)
    peering_links = [iface for iface in egress_interfaces if iface.get('link_type') == 'peering']
    print("Peering Links:")
    print(peering_links)

    # --- NEW: Load traffic data from the DataFrame ---
    # Use the 'to' column for destination names and 'traffic_out_gbps' for the traffic value
    traffic_df.set_index('to', inplace=True)
    traffic_per_destination = traffic_df['traffic_out_gbps'].to_dict()
    destinations = list(traffic_per_destination.keys())
    
    # --- MODIFIED: Increase traffic by the specified factor ---
    for destination, traffic in traffic_per_destination.items():
        traffic_per_destination[destination] = traffic * traffic_increase_factor

    # --- NEW: Define egress reachability based on link type ---
    # This map helps handle minor naming differences between the graph and the CSV (e.g., "ams-ix" vs "amsix")
    GRAPH_TO_CSV_NAME_MAP = {
        "g\u00e9ant": "geant",
        "ams-ix": "amsix",
        "de-cix": "decix",
        "belw\u00fc": "belwue2",
        "cern": "cern",
        "interxion": "interxion",
        "swissix": "swissix",
        "cixp": "cixp",
        "cogent": "cogent",
        "lumen": "lumen",
        "level3": "level3",
        "telia": "telia",
        "tix": "tix"
    }

    egress_to_destination_reachability = {}
    for iface in egress_interfaces:
        iface_id = iface['id']
        if iface in transit_links:
            # Transit links can reach all destinations
            egress_to_destination_reachability[iface_id] = destinations
        else: # Peering link
            peer_name = iface.get('to')
            # Find the corresponding destination name from the CSV
            mapped_dest_name = GRAPH_TO_CSV_NAME_MAP.get(peer_name, peer_name)
            
            # If this peer is a destination in our traffic file, it can reach it
            if mapped_dest_name in destinations:
                egress_to_destination_reachability[iface_id] = [mapped_dest_name]
            else:
                # Otherwise, this peering link doesn't lead to any of the specified destinations
                egress_to_destination_reachability[iface_id] = []

    # Assign latencies and costs (retains original random logic)
    egress_latencies = {}
    egress_costs = {}
    for iface in egress_interfaces:
        iface_id = iface['id']
        if iface in transit_links:
            egress_latencies[iface_id] = random.uniform(50, 100)  # Higher latency for transit
            peering_cost = 1 # random.uniform(3, 5)
            egress_costs[iface_id] = peering_cost * cost_difference_factor
        else:
            egress_latencies[iface_id] = random.uniform(5, 20)  # Lower latency for peering
            egress_costs[iface_id] = 1 #random.uniform(3, 5)

    # Build the output structure
    scenario = {
        "endhosts": endhosts,
        "egress_interfaces": [iface['id'] for iface in egress_interfaces],
        "destinations": destinations,
        "paths_per_endhost": {host: [f"p_{host}_{iface['id']}" for iface in egress_interfaces] for host in endhosts},
        "path_to_egress_mapping": {f"p_{host}_{iface['id']}": iface['id'] for host in endhosts for iface in egress_interfaces},
        "egress_to_destination_reachability": egress_to_destination_reachability,
        "endhost_uplinks": {host: 100 for host in endhosts},  # Assuming 100G uplinks
        "egress_capacities": {iface['id']: parse_capacity(iface.get('capacity') or iface.get('link_capacity', '0')) for iface in egress_interfaces},
        "egress_costs": egress_costs,
        "egress_latencies": egress_latencies,
        "traffic_per_destination": traffic_per_destination
    }

    return scenario

def main():
    parser = argparse.ArgumentParser(description="Generate a realistic traffic scenario from a graph and a traffic data CSV.")
    parser.add_argument("graph_file", help="Path to the graph JSON file.")
    parser.add_argument("traffic_csv_file", help="Path to the traffic data CSV file.")
    parser.add_argument("-o", "--output_file", help="Path to the output JSON file.", default="traffic_scenario.json")
    parser.add_argument("-t", "--traffic_increase_factor", type=float, default=1.0, help="Factor by which to increase the traffic loaded from the CSV.")
    # --- NEW: Added the cost_difference_factor argument ---
    parser.add_argument("-c", "--cost_difference_factor", type=float, default=3.5, help="Cost difference factor between peering and transit links.")


    args = parser.parse_args()

    # Load the graph data
    with open(args.graph_file, 'r') as f:
        graph_data = json.load(f)

    # Load the traffic data
    try:
        traffic_df = pd.read_csv(args.traffic_csv_file)
    except FileNotFoundError:
        print(f"Error: The file {args.traffic_csv_file} was not found.")
        return

    # Generate the traffic scenario
    # --- MODIFIED: Pass the new argument to the function ---
    traffic_scenario = generate_traffic_scenario(graph_data, traffic_df, args.traffic_increase_factor, args.cost_difference_factor)

    # Write the output to a file
    with open(args.output_file, 'w') as f:
        json.dump(traffic_scenario, f, indent=4)

    print(f"Traffic scenario generated and saved to {args.output_file}")

if __name__ == "__main__":
    main()