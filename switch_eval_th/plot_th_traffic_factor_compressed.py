import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_traffic_data_from_folder(results_dir):
    """
    Scans a directory for result files and calculates the ratio of
    spillover traffic to total sent traffic.
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    spillover_ratios_by_factor = defaultdict(list)
    
    # Regex handles integer and float numbers (e.g., 1.5)
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

                # Logic specific to the congestion/latency analysis
                if 'latency_optimal' not in data:
                    continue
                
                analysis_data = data['latency_optimal']
                total_sent_traffic = analysis_data.get('total_sent_traffic', 0)
                congestion_analysis = analysis_data.get('congestion_analysis', {})

                # Calculate the total spillover traffic
                total_spillover = sum(
                    dest_data.get('spillover_traffic_required', 0)
                    for dest_data in congestion_analysis.values()
                )

                if total_sent_traffic > 0:
                    spillover_ratio = total_spillover / total_sent_traffic
                    spillover_ratios_by_factor[traffic_factor].append(spillover_ratio)
                else:
                    spillover_ratios_by_factor[traffic_factor].append(0.0)

            except Exception as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return spillover_ratios_by_factor


def analyze_and_plot_congestion():
    """
    Analyzes results from multiple scenario folders and generates a comparative plot
    showing the spillover traffic ratio against the traffic increase factor.
    """
    
    # --- 1. Style Configuration for LaTeX/Academic Paper ---
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

    # Shortened names for legend to fit column width
    scenarios = {
        "Thundering Herd (Path Unlocking)": {
            "path": "results/worst_case/no_prefer_peering/results",
            "color": "blue",     # Requested Color
            "linestyle": "-",
            "label": "Path Unlocking"
        },
        "Thundering Herd (Prefer Peering)": {
            "path": "results/worst_case/with_prefer_peering/results",
            "color": "red",      # Requested Color
            "linestyle": "--",   # Dashed for contrast
            "label": "Prefer Peering"
        }
    }
    output_plot_file = "congestion_spillover_comparison_compressed.pdf"

    # --- 2. Process data for each scenario ---
    all_factor_results = {}
    for scenario_name, config in scenarios.items():
        factor_data = process_traffic_data_from_folder(config["path"])
        if factor_data:
            all_factor_results[scenario_name] = factor_data

    if not all_factor_results:
        print("\nNo data found. Generating dummy data for visual verification...")
        # Optional: Generate dummy data if folders don't exist
        for name in scenarios:
            # Simulate congestion starting around factor 2.0
            all_factor_results[name] = {
                i/2.0: [max(0, (i/2.0 - 1.5) * 0.1) + np.random.normal(0, 0.01) for _ in range(5)]
                for i in range(2, 10)
            }

    print("\nGenerating condensed congestion plot...")

    # --- 3. Plotting the results ---
    # Standard single-column size
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    all_scenario_factors = set()

    for scenario_name, factor_data in all_factor_results.items():
        config = scenarios[scenario_name]
        color = config["color"]
        linestyle = config["linestyle"]
        label = config["label"]
        
        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)

        # Convert ratio to percentage
        average_ratios = [np.mean(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]
        std_devs = [np.std(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]

        # Scatter points (background, faint)
        for factor in sorted_factors:
            y_values = [v * 100 for v in factor_data[factor]]
            ax.scatter([factor] * len(y_values), y_values,
                       alpha=0.15, color=color, s=10, marker='.', linewidths=0, zorder=1)
        
        # Error bars and trend line
        ax.errorbar(sorted_factors, average_ratios,
                    yerr=std_devs,
                    marker='o',
                    markersize=3,
                    linestyle=linestyle,
                    color=color,
                    label=label,
                    capsize=2,       # Small caps for small figure
                    elinewidth=0.8,
                    capthick=0.8,
                    zorder=2)

    # --- 4. Formatting the plot ---
    # Concise Labels
    ax.set_xlabel('Traffic Multiplier')
    ax.set_ylabel('Congestion (% of Total Traffic)')
    
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)
    
    # Ensure X-axis has reasonable ticks
    if all_scenario_factors:
        sorted_list = sorted(list(all_scenario_factors))
        # If too many factors, just pick a few or let matplotlib decide, 
        # but here we ensure the data points are represented.
        ax.set_xticks(sorted_list)
        # If the labels crowd, rotate them slightly
        if len(sorted_list) > 8:
             plt.xticks(rotation=45)

    # Legend
    ax.legend(loc='best', frameon=True, framealpha=0.9, fancybox=False, edgecolor='white')

    # --- 5. Save and show ---
    plt.tight_layout(pad=0.3)
    plt.savefig(output_plot_file, dpi=300)
    print(f"\nPlot successfully saved to '{output_plot_file}'")
    plt.show()

if __name__ == "__main__":
    analyze_and_plot_congestion()