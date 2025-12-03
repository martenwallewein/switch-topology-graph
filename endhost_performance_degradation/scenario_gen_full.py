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
    latency_inflation=None  # Added parameter
):
    """
    Generates a realistic traffic scenario with differentiated base and dynamic costs
    for transit vs. peering links.

    Args:
        graph_data (dict): The graph data in the specified format.
        traffic_df (pd.DataFrame): A pandas DataFrame containing the traffic data.
        traffic_increase_factor (float): A factor to scale the traffic volumes.
        cost_difference_factor (float): The multiplier for dynamic transit costs relative to a base cost.
        prefer_peering (bool): If True, do not expose transit paths to destinations reachable via peering.
        transit_base_cost (float, optional): If provided, overrides default transit base costs.
        peering_base_cost (float, optional): If provided, overrides default peering base costs.
        peering_variable_cost (float, optional): If provided, overrides default peering variable costs.
        use_worst_case_links (bool): If True, sets latency to correlate with capacity, making low-capacity links have the lowest latency.
        latency_inflation (float, optional): If provided, configures the increase of latency for the second best path 
                                             compared to the first best path for each destination.

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
    if 'to' in traffic_df.columns:
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

    # First, determine all destinations reachable via any peering link
    for iface in peering_links:
        peer_name = iface.get('to')
        mapped_dest_name = GRAPH_TO_CSV_NAME_MAP.get(peer_name, peer_name)
        if mapped_dest_name in destinations:
            peering_destinations.add(mapped_dest_name)

    # Now, build the reachability for all interfaces
    for iface in egress_interfaces:
        iface_id = iface['id']
        if iface in peering_links:
            # Peering links can only reach the directly connected peer
            peer_name = iface.get('to')
            mapped_dest_name = GRAPH_TO_CSV_NAME_MAP.get(peer_name, peer_name)
            if mapped_dest_name in destinations:
                egress_to_destination_reachability[iface_id] = [mapped_dest_name]
            else:
                egress_to_destination_reachability[iface_id] = []
        else:  # Transit link
            # A transit link can reach all peering destinations plus its own transit neighbor.
            reachable_destinations = list(peering_destinations)
            
            # Add the specific transit provider for this link
            transit_provider_name = iface.get('to')
            mapped_transit_name = GRAPH_TO_CSV_NAME_MAP.get(transit_provider_name, transit_provider_name)
            
            if mapped_transit_name in destinations and mapped_transit_name not in reachable_destinations:
                reachable_destinations.append(mapped_transit_name)
            
            egress_to_destination_reachability[iface_id] = reachable_destinations

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
    egress_capacities = {}

    # Define cost tiers based on capacity (in Gbps)
    BASE_TRANSIT_COST_10G = 2000
    BASE_TRANSIT_COST_100G = 10000
    BASE_TRANSIT_COST_400G = 30000
    BASE_PEERING_PORT_COST = 500
    BASE_DYNAMIC_COST_UNIT = 1.0

    print("--- Generating Costs and Latencies ---")
    for iface in egress_interfaces:
        iface_id = iface['id']
        capacity_gbps = parse_capacity(iface.get('capacity') or iface.get('link_capacity', '0'))
        print("Got capacity " + str(capacity_gbps) + " for interface " + iface_id)
        egress_capacities[iface_id] = capacity_gbps
        if iface in transit_links:
            egress_latencies[iface_id] = random.uniform(50, 70)
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
            egress_latencies[iface_id] = random.uniform(10, 20)
            egress_dynamic_costs[iface_id] = random.uniform(0.9, 1.1)
            
            if peering_base_cost is not None:
                egress_base_costs[iface_id] = peering_base_cost
            else: 
                egress_base_costs[iface_id] = BASE_PEERING_PORT_COST
    
    print("Example Costs Generated:")
    if transit_links:
        ex_tr = transit_links[0]['id']
        print(f" - Transit Link '{ex_tr}': Base Cost = ${egress_base_costs.get(ex_tr, 'N/A')}, Dynamic Cost = {egress_dynamic_costs.get(ex_tr, 'N/A')}/Gbps")
    if peering_links:
        ex_pr = peering_links[0]['id']
        print(f" - Peering Link '{ex_pr}': Base Cost = ${egress_base_costs.get(ex_pr, 'N/A')}, Dynamic Cost = {egress_dynamic_costs.get(ex_pr, 'N/A')}/Gbps")
    print("--------------------------------------\n")

    # 6. If use_worst_case_links is True, override latencies based on capacity
    if use_worst_case_links:
        print("--- Applying worst-case link logic ---")
        # Invert reachability to map destinations to their available egress links
        destination_to_egress_links = {}
        for iface_id, destinations_list in egress_to_destination_reachability.items():
            for dest in destinations_list:
                if dest not in destination_to_egress_links:
                    destination_to_egress_links[dest] = []
                destination_to_egress_links[dest].append(iface_id)

        # For each destination, sort its links by capacity and assign new latencies.
        # A link's final latency will be the minimum it's assigned across all destinations it can reach.
        final_latencies = {}
        for dest, links in destination_to_egress_links.items():
            # Sort links for this destination by their capacity (ascending)
            sorted_links = sorted(links, key=lambda link_id: egress_capacities[link_id])

            # Assign latencies based on sorted order (lowest capacity gets lowest latency)
            for i, link_id in enumerate(sorted_links):
                # Use a simple ascending latency scheme, e.g., 10, 11, 12...
                new_latency = 10.0 + i
                
                # If the link already has a latency assigned (from another destination's sort),
                # keep the lower of the two to ensure it remains attractive.
                if link_id not in final_latencies or new_latency < final_latencies[link_id]:
                    final_latencies[link_id] = new_latency
        
        # Override the original latencies with the new worst-case latencies.
        for link_id, latency in final_latencies.items():
            egress_latencies[link_id] = latency
        
        print("Worst-case latencies assigned based on link capacity.")
        print("--------------------------------------\n")
    
    # --- NEW LOGIC: LATENCY INFLATION ---
    if latency_inflation is not None:
        print(f"--- Applying Latency Inflation (Factor: {latency_inflation}) ---")
        
        # Build destination to egress links map
        dest_to_egress = {}
        for iface_id, reach_dests in egress_to_destination_reachability.items():
            for d in reach_dests:
                dest_to_egress.setdefault(d, []).append(iface_id)
        
        # Temp storage for calculating min latency per link
        link_target_latencies = {} 
        
        BASE_LATENCY = 10.0
        STEP_LATENCY = 5.0 # Delta for 3rd, 4th, etc. paths

        for dest, links in dest_to_egress.items():
            if not links:
                continue
            
            # Randomly choose the best path out of all paths to a given destination
            random.shuffle(links)
            
            # Assign target latencies for this destination's view
            # Link 0 (Best): Base
            # Link 1 (2nd): Base * Inflation
            # Link 2+ : Higher
            
            for rank, link_id in enumerate(links):
                if rank == 0:
                    val = BASE_LATENCY
                elif rank == 1:
                    val = BASE_LATENCY * latency_inflation
                else:
                    # Ensure strictly higher than 2nd best (even if inflation is 1.0)
                    base_2nd = BASE_LATENCY * latency_inflation
                    val = base_2nd + (rank - 1) * STEP_LATENCY
                
                # We want to assign latencies to global links. Since a link is shared,
                # we keep the lowest assigned latency to ensure that if a link is 'Best'
                # for someone, it retains the 'Best' latency value.
                if link_id not in link_target_latencies:
                    link_target_latencies[link_id] = val
                else:
                    link_target_latencies[link_id] = min(link_target_latencies[link_id], val)

        # Apply to global egress_latencies (overrides previous random or worst-case values)
        for link_id, lat in link_target_latencies.items():
            egress_latencies[link_id] = lat
            
        print("Latencies adjusted based on inflation factor.")
        print("--------------------------------------\n")
    # --- END NEW LOGIC ---

    # 7. Build the final scenario dictionary
    scenario = {
        "endhosts": endhosts,
        "egress_interfaces": [iface['id'] for iface in egress_interfaces],
        "destinations": destinations,
        "paths_per_endhost": {host: [f"p_{host}_{iface['id']}" for iface in egress_interfaces] for host in endhosts},
        "path_to_egress_mapping": {f"p_{host}_{iface['id']}": iface['id'] for host in endhosts for iface in egress_interfaces},
        "egress_to_destination_reachability": egress_to_destination_reachability,
        "endhost_uplinks": {host: 100 for host in endhosts},
        "egress_capacities": egress_capacities,
        "egress_costs": egress_dynamic_costs,
        "egress_base_costs": egress_base_costs,
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
    
    parser.add_argument("--transit-base-cost", type=float, default=None, help="Override default base cost for all transit links.")
    parser.add_argument("--peering-base-cost", type=float, default=None, help="Override default base cost for all peering links.")
    parser.add_argument("--peering-variable-cost", type=float, default=None, help="Override default variable (per-Gbps) cost for all peering links.")
    parser.add_argument("--use_worst_case_links", action="store_true", help="Set latency to be inversely proportional to capacity to create a worst-case scenario for latency-based routing.")
    
    # --- ADDED PARAMETER ---
    parser.add_argument("--latency_inflation", type=float, default=None, help="Configures the increase of latency for the second best path compared to the first best path (1 = equal, 2 = double).")

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

    # Generate the traffic scenario, passing the new arguments
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
        args.latency_inflation # Pass the new parameter
    )

    # Write the output to a file
    try:
        with open(args.output_file, 'w') as f:
            json.dump(traffic_scenario, f, indent=4)
        print(f"Success! Traffic scenario generated and saved to '{args.output_file}'")
    except IOError as e:
        print(f"Error: Could not write to output file '{args.output_file}': {e}")


if __name__ == "__main__":
    main()