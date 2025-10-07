import json
import argparse
from collections import defaultdict

def simulate_fair_share(data_filepath):
    """
    Simulates a "fair share" scenario where end-hosts divide their traffic
    equally among all available paths to a destination, constrained by capacity.

    Args:
        data_filepath (str): Path to the JSON input file.

    Returns:
        dict: A dictionary containing the simulation results.
    """
    # 1. Load data from JSON
    try:
        with open(data_filepath, 'r') as f:
            problem_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{data_filepath}' not found.")
        return None

    # 2. Extract data and initialize capacities
    H = problem_data.get("endhosts", [])
    paths_per_endhost = problem_data.get("paths_per_endhost", {})
    path_map = problem_data.get("path_to_egress_mapping", {})
    reachability = problem_data.get("egress_to_destination_reachability", {})
    costs = problem_data.get("egress_costs", {})
    traffic_demands = problem_data.get("traffic_per_destination", {})
    
    rem_uplink_cap = problem_data.get("endhost_uplinks", {}).copy()
    rem_egress_cap = problem_data.get("egress_capacities", {}).copy()

    allocation = defaultdict(float)
    total_cost = 0
    unsent_traffic = defaultdict(float)

    # Distribute total destination demand among end-hosts
    total_uplink_cap = sum(rem_uplink_cap.values())
    if total_uplink_cap == 0: return None
    host_traffic_demands = defaultdict(lambda: defaultdict(float))
    for dest, total_demand in traffic_demands.items():
        for host in H:
            host_share = rem_uplink_cap.get(host, 0) / total_uplink_cap
            host_traffic_demands[host][dest] = total_demand * host_share
            
    print("--- Simulating Fair Share (Pillar 2) ---")

    # Process traffic for each host-destination pair
    for h in H:
        for d, traffic_to_send in host_traffic_demands[h].items():
            
            # Find all possible paths for this h->d flow
            available_paths = []
            for path in paths_per_endhost.get(h, []):
                egress = path_map.get(path)
                if egress and d in reachability.get(egress, []):
                    available_paths.append((path, egress))

            if not available_paths:
                unsent_traffic[d] += traffic_to_send
                continue

            # **CORE LOGIC CHANGE**
            # Distribute traffic equally among available paths
            num_paths = len(available_paths)
            print(f"Flow {h}->{d}: Found {num_paths} paths. Distributing {traffic_to_send:.2f} units.")
            
            # This loop attempts to push a fair share down each path
            # A more complex model could iterate, but this is a strong first-order approximation
            for path, egress in available_paths:
                ideal_share = traffic_to_send / num_paths
                
                # Constrain by remaining capacities
                uplink_capacity = rem_uplink_cap.get(h, 0)
                egress_capacity = rem_egress_cap.get(egress, 0)
                
                sent_traffic = min(ideal_share, uplink_capacity, egress_capacity)
                
                if sent_traffic > 0:
                    allocation_key = f"{h}_{path}_to_{d}"
                    allocation[allocation_key] += sent_traffic
                    rem_uplink_cap[h] -= sent_traffic
                    rem_egress_cap[egress] -= sent_traffic
                    total_cost += sent_traffic * costs.get(egress, 0)
    
    # After allocation, calculate total unsent traffic
    total_demand = sum(traffic_demands.values())
    total_sent = sum(allocation.values())
    final_unsent = total_demand - total_sent


    results = {
        "scenario": "fair_share_endhosts",
        "objective_value": total_cost,
        "traffic_allocation": allocation,
        "unsent_traffic_due_to_congestion": final_unsent
    }
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a 'fair share' traffic scenario.")
    parser.add_argument("input_file", help="Path to the JSON input file.")
    parser.add_argument("output_file", help="Path to save the JSON simulation result.")
    args = parser.parse_args()
    results = simulate_fair_share(args.input_file)
    if results:
        with open(args.output_file, 'w') as f: json.dump(results, f, indent=4)
        print(f"\nSimulation results saved to '{args.output_file}'")
        print(f"\n--- Fair Share Simulation Summary ---")
        print(f"Resulting ISP Cost: {results['objective_value']:.2f}")
        print(f"Total Unsent Traffic (Congestion): {results['unsent_traffic_due_to_congestion']:.2f}")