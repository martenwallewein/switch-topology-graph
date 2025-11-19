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

    Args:
        results_dir (str): The path to the directory containing result JSON files.

    Returns:
        defaultdict: A dictionary mapping each traffic factor to a list of
                     calculated spillover traffic ratios.
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    spillover_ratios_by_factor = defaultdict(list)
    
    # --- CORRECTED REGEX ---
    # This regex now correctly handles both integer and float numbers (e.g., 1.5)
    # for the traffic factor and resolves the "unterminated subpattern" error.
    filename_pattern = re.compile(r"result_factor_(\d+(?:\.\d+)?)_run_(\d+)\.json")

    print(f"--> Processing folder: {results_dir}")
    for filename in os.listdir(results_dir):
        match = filename_pattern.match(filename)
        if match:
            # The factor is the traffic multiplier (group 1 in the regex)
            traffic_factor = float(match.group(1))
            file_path = os.path.join(results_dir, filename)

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                if 'latency_optimal' not in data:
                    print(f"    - Warning: 'latency_optimal' key not found in '{filename}'. Skipping.")
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
                    # Calculate the ratio of spillover to total traffic
                    spillover_ratio = total_spillover / total_sent_traffic
                    spillover_ratios_by_factor[traffic_factor].append(spillover_ratio)
                else:
                    # If there's no sent traffic, the ratio is 0.
                    spillover_ratios_by_factor[traffic_factor].append(0.0)

            except Exception as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return spillover_ratios_by_factor


def analyze_and_plot_congestion():
    """
    Analyzes results from multiple scenario folders and generates a comparative plot
    showing the spillover traffic ratio against the traffic increase factor.
    """
    # --- 1. Configuration: Define the scenarios to compare ---
    # IMPORTANT: Update the 'path' for each scenario to point to your results folders.
    scenarios = {
        #"Thundering Herd": {
        #    "path": "results/balanced/no_prefer_peering/results",
        #    "color": "blue",
        #    "linestyle": "solid"
        #},
        "Thundering Herd Worst Case": {
            "path": "results/worst_case/no_prefer_peering/results",
            "color": "red",
            "linestyle": "solid"
        }
    }
    output_plot_file = "congestion_spillover_comparison.pdf"

    # --- 2. Process data for each scenario ---
    all_factor_results = {}
    for scenario_name, config in scenarios.items():
        factor_data = process_traffic_data_from_folder(config["path"])
        if factor_data:
            all_factor_results[scenario_name] = factor_data

    if not all_factor_results:
        print("\nNo data found across any specified directories. Cannot generate a plot.")
        return

    print("\nAll folders processed. Generating comparative plot...")

    # --- 3. Plotting the results ---
    fig, ax = plt.subplots(figsize=(14, 9))
    all_scenario_factors = set()

    # Plot data for each scenario
    for scenario_name, factor_data in all_factor_results.items():
        config = scenarios[scenario_name]
        color = config["color"]
        linestyle = config["linestyle"]
        
        sorted_traffic_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_traffic_factors)

        average_ratios = [np.mean(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_traffic_factors]
        std_devs = [np.std(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_traffic_factors]

        # Plot all individual data points
        #for factor in sorted_traffic_factors:
        #    ax.scatter([factor] * len(factor_data[factor]), factor_data[factor],
        #               alpha=0.2, color=color, s=40, label='_nolegend_')
        
        # Plot the average trend line with error bars
        ax.errorbar(sorted_traffic_factors, average_ratios,
                    yerr=std_devs,
                    marker='o',
                    linestyle=linestyle,
                    color=color,
                    linewidth=2.5,
                    label=scenario_name,
                    capsize=5,
                    capthick=2)

    # --- 4. Formatting the plot ---
    ax.set_title('Congestion vs. Traffic Increase', fontsize=18)
    ax.set_xlabel('Traffic Factor Multiplier', fontsize=14)
    ax.set_ylabel("Congestion in % of overall traffic", fontsize=14)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # ax.axhline(y=0.0, color='gray', linestyle=':', linewidth=1.5, label='Baseline (No Congestion)')
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
    
    # Ensure your result filenames are in the format:
    # result_factor_[TRAFFIC_FACTOR]_run_[RUN_NUMBER].json
    # e.g., result_factor_1.5_run_0.json
    
    analyze_and_plot_congestion()