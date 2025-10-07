import json
import argparse
from pulp import LpProblem, LpMinimize, LpMaximize, LpVariable, lpSum, LpStatus, value

def solve_adversarial_path_selection(data_filepath, optimization_goal="maximize"):
    """
    Solves the adversarial path selection problem with destination-awareness
    using Linear Programming.

    Args:
        data_filepath (str): Path to the JSON file containing the input data.
        optimization_goal (str): "minimize" or "maximize" the operator cost.

    Returns:
        tuple: (problem_status, objective_value, traffic_allocation)
    """
    # 1. Load data from JSON
    try:
        with open(data_filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{data_filepath}' not found.")
        return None, None, None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{data_filepath}'.")
        return None, None, None

    # 2. Extract Sets and Parameters
    H = data.get("endhosts", [])
    E = data.get("egress_interfaces", [])
    paths_per_endhost = data.get("paths_per_endhost", {})
    U = data.get("endhost_uplinks", {})
    Cap = data.get("egress_capacities", {})
    Cost = data.get("egress_costs", {})
    path_to_egress_mapping = data.get("path_to_egress_mapping", {})
    
    # NEW: Destination-related parameters
    D = data.get("destinations", [])
    T_dest = data.get("traffic_per_destination", {})
    reachability = data.get("egress_to_destination_reachability", {})
    
    total_traffic_required = sum(T_dest.values())

    # Input validation
    if not all([H, E, D, T_dest]):
        print("Error: 'endhosts', 'egress_interfaces', 'destinations', or 'traffic_per_destination' are missing/empty.")
        return "Input_Error", None, None

    # 3. Create the LP Problem
    if optimization_goal.lower() == "minimize":
        problem_name = "Minimize_Operator_Cost_With_Destinations"
        problem_sense = LpMinimize
    else:
        problem_name = "Maximize_Operator_Cost_With_Destinations"
        problem_sense = LpMaximize
    
    prob = LpProblem(problem_name, problem_sense)
    print(f"Setting up LP problem to {problem_sense} cost for {total_traffic_required} total traffic.")

    # 4. Define Decision Variables (x_hpd)
    # NEW: Variables now include a destination 'd' and are only created if
    # the path's egress interface can reach the destination.
    x_vars_keys = []
    for h in H:
        for p in paths_per_endhost.get(h, []):
            egress = path_to_egress_mapping.get(p)
            if not egress or egress not in Cost:
                print(f"Warning: Path '{p}' for host '{h}' missing egress mapping or cost. Ignored.")
                continue
            
            # Check which destinations this path can reach
            reachable_dests_for_path = reachability.get(egress, [])
            for d in reachable_dests_for_path:
                if d in D: # Ensure the destination is valid
                    x_vars_keys.append((h, p, d))

    if not x_vars_keys:
        print("Error: No valid (endhost, path, destination) combinations found.")
        return "No_Variables", 0, {}

    x = LpVariable.dicts("x", x_vars_keys, lowBound=0, cat='Continuous')

    # 5. Define the Objective Function
    # The structure is similar, but it sums over the new x_hpd variables.
    objective_terms = []
    for h_key, p_key, d_key in x_vars_keys:
        egress_for_path = path_to_egress_mapping.get(p_key)
        cost_for_egress = Cost.get(egress_for_path, 0)
        objective_terms.append(x[(h_key, p_key, d_key)] * cost_for_egress)

    prob += lpSum(objective_terms), "Total_Operator_Cost"

    # 6. Define Constraints

    # NEW: Constraint 1: Total traffic to each destination MUST EQUAL its required amount.
    for d_dest in D:
        required_traffic = T_dest.get(d_dest, 0)
        # Sum of all traffic from all hosts/paths to this specific destination 'd_dest'
        traffic_to_d_terms = lpSum(
            x[(h, p, d)] for h, p, d in x_vars_keys if d == d_dest
        )
        prob += traffic_to_d_terms == required_traffic, f"Traffic_To_Destination_{d_dest}"
        print(f"Constraint added: Total traffic to '{d_dest}' must equal {required_traffic}")

    # Constraint 2: Endhost Uplink Capacity (updated to sum over destinations)
    for h_host in H:
        traffic_from_host = lpSum(x[(h,p,d)] for h,p,d in x_vars_keys if h == h_host)
        prob += traffic_from_host <= U.get(h_host, 0), f"Uplink_Capacity_{h_host}"

    # Constraint 3: Egress Interface Capacity (updated to sum over destinations)
    for e_egress in E:
        traffic_on_egress = lpSum(x[(h,p,d)] for h,p,d in x_vars_keys if path_to_egress_mapping.get(p) == e_egress)
        prob += traffic_on_egress <= Cap.get(e_egress, 0), f"Egress_Capacity_{e_egress}"

    # 7. Solve the Problem
    print("Solving LP problem...")
    prob.solve()

    # 8. Extract and Return Results
    status = LpStatus[prob.status]
    obj_value = value(prob.objective) if prob.objective is not None else 0.0

    traffic_allocation = {}
    if status == 'Optimal':
        for h, p, d in x_vars_keys:
            val = x[(h, p, d)].varValue
            if val is not None and val > 1e-6:
                traffic_allocation[(h, p, d)] = val
    
    return status, obj_value, traffic_allocation

# --- Main Execution (if __name__ == "__main__":) is updated for new output format ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Solve the destination-aware adversarial path selection problem.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("input_file", help="Path to the JSON file with destination data.")
    parser.add_argument("output_file", help="Path to save the JSON solution file.")
    parser.add_argument("--goal", choices=["minimize", "maximize"], default="maximize", help="Optimization goal.")
    args = parser.parse_args()

    print(f"--- Destination-Aware Path Selection LP Solver ---")
    print(f"Input data file: '{args.input_file}'")
    print(f"Optimization goal: {args.goal.upper()} operator cost")
    print("-" * 50)

    status, objective_value, allocation = solve_adversarial_path_selection(args.input_file, args.goal)

    json_friendly_allocation = {}
    if allocation:
        for (h, p, d), traffic in allocation.items():
            json_friendly_allocation[f"{h}_{p}_to_{d}"] = traffic

    results_to_save = {
        "input_file": args.input_file,
        "optimization_goal": args.goal,
        "lp_status": status,
        "objective_value": objective_value if objective_value is not None else 0.0,
        "traffic_allocation": json_friendly_allocation
    }

    try:
        with open(args.output_file, 'w') as f:
            json.dump(results_to_save, f, indent=4)
        print(f"\nLP solution results successfully saved to '{args.output_file}'")
    except IOError as e:
        print(f"\nError: Could not write results to file: {e}")

    if status:
        print(f"\n--- LP Solution Summary ---")
        print(f"Status: {status}")
        print(f"Optimized Operator Cost (Z): {objective_value:.2f}")

        if allocation:
            print("\nTraffic Allocation (x_hpd):")
            for (h, p, d), traffic in sorted(allocation.items()):
                 print(f"  {h} -> {p} -> Dest {d}: {traffic:.2f} units")
    else:
        print("\nLP solving did not proceed due to input errors.")
    print("-" * 50)