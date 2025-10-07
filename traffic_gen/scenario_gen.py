import json
import argparse
import random

def parse_capacity(capacity_str):
    """Parses a capacity string (e.g., '100G', '200 Gb/s') and returns the value in Gbps."""
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

def generate_traffic_scenario(graph_data, traffic_percentage, transit_ratio):
    """
    Generates a traffic scenario based on the provided graph data and arguments.

    Args:
        graph_data (dict): The graph data in the specified format.
        traffic_percentage (float): The amount of traffic in relation to the overall aggregated egress interface capacity.
        transit_ratio (float): The ratio of traffic going to destinations reachable over transit and peering vs. peering only.

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
    total_egress_capacity = sum(parse_capacity(iface.get('capacity') or iface.get('link_capacity', '0')) for iface in egress_interfaces)

    # Determine the total traffic amount
    total_traffic = total_egress_capacity * (traffic_percentage / 100.0)

    # Distribute traffic
    transit_traffic = total_traffic * transit_ratio
    peering_traffic = total_traffic * (1 - transit_ratio)

    # Create a single, representative destination
    destinations = ["D_Service"]

    # Assign latencies and costs
    egress_latencies = {}
    egress_costs = {}
    for iface in egress_interfaces:
        iface_id = iface['id']
        if iface in transit_links:
            egress_latencies[iface_id] = random.uniform(50, 100)  # Higher latency for transit
            egress_costs[iface_id] = random.uniform(8, 15)
        else:
            egress_latencies[iface_id] = random.uniform(5, 20)  # Lower latency for peering
            egress_costs[iface_id] = random.uniform(1, 5)


    # Build the output structure
    scenario = {
        "endhosts": endhosts,
        "egress_interfaces": [iface['id'] for iface in egress_interfaces],
        "destinations": destinations,
        "paths_per_endhost": {host: [f"p_{host}_{iface['id']}" for iface in egress_interfaces] for host in endhosts},
        "path_to_egress_mapping": {f"p_{host}_{iface['id']}": iface['id'] for host in endhosts for iface in egress_interfaces},
        "egress_to_destination_reachability": {iface['id']: destinations for iface in egress_interfaces},
        "endhost_uplinks": {host: 100 for host in endhosts},  # Assuming 100G uplinks
        "egress_capacities": {iface['id']: parse_capacity(iface.get('capacity') or iface.get('link_capacity', '0')) for iface in egress_interfaces},
        "egress_costs": egress_costs,
        "egress_latencies": egress_latencies,
        "traffic_per_destination": {"D_Service": total_traffic}
    }

    return scenario

def main():
    parser = argparse.ArgumentParser(description="Generate a traffic scenario from a graph.")
    parser.add_argument("graph_file", help="Path to the graph JSON file.")
    parser.add_argument("traffic_percentage", type=float, help="Amount of traffic in relation to the overall aggregated egress interface capacity.")
    parser.add_argument("transit_ratio", type=float, help="Ratio defining how much traffic goes to destinations that are reachable over transit and peering (0.0 to 1.0).")
    parser.add_argument("-o", "--output_file", help="Path to the output JSON file.", default="traffic_scenario.json")


    args = parser.parse_args()

    # Load the graph data
    with open(args.graph_file, 'r') as f:
        graph_data = json.load(f)

    # Generate the traffic scenario
    traffic_scenario = generate_traffic_scenario(graph_data, args.traffic_percentage, args.transit_ratio)

    # Write the output to a file
    with open(args.output_file, 'w') as f:
        json.dump(traffic_scenario, f, indent=4)

    print(f"Traffic scenario generated and saved to {args.output_file}")

if __name__ == "__main__":
    main()