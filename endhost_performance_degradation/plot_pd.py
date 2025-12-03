import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def calculate_congestion_aware_drawback(results_dir):
    """
    Calculates performance drawback considering BOTH path latency inflation
    AND actual link congestion from the simulation results.
    
    Formula: 
    Effective_Latency = Base_Latency * max(1.0, Utilization/100)
    
    We compare:
    1. Single Best Path Strategy: Susceptible to high congestion on Link 1.
    2. ECMP-2 Strategy: Averages the state of Link 1 (Congested) and Link 2 (Inflated but likely freer).
    """
    if not os.path.isdir(results_dir):
        print(f"Error: Directory '{results_dir}' not found.")
        return None

    # Storage: results[inflation] = { 'single_path': [], 'ecmp2': [], 'ecmp3': [] }
    results = defaultdict(lambda: defaultdict(list))
    
    filename_pattern = re.compile(r"result_inflation_(\d+(?:\.\d+)?)_run_(\d+)\.json")
    
    # Latency Constants (Must match generator)
    BASE_LATENCY = 10.0
    STEP_LATENCY = 5.0

    print(f"--> Scanning directory: {results_dir}")

    for filename in os.listdir(results_dir):
        match = filename_pattern.match(filename)
        if match:
            inflation_factor = float(match.group(1))
            file_path = os.path.join(results_dir, filename)

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                # 1. Load Link Utilizations
                # Map "L1" -> 120.5 (percent)
                util_map = {}
                if 'fair_share_latency_optimal_3' in data:
                    perf = data['fair_share_latency_optimal_3'].get('performance_analysis', {})
                    egress_utils = perf.get('egress_utilization', {})
                    for link_id, metrics in egress_utils.items():
                        util_map[link_id] = metrics.get('utilization_percent', 0.0)
                else:
                    continue # Skip if data block missing

                # 2. Analyze Destinations
                congestion_analysis = data['fair_share_latency_optimal_3'].get('congestion_analysis', {})

                for dest, info in congestion_analysis.items():
                    paths = info.get('lowest_latency_paths', [])
                    # paths is a list of link IDs e.g. ["L1", "L2", "L124"] sorted by latency rank
                    
                    num_paths = len(paths)
                    if num_paths == 0: continue

                    # --- Path 1 (Best) ---
                    link_id_1 = paths[0]
                    prop_lat_1 = BASE_LATENCY
                    util_1 = util_map.get(link_id_1, 0.0)
                    # Effective Latency: Propagation * Congestion Factor
                    eff_lat_1 = prop_lat_1 * max(1.0, util_1 / 100.0)

                    # --- Path 2 (2nd Best) ---
                    if num_paths >= 2:
                        link_id_2 = paths[1]
                        prop_lat_2 = BASE_LATENCY * inflation_factor
                        util_2 = util_map.get(link_id_2, 0.0)
                        eff_lat_2 = prop_lat_2 * max(1.0, util_2 / 100.0)
                    else:
                        eff_lat_2 = None # Doesn't exist

                    # --- Path 3 (3rd Best) ---
                    if num_paths >= 3:
                        link_id_3 = paths[2]
                        prop_lat_3 = (BASE_LATENCY * inflation_factor) + STEP_LATENCY
                        util_3 = util_map.get(link_id_3, 0.0)
                        eff_lat_3 = prop_lat_3 * max(1.0, util_3 / 100.0)
                    else:
                        eff_lat_3 = None

                    # --- Calculate Performance Penalties ---
                    # Baseline: The theoretical uncongested best path (10ms)
                    ideal_baseline = BASE_LATENCY

                    # Strategy 1: Single Path (Stubbornly use Best Path)
                    # Penalty comes purely from Congestion on Path 1
                    penalty_single = (eff_lat_1 - ideal_baseline) / ideal_baseline

                    # Strategy 2: ECMP 2
                    if eff_lat_2 is not None:
                        # You split traffic. Avg Latency is the mean of effective latencies.
                        avg_eff_lat = (eff_lat_1 + eff_lat_2) / 2.0
                        penalty_ecmp2 = (avg_eff_lat - ideal_baseline) / ideal_baseline
                    else:
                        penalty_ecmp2 = penalty_single

                    # Strategy 3: ECMP 3
                    if eff_lat_3 is not None:
                        avg_eff_lat = (eff_lat_1 + eff_lat_2 + eff_lat_3) / 3.0
                        penalty_ecmp3 = (avg_eff_lat - ideal_baseline) / ideal_baseline
                    elif eff_lat_2 is not None:
                         # Fallback to 2
                        avg_eff_lat = (eff_lat_1 + eff_lat_2) / 2.0
                        penalty_ecmp3 = (avg_eff_lat - ideal_baseline) / ideal_baseline
                    else:
                        penalty_ecmp3 = penalty_single

                    results[inflation_factor]['single_path'].append(penalty_single)
                    results[inflation_factor]['ecmp2'].append(penalty_ecmp2)
                    results[inflation_factor]['ecmp3'].append(penalty_ecmp3)

            except Exception as e:
                print(f"    Error processing {filename}: {e}")

    return results

def plot_congestion_aware_drawback(data):
    if not data: return

    output_file = "congestion_aware_drawback.pdf"
    
    # Style
    plt.rcParams.update({
        'font.family': 'serif', 'font.size': 10,
        'axes.labelsize': 11, 'axes.titlesize': 11,
        'legend.fontsize': 9, 'lines.linewidth': 2
    })

    fig, ax = plt.subplots(figsize=(7, 5))
    sorted_factors = sorted(data.keys())
    
    # Calculate Global Means
    y_single = [np.mean(data[x]['single_path']) * 100 for x in sorted_factors]
    y_ecmp2  = [np.mean(data[x]['ecmp2']) * 100 for x in sorted_factors]
    y_ecmp3  = [np.mean(data[x]['ecmp3']) * 100 for x in sorted_factors]
    
    # --- Plotting ---
    
    # 1. Single Path (Congestion Vulnerable)
    ax.plot(sorted_factors, y_single, 
            label="Strategy: Single Best Path\n(High Congestion Risk)", 
            color="#d62728", linestyle="-", marker="x", alpha=0.8) # Red

    # 2. ECMP 2 (Load Balanced)
    ax.plot(sorted_factors, y_ecmp2, 
            label="Strategy: ECMP 2 Paths\n(Balances Congestion vs Latency)", 
            color="#1f77b4", linestyle="-", marker="o") # Blue

    # 3. ECMP 3
    ax.plot(sorted_factors, y_ecmp3, 
            label="Strategy: ECMP 3 Paths", 
            color="#2ca02c", linestyle="--", alpha=0.7) # Green

    # Zero Line
    ax.axhline(0, color='black', linewidth=0.8)

    # --- Annotations ---
    # Find Crossover point (Where ECMP becomes worse than Single Path)
    crossover_x = None
    for x, single, ecmp in zip(sorted_factors, y_single, y_ecmp2):
        if ecmp > single and crossover_x is None:
            crossover_x = x
    
    if crossover_x:
        ax.axvline(crossover_x, color='gray', linestyle=':', alpha=0.5)
        ax.text(crossover_x, max(y_single)*0.9, "  Point of\n  Diminishing\n  Returns", 
                fontsize=8, color='#333')

    # --- Formatting ---
    ax.set_xlabel("Latency Inflation of 2nd Best Path\n(1.0 = Equal, 2.0 = 2nd Path is 2x Slower)")
    ax.set_ylabel("Effective Performance Penalty (%)\n(Includes Latency + Congestion Delays)")
    ax.set_title("Real-World Transfer Penalty: Congestion vs. Path Inflation")
    
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='best', framealpha=0.95)
    
    # Ticks
    ax.set_xticks(sorted_factors[::2] if len(sorted_factors) > 15 else sorted_factors)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"\nPlot saved to: {output_file}")
    plt.show()

if __name__ == "__main__":
    RESULTS_FOLDER = "results/worst_case/with_prefer_peering/results"
    
    print("Calculating Congestion-Aware Drawbacks...")
    processed_data = calculate_congestion_aware_drawback(RESULTS_FOLDER)
    plot_congestion_aware_drawback(processed_data)