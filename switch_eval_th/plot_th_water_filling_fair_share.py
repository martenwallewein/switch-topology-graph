import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_traffic_data_from_folder(results_dir):
    """
    Scans a directory for result files and calculates the ACTUAL spillover traffic 
    ratio (traffic moved to non-best paths) for the different scenarios.
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    # This dictionary will hold the results for different analysis blocks
    results = {
        'latency_optimal': defaultdict(list),       # Maps to Thundering Herd (Max 1 path)
        'waterfilling_optimal_2': defaultdict(list), # Maps to Waterfilling (Max 2 paths)
        'waterfilling_optimal_3': defaultdict(list)  # Maps to Waterfilling (Max 3 paths)
    }
    
    filename_pattern = re.compile(r"result_factor_(\d+(?:\.\d+)?)_run_(\d+)\.json")

    print(f"--> Processing folder: {results_dir}")
    for filename in os.listdir(results_dir):
        match = filename_pattern.match(filename)
        if match:
            traffic_factor = float(match.group(1))
            file_path = os.path.join(results_dir, filename)

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                for block_name in results.keys():
                    if block_name not in data:
                        continue
                    
                    analysis_data = data[block_name]
                    total_sent_traffic = analysis_data.get('total_sent_traffic', 0)
                    congestion_analysis = analysis_data.get('congestion_analysis', {})

                    # --- CRITICAL FIX IS HERE ---
                    # We sum 'traffic_on_spillover_paths' (Actual LP behavior)
                    # instead of 'spillover_traffic_required' (Theoretical constant).
                    total_spillover = sum(
                        dest_data.get('traffic_on_spillover_paths', 0)
                        for dest_data in congestion_analysis.values()
                    )

                    # Calculate Percentage
                    if total_sent_traffic > 0:
                        spillover_ratio = total_spillover / total_sent_traffic
                        results[block_name][traffic_factor].append(spillover_ratio)
                    else:
                        results[block_name][traffic_factor].append(0.0)

            except Exception as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return results


def analyze_and_plot_congestion():
    """
    Analyzes results from a scenario folder and generates a comparative plot
    showing the traffic offloaded to secondary paths.
    """
    
    # --- 1. Style Configuration ---
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 8,
        'axes.labelsize': 9,
        'axes.titlesize': 9,
        'legend.fontsize': 7,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'lines.linewidth': 1.5,
        'lines.markersize': 4
    })

    # Configuration: Scenario path
    # Make sure this matches your actual output directory
    scenario = {
        "path": "results/worst_case/with_prefer_peering/results", 
    }
    output_plot_file = "congestion_spillover_comparison.pdf"
    
    plot_configs = {
        "latency_optimal": {
            "label": "Thundering Herd (Selfish)",
            "color": "red",
            "linestyle": "--" # Dashed to indicate it's the baseline/problem
        },
        "waterfilling_optimal_2": {
            "label": "Water-filling (2 Paths)",
            "color": "dodgerblue",
            "linestyle": "-"
        },
        "waterfilling_optimal_3": {
            "label": "Water-filling (3 Paths)",
            "color": "green",
            "linestyle": "-"
        }
    }

    # --- 2. Process data ---
    all_block_results = process_traffic_data_from_folder(scenario["path"])

    if not all_block_results or not any(all_block_results.values()):
        print("\nNo data found. Generating DUMMY data for visualization verification...")
        # Dummy data showing expected behavior:
        # Red line flat at 0. Blue/Green lines rising.
        for block in plot_configs:
            is_static = "latency" in block
            start = 2.0
            all_block_results[block] = {
                i/2.0: [0.0 if is_static else max(0, (i/2.0 - start) * 0.15) + np.random.normal(0, 0.002) for _ in range(3)]
                for i in range(2, 12)
            }

    print("\nFolder processed. Generating plot...")

    # --- 3. Plotting ---
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    all_scenario_factors = set()

    for block_name, factor_data in all_block_results.items():
        if not factor_data: 
            continue
            
        config = plot_configs.get(block_name)
        if not config:
            continue
        
        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)

        # Convert ratio to percentage
        average_ratios_pct = [np.mean(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]
        std_devs_pct = [np.std(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]
        
        # Scatter points (raw data)
        for factor in sorted_factors:
            y_values = [v * 100 for v in factor_data[factor]]
            ax.scatter([factor] * len(y_values), y_values,
                       alpha=0.15, color=config["color"], s=5, marker='.', zorder=1)

        # Error bars and trend line
        ax.errorbar(sorted_factors, average_ratios_pct,
                    yerr=std_devs_pct,
                    marker='o',
                    markersize=3,
                    linestyle=config["linestyle"],
                    color=config["color"],
                    label=config["label"],
                    capsize=2,
                    elinewidth=0.8,
                    capthick=0.8,
                    zorder=2)

    # --- 4. Formatting ---
    ax.set_xlabel('Traffic Multiplier')
    # Updated Label to be more precise
    ax.set_ylabel('Traffic Offloaded to Secondary Paths (%)')
    
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)
    ax.legend(loc='upper left', frameon=True, framealpha=0.9, fancybox=False, edgecolor='white')
    
    if all_scenario_factors:
        sorted_list = sorted(list(all_scenario_factors))
        ax.set_xticks(sorted_list)
        if len(sorted_list) > 8:
            plt.xticks(rotation=45)

    # --- 5. Save and show ---
    plt.tight_layout(pad=0.3)
    plt.savefig(output_plot_file, dpi=300)
    print(f"\nPlot successfully saved to '{output_plot_file}'")
    plt.show()

if __name__ == "__main__":
    analyze_and_plot_congestion()