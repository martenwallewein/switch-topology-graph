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

    # This dictionary will now store lists for both optimal and pessimal traffic
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

                # Extract total_sent_traffic for both optimal and pessimal cases
                optimal_traffic = data['thundering_herd']['total_sent_traffic']
                pessimal_traffic = data['thundering_herd']['total_unsent_traffic']

                traffic_data_by_factor[cost_factor]['optimal'].append(optimal_traffic)
                traffic_data_by_factor[cost_factor]['pessimal'].append(pessimal_traffic)

            except (KeyError, json.JSONDecodeError) as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return traffic_data_by_factor

def analyze_and_plot_final_comparison():
    """
    Analyzes results from multiple scenario folders and generates a comparative plot
    showing the total sent traffic (optimal) and congestion percentage (pessimal).
    """
    # --- 1. Configuration ---
    scenarios = {
        "Switch Traffic Data": {
            "path": "thundering_herd/results",
            "color": "green",
            "congestion_color": "red"
        },
    }
    output_plot_file = "scenario_traffic_comparison.png"

    # --- 2. Process data for each scenario ---
    all_scenario_results = {}
    for scenario_name, config in scenarios.items():
        factor_data = process_data_from_folder(config["path"])
        if factor_data:
            all_scenario_results[scenario_name] = factor_data

    if not all_scenario_results:
        print("\nNo data found across any specified directories. Cannot generate a plot.")
        return

    print("\nAll folders processed. Generating comparative plot...")

    # --- 3. Plotting the results ---
    fig, ax = plt.subplots(figsize=(14, 9))
    ax2 = ax.twinx()  # Create a second y-axis sharing the same x-axis

    all_scenario_factors = set()

    # Plot data for each scenario
    for scenario_name, factor_data in all_scenario_results.items():
        config = scenarios[scenario_name]
        color = config["color"]
        congestion_color = config["congestion_color"]

        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)

        # Calculate average traffic for both optimal and pessimal cases
        avg_optimal_traffic = [np.mean(factor_data[f]['optimal']) if factor_data[f]['optimal'] else 0 for f in sorted_factors]
        avg_pessimal_traffic = [np.mean(factor_data[f]['pessimal']) if factor_data[f]['pessimal'] else 0 for f in sorted_factors]

        # Calculate congestion percentage: pessimal / (optimal + pessimal)
        with np.errstate(divide='ignore', invalid='ignore'):
            avg_congestion_percent = [
                (p / (o + p)) * 100 if (o + p) > 0 else 0
                for o, p in zip(avg_optimal_traffic, avg_pessimal_traffic)
            ]

        # Plot all individual data points
        for factor in sorted_factors:
            # Optimal traffic points on the primary axis
            ax.scatter([factor] * len(factor_data[factor]['optimal']), factor_data[factor]['optimal'],
                       alpha=0.15, color=color, s=40, label='_nolegend_')

            # Congestion percentage points on the secondary axis
            optimal_points = factor_data[factor]['optimal']
            pessimal_points = factor_data[factor]['pessimal']
            congestion_points = [
                (p / (o + p)) * 100 if (o + p) > 0 else 0
                for o, p in zip(optimal_points, pessimal_points)
            ]
            ax2.scatter([factor] * len(congestion_points), congestion_points,
                        alpha=0.15, color=congestion_color, s=40, marker='x', label='_nolegend_')

        # Plot the average trend lines
        # Solid line for OPTIMAL traffic on the primary y-axis
        ax.plot(sorted_factors, avg_optimal_traffic,
                marker='o',
                linestyle='solid',
                color=color,
                linewidth=2.5,
                label=f"{scenario_name} - Sent Traffic (Left Axis)")

        # Dashed line for CONGESTION PERCENTAGE on the secondary y-axis
        ax2.plot(sorted_factors, avg_congestion_percent,
                 marker='x',
                 linestyle='dashed',
                 color=congestion_color,
                 linewidth=2.5,
                 label=f"{scenario_name} - Congestion % (Right Axis)")

    # --- 4. Formatting the plot ---
    ax.set_title('Sent Traffic vs. Congestion Percentage', fontsize=18)
    ax.set_xlabel('Traffic Increase Factor', fontsize=14)

    # Primary Y-axis (Optimal Traffic)
    ax.set_ylabel('Thundering Herd: Total Sent Traffic (gbps)', fontsize=14, color='green')
    ax.tick_params(axis='y', labelcolor='green')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Secondary Y-axis (Congestion Percentage)
    ax2.set_ylabel('Congestion in Percent (%)', fontsize=14, color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    ax2.set_ylim(0, 100) # Percentage is bounded by 0 and 100

    # Unified Legend
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, fontsize=12, loc='upper left')


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