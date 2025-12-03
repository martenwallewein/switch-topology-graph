import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_folder(folder_path):
    """
    Calculates the relative performance impact of ECMP2 vs Single Path
    for a specific results folder.
    
    Returns:
        dict: mapping {inflation_factor: mean_relative_impact}
    """
    if not os.path.isdir(folder_path):
        print(f"Warning: Directory '{folder_path}' not found. Skipping.")
        return {}

    results = defaultdict(list)
    filename_pattern = re.compile(r"result_inflation_(\d+(?:\.\d+)?)_run_(\d+)\.json")
    
    BASE_LATENCY = 10.0
    
    print(f"--> Processing: {folder_path}")
    
    files = [f for f in os.listdir(folder_path) if filename_pattern.match(f)]
    if not files:
        print(f"    No matching files found in {folder_path}")
        return {}

    for filename in files:
        match = filename_pattern.match(filename)
        inflation_factor = float(match.group(1))
        
        # --- MODIFICATION START ---
        # Filter: Only consider data from 1.0 to 2.0 inclusive.
        if inflation_factor < 1.0 or inflation_factor > 2.0:
            continue
        # --- MODIFICATION END ---

        file_path = os.path.join(folder_path, filename)

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # 1. Get Utilization Map from the 3-path analysis block 
            # (Using this block ensures we see all potential paths)
            if 'fair_share_latency_optimal_3' not in data:
                continue

            perf = data['fair_share_latency_optimal_3'].get('performance_analysis', {})
            egress_utils = perf.get('egress_utilization', {})
            
            # Map Link ID -> Utilization %
            util_map = {k: v.get('utilization_percent', 0.0) for k, v in egress_utils.items()}

            # 2. Analyze Destinations
            congestion_analysis = data['fair_share_latency_optimal_3'].get('congestion_analysis', {})
            
            run_impacts = []

            for dest, info in congestion_analysis.items():
                paths = info.get('lowest_latency_paths', [])
                num_paths = len(paths)
                
                if num_paths == 0: 
                    continue

                # --- Path 1 (Best) ---
                link_1 = paths[0]
                # Effective Latency = Base * Max(1, Utilization)
                eff_lat_1 = BASE_LATENCY * max(1.0, util_map.get(link_1, 0.0) / 100.0)

                # --- Path 2 (2nd Best) ---
                eff_lat_2 = None
                if num_paths >= 2:
                    link_2 = paths[1]
                    raw_lat_2 = BASE_LATENCY * inflation_factor
                    eff_lat_2 = raw_lat_2 * max(1.0, util_map.get(link_2, 0.0) / 100.0)

                # --- Calculate Strategy Scores ---
                
                # Strategy A: Single Path (Baseline)
                score_single = eff_lat_1

                # Strategy B: ECMP 2
                if eff_lat_2 is not None:
                    # Avg effective latency of splitting traffic
                    score_ecmp2 = (eff_lat_1 + eff_lat_2) / 2.0
                else:
                    # Fallback to single path behavior if only 1 path exists
                    score_ecmp2 = score_single

                # --- Calculate Relative Difference ---
                # (ECMP - Single) / Single
                # Negative = ECMP is Faster (Benefit)
                # Positive = ECMP is Slower (Penalty)
                if score_single > 0:
                    diff = (score_ecmp2 - score_single) / score_single
                else:
                    diff = 0.0
                
                run_impacts.append(diff)

            if run_impacts:
                # Average impact across all destinations for this run
                results[inflation_factor].append(np.mean(run_impacts))

        except Exception as e:
            print(f"    Error reading {filename}: {e}")
            
    # Aggregate runs: {inflation: mean_of_runs}
    final_data = {k: np.mean(v) for k, v in results.items()}
    return final_data

def plot_comparative_impact(scenarios):
    """
    Plots the Relative Performance Impact for multiple traffic scenarios.
    """
    output_file = "comparative_ecmp2_impact.pdf"
    
    # Style
    plt.rcParams.update({
        'font.family': 'serif', 'font.size': 10,
        'axes.labelsize': 11, 'axes.titlesize': 12,
        'legend.fontsize': 9, 'lines.linewidth': 2,
        'xtick.labelsize': 10, 'ytick.labelsize': 10
    })

    fig, ax = plt.subplots(figsize=(7, 5))
    
    # Define colors/markers for the 3 scenarios
    styles = [
        {"color": "#1f3f85", "marker": "o", "label": "Traffic Factor 5 (Very Low)"},   # Blue
        {"color": "#2ca02c", "marker": "o", "label": "Traffic Factor 10 (Low)"},       # Green
        {"color": "#ff7f0e", "marker": "^", "label": "Traffic Factor 15 (Medium)"},    # Orange
        {"color": "#d62728", "marker": "s", "label": "Traffic Factor 20 (High)"}       # Red
    ]

    # Plot Zero Line (Baseline)
    ax.axhline(0, color='black', linewidth=1.2, linestyle='-', label="Single Best Path (Baseline)")


    # Plot each scenario
    for idx, (name, data) in enumerate(scenarios.items()):
        if not data:
            continue
            
        sorted_factors = sorted(data.keys())
        # Convert fractional difference to Percentage
        y_values = [data[x] * 100 for x in sorted_factors]
        
        style = styles[idx % len(styles)]
        
        ax.plot(sorted_factors, y_values, 
                label=name,
                color=style["color"], 
                marker=style["marker"], 
                markersize=5,
                alpha=0.9)
        
    

    # --- Formatting ---
    ax.set_xlabel("Latency Inflation of 2nd Best Path")
    ax.set_ylabel("Relative Performance Impact (%)")
    ax.set_title("ECMP-2 Performance vs. Single Path (Range 1.0-2.0)")
    
    # Annotations for zones
    #ax.text(1.05, -5, "Benefit Zone\n(Congestion Relief)", fontsize=8, color='green', va='top')
    #ax.text(1.05, 5, "Penalty Zone\n(Latency Overhead)", fontsize=8, color='red', va='bottom')

    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='upper left', framealpha=0.95)
    
    # Ticks
    all_keys = set()
    for d in scenarios.values(): all_keys.update(d.keys())
    if all_keys:
        sorted_keys = sorted(list(all_keys))
        ax.set_xticks(sorted_keys[::2] if len(sorted_keys) > 15 else sorted_keys)

    plt.tight_layout()
    try:
        plt.savefig(output_file, dpi=300)
        print(f"\nSuccess! Plot saved to: {output_file}")
    except Exception as e:
        print(f"Error saving plot: {e}")
    plt.show()

if __name__ == "__main__":
    # Define your configuration here
    SCENARIO_CONFIG = {
        "Traffic Factor 5": "results/worst_case_5/no_prefer_peering/results",
        #"Traffic Factor 10": "results/worst_case_10/no_prefer_peering/results",
        #"Traffic Factor 15": "results/worst_case_15/no_prefer_peering/results", 
        #"Traffic Factor 20": "results/worst_case_20/no_prefer_peering/results"
    }
    
    all_scenario_data = {}
    
    print("Starting Comparative Analysis (Filtering 1.0 to 2.0)...")
    for label, path in SCENARIO_CONFIG.items():
        data = process_folder(path)
        if data:
            all_scenario_data[label] = data
            
    plot_comparative_impact(all_scenario_data)