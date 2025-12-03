import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def calculate_relative_drawback(results_dir):
    """
    Calculates the performance difference of ECMP strategies RELATIVE to 
    the Single Best Path strategy.
    
    Positive Value = ECMP is SLOWER (Drawback)
    Negative Value = ECMP is FASTER (Benefit)
    Zero = Same Performance
    """
    if not os.path.isdir(results_dir):
        print(f"Error: Directory '{results_dir}' not found.")
        return None

    results = defaultdict(lambda: defaultdict(list))
    filename_pattern = re.compile(r"result_inflation_(\d+(?:\.\d+)?)_run_(\d+)\.json")
    
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

                # 1. Get Utilization Map
                util_map = {}
                if 'fair_share_latency_optimal_3' in data:
                    perf = data['fair_share_latency_optimal_3'].get('performance_analysis', {})
                    egress_utils = perf.get('egress_utilization', {})
                    for link_id, metrics in egress_utils.items():
                        util_map[link_id] = metrics.get('utilization_percent', 0.0)
                else:
                    continue

                # 2. Analyze Destinations
                congestion_analysis = data['fair_share_latency_optimal_3'].get('congestion_analysis', {})

                for dest, info in congestion_analysis.items():
                    paths = info.get('lowest_latency_paths', [])
                    num_paths = len(paths)
                    if num_paths == 0: continue

                    # --- 1. Calculate Effective Latencies (Latency * Congestion) ---
                    
                    # Path 1 (Best)
                    link_1 = paths[0]
                    eff_lat_1 = BASE_LATENCY * max(1.0, util_map.get(link_1, 0.0) / 100.0)

                    # Path 2
                    eff_lat_2 = None
                    if num_paths >= 2:
                        link_2 = paths[1]
                        raw_lat_2 = BASE_LATENCY * inflation_factor
                        eff_lat_2 = raw_lat_2 * max(1.0, util_map.get(link_2, 0.0) / 100.0)

                    # Path 3
                    eff_lat_3 = None
                    if num_paths >= 3:
                        link_3 = paths[2]
                        raw_lat_3 = (BASE_LATENCY * inflation_factor) + STEP_LATENCY
                        eff_lat_3 = raw_lat_3 * max(1.0, util_map.get(link_3, 0.0) / 100.0)

                    # --- 2. Calculate Strategy Scores ---
                    
                    # Strategy A: Single Path (The Baseline)
                    # The score is simply the Effective Latency of Path 1
                    score_single = eff_lat_1

                    # Strategy B: ECMP 2
                    if eff_lat_2 is not None:
                        score_ecmp2 = (eff_lat_1 + eff_lat_2) / 2.0
                    else:
                        score_ecmp2 = score_single

                    # Strategy C: ECMP 3
                    if eff_lat_3 is not None:
                        score_ecmp3 = (eff_lat_1 + eff_lat_2 + eff_lat_3) / 3.0
                    elif eff_lat_2 is not None:
                        score_ecmp3 = score_ecmp2
                    else:
                        score_ecmp3 = score_single

                    # --- 3. Calculate Relative Difference (%) ---
                    # Formula: (ECMP_Score - Single_Score) / Single_Score
                    
                    diff_ecmp2 = (score_ecmp2 - score_single) / score_single
                    diff_ecmp3 = (score_ecmp3 - score_single) / score_single

                    results[inflation_factor]['ecmp2'].append(diff_ecmp2)
                    results[inflation_factor]['ecmp3'].append(diff_ecmp3)

            except Exception as e:
                print(f"    Error processing {filename}: {e}")

    return results

def plot_relative_drawback(data):
    if not data: return

    output_file = "relative_performance_impact.pdf"
    
    # Style configuration
    plt.rcParams.update({
        'font.family': 'serif', 'font.size': 10,
        'axes.labelsize': 11, 'axes.titlesize': 12,
        'legend.fontsize': 9, 'lines.linewidth': 2
    })

    fig, ax = plt.subplots(figsize=(7, 5))
    sorted_factors = sorted(data.keys())
    
    # Calculate Means
    y_ecmp2 = [np.mean(data[x]['ecmp2']) * 100 for x in sorted_factors]
    y_ecmp3 = [np.mean(data[x]['ecmp3']) * 100 for x in sorted_factors]
    
    # --- Plotting ---
    
    # 1. Zero Line (The "Single Path" Baseline)
    ax.axhline(0, color='black', linewidth=1.5, linestyle='-', label="Single Best Path Strategy (Baseline)")
    
    # 2. ECMP 2
    ax.plot(sorted_factors, y_ecmp2, 
            label="ECMP 2 Impact", 
            color="#1f77b4", marker="o", markersize=5) # Blue

    # 3. ECMP 3
    ax.plot(sorted_factors, y_ecmp3, 
            label="ECMP 3 Impact", 
            color="#2ca02c", linestyle="--", marker="^", markersize=5) # Green

    # --- Coloring Areas ---
    # Fill area below 0 (Benefit)
    ax.fill_between(sorted_factors, 0, y_ecmp2, where=np.array(y_ecmp2)<0, 
                    color='green', alpha=0.1, interpolate=True)
    ax.text(sorted_factors[1], -5, "ECMP is Faster\n(Congestion Relief)", color='green', fontsize=9, va='top')

    # Fill area above 0 (Drawback)
    ax.fill_between(sorted_factors, 0, y_ecmp2, where=np.array(y_ecmp2)>0, 
                    color='red', alpha=0.1, interpolate=True)
    ax.text(sorted_factors[-4], 10, "ECMP is Slower\n(Latency Penalty)", color='red', fontsize=9, va='bottom')

    # --- Formatting ---
    ax.set_xlabel("Latency Inflation of 2nd Best Path\n(1.0 = Equal, 2.0 = 2nd Path is 2x Slower)")
    ax.set_ylabel("Relative Performance Impact (%)\n(Negative = Faster than Single Path)")
    ax.set_title("Impact of ECMP vs. Single Path (Congestion Aware)")
    
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
    
    print("Calculating Relative Performance Impact...")
    processed_data = calculate_relative_drawback(RESULTS_FOLDER)
    plot_relative_drawback(processed_data)