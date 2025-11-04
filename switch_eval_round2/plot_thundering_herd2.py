import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_data_from_folder(results_dir):
    """
    Scans a directory for result files and extracts the total sent traffic for
    both optimal and pessimal cases.

    Args:
        results_dir (str): The path to the directory containing result JSON files.

    Returns:
        defaultdict: A dictionary mapping each factor to a dictionary containing
                     lists of 'optimal' and 'pessimal' total sent traffic values.
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    traffic_data_by_factor = defaultdict(lambda: {'optimal': [], 'pessimal': []})
    filename_pattern = re.compile(r"result_factor_(\d+)_run_(\d+)\.json")

    print(f"--> Processing folder: {results_dir}")
    for filename in os.listdir(results_dir):
        match = filename_pattern.match(filename)
        if match:
            cost_factor = int(match.group(1))
            file_path = os.path.join(results_dir, filename)

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                optimal_traffic = data['thundering_herd']['total_sent_traffic']
                pessimal_traffic = data['thundering_herd']['total_unsent_traffic']

                traffic_data_by_factor[cost_factor]['optimal'].append(optimal_traffic)
                traffic_data_by_factor[cost_factor]['pessimal'].append(pessimal_traffic)

            except (KeyError, json.JSONDecodeError) as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return traffic_data_by_factor

def analyze_and_plot_final_comparison():
    """
    Analyzes results from multiple scenario folders and generates a plot showing
    the congestion percentage, including average, min, and max values.
    """
    # --- 1. Configuration ---
    scenarios = {
        "Switch Traffic Data": {
            "path": "thundering_herd/results",
            "color": "red"
        },
    }
    output_plot_file = "congestion_plot.png"

    # --- 2. Process data for each scenario ---
    all_scenario_results = {}
    for scenario_name, config in scenarios.items():
        factor_data = process_data_from_folder(config["path"])
        if factor_data:
            all_scenario_results[scenario_name] = factor_data

    if not all_scenario_results:
        print("\nNo data found across any specified directories. Cannot generate a plot.")
        return

    print("\nAll folders processed. Generating plot...")

    # --- 3. Plotting the results ---
    fig, ax = plt.subplots(figsize=(14, 9))
    all_scenario_factors = set()

    # Plot data for each scenario
    for scenario_name, factor_data in all_scenario_results.items():
        config = scenarios[scenario_name]
        color = config["color"]

        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)

        avg_congestion_list = []
        min_congestion_list = []
        max_congestion_list = []

        # Calculate congestion for each factor
        for factor in sorted_factors:
            optimal_points = factor_data[factor]['optimal']
            pessimal_points = factor_data[factor]['pessimal']
            
            # Calculate congestion percentage for each individual run
            with np.errstate(divide='ignore', invalid='ignore'):
                congestion_points = [
                    (p / (o + p)) * 100 if (o + p) > 0 else 0
                    for o, p in zip(optimal_points, pessimal_points)
                ]

            if congestion_points:
                avg_congestion_list.append(np.mean(congestion_points))
                min_congestion_list.append(np.min(congestion_points))
                max_congestion_list.append(np.max(congestion_points))
                
                # Plot all individual data points
                ax.scatter([factor] * len(congestion_points), congestion_points,
                           alpha=0.15, color=color, s=40, marker='x', label='_nolegend_')
            else:
                # Handle cases where there's no data for a factor
                avg_congestion_list.append(0)
                min_congestion_list.append(0)
                max_congestion_list.append(0)

        # Plot the average, min, and max trend lines
        # Solid line for AVERAGE congestion
        ax.plot(sorted_factors, avg_congestion_list,
                marker='o',
                linestyle='solid',
                color=color,
                linewidth=2.5,
                label=f"{scenario_name} - Average Congestion")
        
        # Dashed line for MIN congestion
        ax.plot(sorted_factors, min_congestion_list,
                marker='_',
                linestyle='dashed',
                color=color,
                linewidth=1.5,
                alpha=0.8,
                label=f"{scenario_name} - Min & Max Congestion")

        # Dashed line for MAX congestion (without adding a new legend entry)
        ax.plot(sorted_factors, max_congestion_list,
                marker='_',
                linestyle='dashed',
                color=color,
                linewidth=1.5,
                alpha=0.8,
                label='_nolegend_')

    # --- 4. Formatting the plot ---
    ax.set_title('Congestion Percentage by Traffic Increase Factor', fontsize=18)
    ax.set_xlabel('Traffic Increase Factor', fontsize=14)
    ax.set_ylabel('Congestion in Percent (%)', fontsize=14)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.set_ylim(0, 100) # Percentage is bounded by 0 and 100

    ax.legend(fontsize=12)

    if all_scenario_factors:
        ax.set_xticks(sorted(list(all_scenario_factors)))
        plt.xticks(rotation=45)

    # --- 5. Save and show the plot ---
    plt.tight_layout()
    plt.savefig(output_plot_file)
    print(f"\nPlot successfully saved to '{output_plot_file}'")
    plt.show()

if __name__ == "__main__":
    # Ensure you have matplotlib and numpy installed:
    # pip install matplotlib numpy
    analyze_and_plot_final_comparison()