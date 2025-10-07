import json
import argparse
import random
import math

def parse_capacity(capacity_str):
    """Parses a capacity string (e.g., '100G', '200 Gb/s', '1000M') and returns the value in Gbps."""
    if not isinstance(capacity_str, str):
        return 0.0
    capacity_str = capacity_str.lower().replace(' ', '')
    try:
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
            return float(capacity_str) / 1000 # Assume bps if no unit
    except (ValueError, TypeError):
        return 0.0

def generate_traffic_scenario(graph_data, traffic_percentage, transit_ratio, num_destinations):
    """
    Generates a traffic scenario based on the provided graph data and arguments.

    Args:
        graph_data (dict): The graph data in the specified format.
        traffic_percentage (float): The amount of traffic in relation to the overall aggregated egress interface capacity.
        transit_ratio (float): The ratio of traffic and destinations that are reachable only over transit links.
        num_destinations (int): The total number of destinations to be targeted with traffic.

    Returns:
        dict: The generated traffic scenario in the specified format.
    """

    # Identify internal nodes (end hosts) and external links (egress interfaces)
    endhosts = [node['id'] for node in graph_data['nodes'] if node['type'] == 'internal']
    egress_interfaces = [edge for edge in graph_data['edges'] if edge.get('edge_type') == 'external']

    # Differentiate between transit and peering links
    transit_links = [iface for iface in egress_interfaces if iface.get('link_type') == 'transit']
    peering_links = [iface for iface in egress_interfaces if iface.get('link_type') == 'peering']

    # Calculate the total egress capacity
    total_egress_capacity = sum(parse_capacity(iface.get('capacity') or iface.get('link_capacity')) for iface in egress_interfaces)
    if total_egress_capacity == 0:
        raise ValueError("Total egress capacity is zero. Cannot generate traffic.")

    # Determine the total traffic amount
    total_traffic = total_egress_capacity * (traffic_percentage / 100.0)

    # --- Destination and Traffic Distribution ---
    # Determine the number of destinations for each category based on the ratio
    num_transit_only_dest = round(num_destinations * transit_ratio)
    num_universal_dest = num_destinations - num_transit_only_dest

    # Create destination names
    transit_only_destinations = [f"D_Transit_Only_{i+1}" for i in range(num_transit_only_dest)]
    universal_destinations = [f"D_Universal_{i+1}" for i in range(num_universal_dest)]
    all_destinations = transit_only_destinations + universal_destinations

    # Split total traffic according to the ratio
    traffic_for_transit_only = total_traffic * transit_ratio
    traffic_for_universal = total_traffic * (1 - transit_ratio)

    # Calculate traffic per destination
    traffic_per_destination = {}
    if num_transit_only_dest > 0:
        avg_traffic_transit = traffic_for_transit_only / num_transit_only_dest
        for dest in transit_only_destinations:
            traffic_per_destination[dest] = avg_traffic_transit

    if num_universal_dest > 0:
        avg_traffic_universal = traffic_for_universal / num_universal_dest
        for dest in universal_destinations:
            traffic_per_destination[dest] = avg_traffic_universal
            
    # Define reachability for each egress type
    egress_to_destination_reachability = {}
    for iface in egress_interfaces:
        iface_id = iface['id']
        if iface in transit_links:
            # Transit links can reach ALL destinations
            egress_to_destination_reachability[iface_id] = all_destinations
        else:
            # Peering links can only reach the universal destinations
            egress_to_destination_reachability[iface_id] = universal_destinations

    # Assign latencies and costs
    egress_latencies = {}
    egress_costs = {}
    for iface in egress_interfaces:
        iface_id = iface['id']
        if iface in transit_links:
            egress_latencies[iface_id] = random.uniform(50, 100)  # Higher latency for transit
            egress_costs[iface_id] = random.uniform(8, 15)       # Higher cost for transit
        else:
            egress_latencies[iface_id] = random.uniform(5, 20)   # Lower latency for peering
            egress_costs[iface_id] = random.uniform(1, 5)        # Lower cost for peering

    # Build the output structure
    scenario = {
        "endhosts": endhosts,
        "egress_interfaces": [iface['id'] for iface in egress_interfaces],
        "destinations": all_destinations,
        "paths_per_endhost": {host: [f"p_{host}_{iface['id']}" for iface in egress_interfaces] for host in endhosts},
        "path_to_egress_mapping": {f"p_{host}_{iface['id']}": iface['id'] for host in endhosts for iface in egress_interfaces},
        "egress_to_destination_reachability": egress_to_destination_reachability,
        "endhost_uplinks": {host: 100 for host in endhosts},  # Assuming 100G uplinks
        "egress_capacities": {iface['id']: parse_capacity(iface.get('capacity') or iface.get('link_capacity')) for iface in egress_interfaces},
        "egress_costs": egress_costs,
        "egress_latencies": egress_latencies,
        "traffic_per_destination": traffic_per_destination
    }

    return scenario

def main():
    parser = argparse.ArgumentParser(description="Generate a traffic scenario from a network graph.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("graph_file", help="Path to the graph JSON file.")
    parser.add_argument("traffic_percentage", type=float, help="Total traffic volume as a percentage of the aggregated egress capacity.")
    parser.add_argument("transit_ratio", type=float, help="Ratio (0.0 to 1.0) of destinations and traffic reachable only via transit.")
    parser.add_argument("num_destinations", type=int, help="Total number of external destinations to generate.")
    parser.add_argument("-o", "--output_file", default="traffic_scenario.json", help="Path to the output JSON file.")

    args = parser.parse_args()
    
    if not 0.0 <= args.transit_ratio <= 1.0:
        raise argparse.ArgumentTypeError("transit_ratio must be between 0.0 and 1.0")

    # Load the graph data
    try:
        with open(args.graph_file, 'r') as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {args.graph_file} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {args.graph_file}.")
        return

    # Generate the traffic scenario
    traffic_scenario = generate_traffic_scenario(graph_data, args.traffic_percentage, args.transit_ratio, args.num_destinations)

    # Write the output to a file
    with open(args.output_file, 'w') as f:
        json.dump(traffic_scenario, f, indent=4)

    print(f"Traffic scenario with {args.num_destinations} destinations generated successfully.")
    print(f"Output saved to {args.output_file}")

if __name__ == "__main__":
    main()