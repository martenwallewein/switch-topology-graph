import json
import argparse
from collections import defaultdict

def analyze_performance(input_filepath, solution_filepath):
    """
    Analyzes the performance of a traffic allocation produced by the cost model.

    Args:
        input_filepath (str): The original input JSON file for the cost model.
        solution_filepath (str): The solution JSON file from the cost model.
    """
    # 1. Load both the original problem and the solution
    try:
        with open(input_filepath, 'r') as f:
            problem_data = json.load(f)
        with open(solution_filepath, 'r') as f:
            solution_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON - {e}")
        return

    # 2. Extract necessary info from the problem data
    capacities = problem_data.get("egress_capacities", {})
    latencies = problem_data.get("egress_latencies", {}) # Assuming latencies are now in the cost input
    path_map = problem_data.get("path_to_egress_mapping", {})
    
    # 3. Reconstruct the traffic flow from the solution data
    allocation = solution_data.get("traffic_allocation", {})
    traffic_on_egress = defaultdict(float)
    traffic_to_destination = defaultdict(float)
    weighted_latency_sum = 0
    total_traffic = 0

    for key, traffic_volume in allocation.items():
        # Key is like "h1_p_h1_e2_to_D_Peer_e2"
        parts = key.split('_to_')
        h_p_part = parts[0]
        dest = parts[1]
        
        # Find the path identifier, which could have underscores
        # Example: h_p = "h1_p_h1_e2" -> path_id = "p_h1_e2"
        path_id_parts = h_p_part.split('_', 1) # Split only on the first underscore
        if len(path_id_parts) > 1:
            path_id = path_id_parts[1]
        else:
            print(f"Warning: Could not parse path from key '{key}'. Skipping.")
            continue

        egress = path_map.get(path_id)
        if not egress:
            print(f"Warning: No egress mapping for path '{path_id}'. Skipping.")
            continue

        # Aggregate metrics
        traffic_on_egress[egress] += traffic_volume
        traffic_to_destination[dest] += traffic_volume
        
        if latencies:
            weighted_latency_sum += traffic_volume * latencies.get(egress, 0)
        
        total_traffic += traffic_volume

    # 4. Calculate and Print Performance Metrics
    print("-" * 50)
    print(f"Performance Analysis for: {solution_filepath}")
    print(f"Based on Input: {input_filepath}")
    print(f"Total Traffic Transferred: {total_traffic:.2f}")
    print(f"Total Operator Cost: {solution_data.get('objective_value', 0):.2f}")
    print("-" * 50)

    # Metric 1: Egress Link Utilization (Congestion)
    # This is the key metric for your Pillars 2 and 3.
    print("\n--- Egress Link Utilization (Congestion) ---")
    for egress, capacity in capacities.items():
        traffic = traffic_on_egress[egress]
        utilization = (traffic / capacity) * 100 if capacity > 0 else 0
        print(f"  - Egress '{egress}':")
        print(f"    - Traffic: {traffic:.2f} / {capacity:.2f}")
        print(f"    - Utilization: {utilization:.2f}%")
        if utilization > 90:
            print("    - STATUS: HEAVILY CONGESTED")
        elif utilization > 70:
            print("    - STATUS: HIGHLY UTILIZED")


    # Metric 2: Weighted Average Latency
    if latencies and total_traffic > 0:
        avg_latency = weighted_latency_sum / total_traffic
        print("\n--- Overall Network Performance ---")
        print(f"  - Weighted Average Latency (across all traffic): {avg_latency:.2f} ms")

    print("\n" + "-" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze the performance (congestion, latency) of a given traffic allocation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("input_file", help="Path to the original JSON input file (used for capacities, etc.).")
    parser.add_argument("solution_file", help="Path to the JSON solution file from the cost model.")
    args = parser.parse_args()

    analyze_performance(args.input_file, args.solution_file)