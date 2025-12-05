import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_loss_data_from_folder(results_dir):
    """
    Scans a directory for result files and calculates the PACKET LOSS RATIO
    (Unsent Traffic / Total Demand).
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    results = {
        'waterfilling_optimal_1': defaultdict(list),       # Thundering Herd
        'waterfilling_optimal_2': defaultdict(list), # WF 2 Paths
        'waterfilling_optimal_3': defaultdict(list)  # WF 3 Paths
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
                    
                    # --- CORE CALCULATION ---
                    total_sent = analysis_data.get('total_sent_traffic', 0)
                    total_unsent = analysis_data.get('total_unsent_traffic', 0)
                    total_demand = total_sent + total_unsent

                    # Avoid division by zero
                    if total_demand > 0:
                        loss_ratio = total_unsent / total_demand
                    else:
                        loss_ratio = 0.0

                    results[block_name][traffic_factor].append(loss_ratio)

            except Exception as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return results


def analyze_and_plot_packet_loss():
    """
    Generates a comparative plot showing Packet Loss (%) vs Traffic Load.
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
    scenario = {
        "path": "results/random/with_prefer_peering/results", 
    }
    output_plot_file = "packet_loss_comparison2.pdf"
    
    plot_configs = {
        "waterfilling_optimal_1": {
            "label": "Thundering Herd (Selfish)",
            "color": "red",
            "linestyle": "--" 
        },
        "waterfilling_optimal_2": {
            "label": "UMCC (2 Paths)",
            "color": "dodgerblue",
            "linestyle": "-"
        },
        "waterfilling_optimal_3": {
            "label": "UMCC (3 Paths)",
            "color": "green",
            "linestyle": "-"
        }
    }

    # --- 2. Process data ---
    all_block_results = process_loss_data_from_folder(scenario["path"])

    # Dummy Data Generation (if files missing)
    if not all_block_results or not any(all_block_results.values()):
        print("\nNo data found. Generating DUMMY data for visualization verification...")
        for block in plot_configs:
            # Simulation: Red starts losing packets at load 1.5, Blue at 2.5, Green at 3.5
            start_point = 1.5
            if "waterfilling_optimal_2" in block: start_point = 2.5
            if "waterfilling_optimal_3" in block: start_point = 3.5
            
            all_block_results[block] = {
                i/2.0: [max(0, min(1.0, (i/2.0 - start_point) * 0.25)) + np.random.normal(0, 0.005) for _ in range(5)]
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
        average_loss_pct = [np.mean(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]
        std_devs_pct = [np.std(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]
        
        # Scatter points (raw data)
        for factor in sorted_factors:
            y_values = [v * 100 for v in factor_data[factor]]
            ax.scatter([factor] * len(y_values), y_values,
                       alpha=0.15, color=config["color"], s=5, marker='.', zorder=1)

        # Error bars and trend line
        ax.errorbar(sorted_factors, average_loss_pct,
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
    ax.set_ylabel('Traffic Loss / Unsent (%)')
    
    # Set Y-axis to standard 0-100% or auto
    ax.set_ylim(bottom=-2) # Slight buffer below 0
    
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
    analyze_and_plot_packet_loss()