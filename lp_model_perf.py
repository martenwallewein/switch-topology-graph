import json
import argparse
from pulp import LpProblem, LpMinimize, LpMaximize, LpVariable, lpSum, LpStatus, value

def solve_time_optimization(data_filepath, optimization_goal="maximize"):
    """
    Solves the data transfer time optimization problem using Linear Programming.
    Aims to minimize/maximize the time until ALL data is transferred.

    Args:
        data_filepath (str): Path to the JSON file with the input data.
        optimization_goal (str): "minimize" or "maximize" the effective throughput.

    Returns:
        tuple: (status, results_dict)
    """
    # 1. Load data from JSON
    try:
        with open(data_filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{data_filepath}' not found.")
        return None, None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{data_filepath}'.")
        return None, None

    # 2. Extract Sets and Parameters
    H = data.get("endhosts", [])
    E = data.get("egress_interfaces", [])
    D = data.get("destinations", [])
    paths_per_endhost = data.get("paths_per_endhost", {})
    path_to_egress_mapping = data.get("path_to_egress_mapping", {})
    reachability = data.get("egress_to_destination_reachability", {})
    U = data.get("endhost_uplinks", {})
    Cap = data.get("egress_capacities", {})
    
    # NEW: Data volumes and latencies
    V_dest = data.get("data_volumes_per_destination", {})
    L_egress = data.get("egress_latencies", {})

    if not all([H, E, D, V_dest]):
        print("Error: Core data (hosts, egresses, destinations, volumes) is missing.")
        return "Input_Error", None

    # 3. Create the LP Problem
    if optimization_goal.lower() == "minimize":
        problem_name = "Worst_Case_Transfer_Time"
        problem_sense = LpMinimize # Minimize Z -> Maximize Time
        print("Setting up LP to MINIMIZE effective throughput (=> WORST case time)")
    else:
        problem_name = "Best_Case_Transfer_Time"
        problem_sense = LpMaximize # Maximize Z -> Minimize Time
        print("Setting up LP to MAXIMIZE effective throughput (=> BEST case time)")
    
    prob = LpProblem(problem_name, problem_sense)

    # 4. Define Decision Variables
    # x_hpd is the traffic RATE (e.g., in Gbps)
    x_vars_keys = []
    for h in H:
        for p in paths_per_endhost.get(h, []):
            egress = path_to_egress_mapping.get(p)
            if not egress: continue
            reachable_dests = reachability.get(egress, [])
            for d in reachable_dests:
                if d in D:
                    x_vars_keys.append((h, p, d))

    x = LpVariable.dicts("x", x_vars_keys, lowBound=0, cat='Continuous')

    # NEW: The objective variable 'Z' (effective throughput, in units of 1/time)
    Z = LpVariable("Z_effective_throughput", lowBound=0, cat='Continuous')

    # 5. Define the Objective Function
    # The goal is simply to maximize or minimize Z.
    prob += Z, "Effective_Throughput"

    # 6. Define Constraints

    # NEW: Constraint 1: Bottleneck Throughput Constraint
    # For each destination 'd', the allocated rate must be sufficient to transfer
    # the volume V_d at an effective throughput of Z.
    # Σ_{h,p} x_hpd >= V_d * Z
    for d_dest in D:
        volume = V_dest.get(d_dest, 0)
        if volume > 0:
            rate_to_dest = lpSum(x[(h,p,d)] for h,p,d in x_vars_keys if d == d_dest)
            prob += rate_to_dest >= volume * Z, f"Bottleneck_Constraint_{d_dest}"

    # Constraint 2: Endhost Uplink Capacity (same as before)
    for h_host in H:
        traffic_from_host = lpSum(x[(h,p,d)] for h,p,d in x_vars_keys if h == h_host)
        prob += traffic_from_host <= U.get(h_host, 0), f"Uplink_Capacity_{h_host}"

    # Constraint 3: Egress Interface Capacity (same as before)
    for e_egress in E:
        traffic_on_egress = lpSum(x[(h,p,d)] for h,p,d in x_vars_keys if path_to_egress_mapping.get(p) == e_egress)
        prob += traffic_on_egress <= Cap.get(e_egress, 0), f"Egress_Capacity_{e_egress}"

    # 7. Solve the Problem
    print("Solving LP problem...")
    prob.solve()

    # 8. Extract and Post-Process Results
    status = LpStatus[prob.status]
    if status != 'Optimal':
        return status, {}

    z_value = value(Z)
    duration = (1 / z_value) if z_value and z_value > 1e-9 else float('inf')

    allocation = {}
    for h, p, d in x_vars_keys:
        val = x[(h, p, d)].varValue
        if val is not None and val > 1e-6:
            allocation[(h, p, d)] = val
    
    # Post-processing: Calculate latencies and final completion times
    destination_details = {}
    for d_dest in D:
        total_rate_to_dest = sum(val for (h,p,d), val in allocation.items() if d == d_dest)
        
        avg_latency = 0
        if total_rate_to_dest > 1e-9:
            weighted_latency_sum = sum(
                val * L_egress.get(path_to_egress_mapping.get(p), 0)
                for (h,p,d), val in allocation.items() if d == d_dest
            )
            avg_latency = weighted_latency_sum / total_rate_to_dest
            
        destination_details[d_dest] = {
            "allocated_rate": total_rate_to_dest,
            "data_volume": V_dest.get(d_dest, 0),
            "avg_latency_ms": avg_latency,
            "completion_time_sec": avg_latency / 1000.0 + duration
        }

    results = {
        "lp_status": status,
        "optimization_goal": optimization_goal,
        "effective_throughput_Z": z_value,
        "transfer_duration_sec": duration,
        "destination_details": destination_details,
        "rate_allocation_gbps": {f"{h}_{p}_to_{d}": v for (h,p,d), v in allocation.items()}
    }
    return status, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solve for best/worst case data transfer time.")
    parser.add_argument("input_file", help="Path to the JSON input file.")
    parser.add_argument("output_file", help="Path to save the JSON solution.")
    parser.add_argument("--goal", choices=["minimize", "maximize"], default="maximize", help="Maximize Z for best time, minimize Z for worst time.")
    args = parser.parse_args()

    status, results = solve_time_optimization(args.input_file, args.goal)

    if results:
        try:
            with open(args.output_file, 'w') as f:
                json.dump(results, f, indent=4)
            print(f"\nSolution successfully saved to '{args.output_file}'")
        except IOError as e:
            print(f"\nError writing to file: {e}")

        print(f"\n--- Time Optimization Summary ---")
        print(f"Status: {results['lp_status']}")
        print(f"Transfer Duration (bandwidth-dependent): {results['transfer_duration_sec']:.2f} seconds")
        print("\nCompletion Time per Destination (including latency):")
        for dest, details in results['destination_details'].items():
            print(f"  - {dest}: {details['completion_time_sec']:.2f} sec (Rate: {details['allocated_rate']:.2f} Gbps, Latency: {details['avg_latency_ms']:.1f} ms)")
    else:
        print(f"\nLP solving failed with status: {status}")
    print("-" * 50)