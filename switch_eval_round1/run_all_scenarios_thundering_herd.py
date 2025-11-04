import json
import argparse
from collections import defaultdict
from pulp import LpProblem, LpMinimize, LpMaximize, LpVariable, lpSum, LpStatus, value

# --- HELPER / UTILITY FUNCTIONS ---

def load_json_data(filepath):
    """Loads and validates the input JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"FATAL: Input file '{filepath}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"FATAL: Could not decode JSON from '{filepath}'.")
        return None

def analyze_performance_of_result(problem_data, solution_data):
    """
    Calculates performance metrics for a given solution and adds them to the dict.
    This is the logic from performance_analyzer.py.
    """
    # Return early if there's an error in the solution data
    if "error" in solution_data:
        return solution_data

    capacities = problem_data.get("egress_capacities", {})
    path_map = problem_data.get("path_to_egress_mapping", {})
    allocation = solution_data.get("traffic_allocation", {})
    
    traffic_on_egress = defaultdict(float)
    for key, traffic_volume in allocation.items():
        # Key is like "h1_p_h1_e2_to_D_Peer_e2"
        path_id = key.split('_to_')[0].split('_', 1)[1]
        egress = path_map.get(path_id)
        if egress:
            traffic_on_egress[egress] += traffic_volume

    utilization_metrics = {}
    for egress, capacity in capacities.items():
        traffic = traffic_on_egress[egress]
        util = (traffic / capacity) * 100 if capacity > 0 else 0
        utilization_metrics[egress] = {
            "traffic": round(traffic, 2),
            "capacity": capacity,
            "utilization_percent": round(util, 2)
        }
    solution_data["performance_analysis"] = {"egress_utilization": utilization_metrics}
    return solution_data


# --- MODEL 1: LP COST SOLVER (from model_with_destinations.py) ---

def solve_cost_lp(problem_data, optimization_goal):
    # (Code from model_with_destinations.py, adapted to take data dict directly)
    H = problem_data.get("endhosts", [])
    E = problem_data.get("egress_interfaces", [])
    D = problem_data.get("destinations", [])
    paths_per_endhost = problem_data.get("paths_per_endhost", {})
    path_map = problem_data.get("path_to_egress_mapping", {})
    reachability = problem_data.get("egress_to_destination_reachability", {})
    U = problem_data.get("endhost_uplinks", {})
    Cap = problem_data.get("egress_capacities", {})
    Cost = problem_data.get("egress_costs", {})
    T_dest = problem_data.get("traffic_per_destination", {})

    prob = LpProblem("Cost_LP", LpMinimize if optimization_goal == "minimize" else LpMaximize)

    x_vars_keys = []
    for h in H:
        for p in paths_per_endhost.get(h, []):
            egress = path_map.get(p)
            if not egress or egress not in Cost: continue
            for d in reachability.get(egress, []):
                if d in D: x_vars_keys.append((h, p, d))

    if not x_vars_keys: return {"error": "No valid variables for LP model."}
    
    x = LpVariable.dicts("x", x_vars_keys, lowBound=0)
    prob += lpSum(x[(h,p,d)] * Cost.get(path_map.get(p),0) for h,p,d in x_vars_keys), "Total_Cost"

    for d_dest in D:
        prob += lpSum(x[(h,p,d)] for h,p,d in x_vars_keys if d == d_dest) == T_dest.get(d_dest, 0)
    for h_host in H:
        prob += lpSum(x[(h,p,d)] for h,p,d in x_vars_keys if h == h_host) <= U.get(h_host, 0)
    for e_egress in E:
        prob += lpSum(x[(h,p,d)] for h,p,d in x_vars_keys if path_map.get(p) == e_egress) <= Cap.get(e_egress, 0)

    prob.solve()
    
    allocation = {f"{h}_{p}_to_{d}": v.varValue for (h,p,d), v in x.items() if v.varValue and v.varValue > 1e-6}
    
    return {
        "scenario_name": f"ISP {'Optimal' if optimization_goal == 'minimize' else 'Pessimal'} (Cost LP)",
        "lp_status": LpStatus[prob.status],
        "total_cost": round(value(prob.objective), 2) if prob.objective else 0.0,
        "traffic_allocation": allocation
    }

# --- MODEL 2 & 3: BEHAVIORAL SIMULATORS ---

def run_behavioral_sim(problem_data, mode, use_transit_links=True):
    # (Combines logic from thundering_herd_simulator.py and fair_share_simulator.py)
    H, D = problem_data.get("endhosts", []), problem_data.get("destinations", [])
    paths_per_endhost = problem_data.get("paths_per_endhost", {})
    path_map = problem_data.get("path_to_egress_mapping", {})
    reachability = problem_data.get("egress_to_destination_reachability", {})
    costs = problem_data.get("egress_costs", {})
    latencies = problem_data.get("egress_latencies", {})
    egress_types = problem_data.get("egress_types", {}) # NEW: Get egress types
    T_dest = problem_data.get("traffic_per_destination", {})
    rem_uplink = problem_data.get("endhost_uplinks", {}).copy()
    rem_egress = problem_data.get("egress_capacities", {}).copy()

    total_uplink = sum(rem_uplink.values())
    if total_uplink == 0: return {"error": "Total uplink capacity is zero."}
    
    # Distribute traffic demand proportionally to host uplink capacity
    host_demands = defaultdict(lambda: defaultdict(float))
    for dest, demand in T_dest.items():
        for host in H:
            host_demands[host][dest] = demand * (rem_uplink.get(host, 0) / total_uplink)

    allocation = defaultdict(float)
    # Iterate through each host
    for h in H:
        # Iterate through each destination the host wants to send traffic to
        for d, demand in host_demands[h].items():
            # Find all possible paths from the host to the destination
            possible_paths = []
            for path in paths_per_endhost.get(h, []):
                egress = path_map.get(path)
                # Check if the path's egress can reach the destination
                if egress and d in reachability.get(egress, []):
                    # NEW: Filter out transit links if they are disabled
                    if not use_transit_links:
                        if egress_types.get(egress) == 'transit':
                            continue # Skip this path if it's a transit link

                    possible_paths.append({
                        "path": path, 
                        "egress": egress, 
                        "latency": latencies.get(egress, float('inf'))
                    })
            
            if not possible_paths: 
                continue

            # --- BEHAVIORAL LOGIC ---

            if mode == 'thundering_herd':
                # Sort paths by latency, from best to worst
                sorted_paths = sorted(possible_paths, key=lambda x: x['latency'])
                
                remaining_demand = demand
                # Iterate through sorted paths, filling them one by one
                for p_info in sorted_paths:
                    if remaining_demand <= 1e-6: # Stop if demand is met
                        break

                    # Determine how much traffic can be sent on this path
                    # It's the minimum of remaining demand, host uplink, and egress capacity
                    can_send = min(remaining_demand, 
                                   rem_uplink.get(h, 0), 
                                   rem_egress.get(p_info['egress'], 0))
                    
                    if can_send > 0:
                        key = f"{h}_{p_info['path']}_to_{d}"
                        allocation[key] += can_send
                        rem_uplink[h] -= can_send
                        rem_egress[p_info['egress']] -= can_send
                        remaining_demand -= can_send
            
            else: # fair_share logic (unchanged)
                paths_to_use = possible_paths
                # Distribute demand evenly across all possible paths
                traffic_per_path = demand / len(paths_to_use) if paths_to_use else 0
                
                for p_info in paths_to_use:
                    # Send the minimum of the fair share, remaining uplink, and remaining egress capacity
                    sent = min(traffic_per_path, rem_uplink.get(h,0), rem_egress.get(p_info['egress'],0))
                    if sent > 0:
                        key = f"{h}_{p_info['path']}_to_{d}"
                        allocation[key] += sent
                        rem_uplink[h] -= sent
                        rem_egress[p_info['egress']] -= sent
    
    # Calculate final metrics for the simulation run
    total_cost = sum(v * costs.get(path_map.get(k.split('_to_')[0].split('_',1)[1]), 0) for k,v in allocation.items())
    total_sent = sum(allocation.values())
    total_demand = sum(T_dest.values())
    
    # NEW: Update scenario name based on whether transit links were used
    name_suffix = "(All Links)" if use_transit_links else "(Peering Only)"
    
    return {
        "scenario_name": f"End-Host {'Selfish (Thundering Herd)' if mode == 'thundering_herd' else 'Cooperative (Fair Share)'} {name_suffix}",
        "total_cost": round(total_cost, 2),
        "total_sent_traffic": round(total_sent, 2),
        "total_unsent_traffic": round(total_demand - total_sent, 2),
        "traffic_allocation": dict(allocation)
    }

# --- MAIN EXECUTION ---

def main():
    parser = argparse.ArgumentParser(
        description="Run a full suite of scenario analyses (LP, Thundering Herd, Fair Share) on a single input file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("input_file", help="Path to the master JSON input file for the scenario.")
    parser.add_argument("output_file", help="Path to save the consolidated JSON results report.")
    args = parser.parse_args()

    print(f"--- Running Full Scenario Analysis on '{args.input_file}' ---")
    problem_data = load_json_data(args.input_file)
    if not problem_data:
        return

    all_results = {}

    # 1. ISP Optimal (Min Cost)
    print("1. Calculating ISP-Optimal (Min Cost)...")
    min_cost_res = solve_cost_lp(problem_data, "minimize")
    all_results["isp_optimal"] = analyze_performance_of_result(problem_data, min_cost_res)

    # 2. ISP Pessimal (Max Cost)
    print("2. Calculating ISP-Pessimal (Max Cost)...")
    max_cost_res = solve_cost_lp(problem_data, "maximize")
    all_results["isp_pessimal"] = analyze_performance_of_result(problem_data, max_cost_res)
    
    # 3. Thundering Herd (All Links)
    print("3. Simulating Thundering Herd (All Links)...")
    herd_res_all = run_behavioral_sim(problem_data, "thundering_herd", use_transit_links=True)
    all_results["thundering_herd_all_links"] = analyze_performance_of_result(problem_data, herd_res_all)

    # 4. Thundering Herd (Peering Only)
    print("4. Simulating Thundering Herd (Peering Only)...")
    herd_res_peering = run_behavioral_sim(problem_data, "thundering_herd", use_transit_links=False)
    all_results["thundering_herd_peering_only"] = analyze_performance_of_result(problem_data, herd_res_peering)

    # 5. Fair Share (All Links)
    print("5. Simulating Fair Share (All Links)...")
    fair_res_all = run_behavioral_sim(problem_data, "fair_share", use_transit_links=True)
    all_results["fair_share_all_links"] = analyze_performance_of_result(problem_data, fair_res_all)

    # 6. Fair Share (Peering Only)
    print("6. Simulating Fair Share (Peering Only)...")
    fair_res_peering = run_behavioral_sim(problem_data, "fair_share", use_transit_links=False)
    all_results["fair_share_peering_only"] = analyze_performance_of_result(problem_data, fair_res_peering)

    # Save consolidated results
    try:
        with open(args.output_file, 'w') as f:
            json.dump(all_results, f, indent=4)
        print(f"\n--- Analysis Complete. Consolidated report saved to '{args.output_file}' ---")
    except IOError as e:
        print(f"\nError: Could not write results to file: {e}")

if __name__ == "__main__":
    main()