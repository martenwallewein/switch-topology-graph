import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt

def process_factors_from_folder(results_dir):
    """
    Scans a directory for result files and calculates the cost increase factor.
    (No changes needed in this function)
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    increase_factors_by_factor = defaultdict(list)
    filename_pattern = re.compile(r"result_factor_(\d+)_run_(\d+)\.json")

    print(f"--> Processing folder: {results_dir}")
    for filename in sorted(os.listdir(results_dir)):
        match = filename_pattern.match(filename)
        if match:
            cost_factor = int(match.group(1))
            file_path = os.path.join(results_dir, filename)

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                optimal_cost = data['isp_optimal']['total_cost']
                pessimal_cost = data['isp_pessimal']['total_cost']

                if optimal_cost > 0:
                    increase_factor = pessimal_cost / optimal_cost
                    increase_factors_by_factor[cost_factor].append(increase_factor)
                elif pessimal_cost == 0:
                    increase_factors_by_factor[cost_factor].append(1.0)
                else:
                    print(f"    - Warning: Infinite increase factor in '{filename}' (optimal cost is 0). Skipping point.")
            except Exception as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return increase_factors_by_factor

def analyze_and_plot_final_comparison():
    """
    Analyzes results from four different cost model scenarios and generates
    a comparative plot showing the cost increase factor for each.
    """
    # --- 1. MODIFIED Configuration: Define the 4 cost scenarios to compare ---
    scenarios = {
        "High Fixed Transit, Low Peering": {
            "path": "results/high_fixed_transit/results",
            "color": "dodgerblue",
            "linestyle": "solid"
        },
        "Commitment-Based Transit": {
            "path": "results/commitment_based_transit/results",
            "color": "green",
            "linestyle": "dashed"
        },
        "Peering with High Port Fees": {
            "path": "results/peering_with_port_fees/results",
            "color": "red",
            "linestyle": "dotted"
        },
        "Paid Peering Model": {
            "path": "results/paid_peering/results",
            "color": "darkorange",
            "linestyle": "dashdot"
        }
    }
    output_plot_file = "cost_model_scenario_comparison.png"

    # --- 2. Process data for each scenario ---
    all_factor_results = {}
    for scenario_name, config in scenarios.items():
        factor_data = process_factors_from_folder(config["path"])
        if factor_data:
            all_factor_results[scenario_name] = factor_data

    if not all_factor_results:
        print("\nNo data found across any specified directories. Cannot generate a plot.")
        return

    print("\nAll folders processed. Generating comparative plot...")

    # --- 3. Plotting the results ---
    fig, ax = plt.subplots(figsize=(16, 10))
    all_scenario_factors = set()

    for scenario_name, factor_data in all_factor_results.items():
        config = scenarios[scenario_name]
        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)
        average_factors = [sum(factor_data[f]) / len(factor_data[f]) if factor_data[f] else 0 for f in sorted_factors]

        # Plot individual data points with low opacity
        for factor in sorted_factors:
            ax.scatter([factor] * len(factor_data[factor]), factor_data[factor],
                       alpha=0.15, color=config["color"], s=40, label='_nolegend_')
        
        # Plot the average trend line
        ax.plot(sorted_factors, average_factors,
                marker='o',
                linestyle=config["linestyle"],
                color=config["color"],
                linewidth=2.5,
                label=scenario_name)

    # --- 4. Formatting the plot ---
    ax.set_title('ISP Cost Increase Factor Across Different Cost Models', fontsize=20)
    ax.set_xlabel('Cost Difference Factor (Transit Variable Cost / Peering Variable Cost)', fontsize=14)
    ax.set_ylabel('Cost Increase Factor (Pessimal / Optimal)', fontsize=14)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.axhline(y=1.0, color='gray', linestyle=':', linewidth=1.5, label='Baseline (No Increase)')
    ax.legend(fontsize=12, loc='upper left')
    
    if all_scenario_factors:
        ax.set_xticks(sorted(list(all_scenario_factors)))
        plt.xticks(rotation=45)

    # --- 5. Save and show the plot ---
    plt.tight_layout()
    plt.savefig(output_plot_file)
    print(f"\nPlot successfully saved to '{output_plot_file}'")
    plt.show()

if __name__ == "__main__":
    # Ensure you have matplotlib installed: pip install matplotlib
    analyze_and_plot_final_comparison()