import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_traffic_data_from_folder(results_dir):
    """
    Scans a directory for result files and calculates the spillover traffic ratio
    for both 'latency_optimal' and 'fair_share_latency_optimal' blocks.

    Args:
        results_dir (str): The path to the directory containing result JSON files.

    Returns:
        dict: A dictionary containing the spillover ratios for each analysis block.
              e.g., {'latency_optimal': defaultdict, 'fair_share_latency_optimal': defaultdict}
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    # This dictionary will hold the results for different analysis blocks
    results = {
        'latency_optimal': defaultdict(list),
        'fair_share_latency_optimal': defaultdict(list),
        'fair_share_latency_optimal_3': defaultdict(list)
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

                # --- MODIFIED: Process multiple blocks from the same file ---
                for block_name in results.keys():
                    if block_name not in data:
                        print(f"    - Info: '{block_name}' key not found in '{filename}'. Skipping this block.")
                        continue
                    
                    analysis_data = data[block_name]
                    total_sent_traffic = analysis_data.get('total_sent_traffic', 0)
                    congestion_analysis = analysis_data.get('congestion_analysis', {})

                    total_spillover = sum(
                        dest_data.get('spillover_traffic_required', 0)
                        for dest_data in congestion_analysis.values()
                    )

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
    showing the spillover ratio for different analysis methods.
    """
    # --- 1. Configuration: Define the scenario path ---
    # This now points to a single directory containing the result files.
    scenario = {
        "path": "results/worst_case/with_prefer_peering/results",
    }
    output_plot_file = "congestion_spillover_comparison.pdf"
    
    # --- NEW: Define plot styles for each analysis block ---
    plot_configs = {
        "latency_optimal": {
            "label": "Thundering Herd",
            "color": "red",
            "linestyle": "solid"
        },
        "fair_share_latency_optimal": {
            "label": "ECMP 2 Paths",
            "color": "dodgerblue",
            "linestyle": "solid"
        },
        "fair_share_latency_optimal_3": {
            "label": "ECMP 3 Paths",
            "color": "green",
            "linestyle": "solid"
        }
    }

    # --- 2. Process data for the scenario ---
    # This now returns a dictionary with results for both blocks
    all_block_results = process_traffic_data_from_folder(scenario["path"])

    if not all_block_results:
        print("\nNo data found in the specified directory. Cannot generate a plot.")
        return

    print("\nFolder processed. Generating comparative plot...")

    # --- 3. Plotting the results ---
    fig, ax = plt.subplots(figsize=(14, 9))
    all_scenario_factors = set()

    # --- MODIFIED: Loop through the analysis blocks found in the files ---
    for block_name, factor_data in all_block_results.items():
        if not factor_data: # Skip if no data was found for this block
            continue
            
        config = plot_configs.get(block_name)
        if not config: # Skip if no plot configuration is defined
            print(f"Warning: No plot configuration for '{block_name}'. Skipping.")
            continue
        
        color = config["color"]
        linestyle = config["linestyle"]
        label = config["label"]
        
        sorted_traffic_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_traffic_factors)

        # Convert ratio to percentage for plotting
        average_ratios_pct = [np.mean(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_traffic_factors]
        std_devs_pct = [np.std(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_traffic_factors]
        
        # Plot the average trend line with error bars
        ax.errorbar(sorted_traffic_factors, average_ratios_pct,
                    yerr=std_devs_pct,
                    marker='o',
                    linestyle=linestyle,
                    color=color,
                    linewidth=2.5,
                    label=label, # Use the label from plot_configs
                    capsize=5,
                    capthick=2)

    # --- 4. Formatting the plot ---
    ax.set_title('Congestion Comparison: Latency Optimal vs. Fair Share', fontsize=18)
    ax.set_xlabel('Traffic Factor Multiplier', fontsize=14)
    ax.set_ylabel("Congestion (% of Overall Traffic)", fontsize=14)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
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
    
    analyze_and_plot_congestion()