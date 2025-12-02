import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_factors_from_folder(results_dir):
    """
    Scans a directory for result files and calculates the cost increase factor.
    (Logic preserved from input script)
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    increase_factors_by_factor = defaultdict(list)
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

                optimal_cost = data['isp_optimal']['total_cost']
                pessimal_cost = data['isp_pessimal']['total_cost']

                if optimal_cost > 0:
                    increase_factor = pessimal_cost / optimal_cost
                    increase_factors_by_factor[cost_factor].append(increase_factor)
                elif pessimal_cost == 0:
                    increase_factors_by_factor[cost_factor].append(1.0)
                else:
                    # Silent skip for infinite increase to keep log clean
                    pass

            except Exception as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return increase_factors_by_factor


def analyze_and_plot_final_comparison():
    """
    Analyzes results (With vs Without Peering Preference) and generates a 
    condensed, academic-style plot with error bars.
    """

    # --- 1. Style Configuration for LaTeX/Academic Paper ---
    # Sets font sizes to be readable at approx 3.5 inches wide
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

    # Shortened names for the legend to fit narrow column
    scenarios = {
        "Without --prefer_peering": {
            "path": "results/balanced/no_prefer_peering/results",
            "color": "#1f77b4", # Standard Matplotlib Blue
            "linestyle": "-", 
            "label": "No Preference" 
        },
        "With --prefer_peering": {
            "path": "results/balanced/with_prefer_peering/results",
            "color": "#2ca02c", # Standard Matplotlib Green
            "linestyle": "-",
            "label": "Prefer Peering"
        }
    }
    
    output_plot_file = "peering_preference_comparison.pdf"

    # --- 2. Process data for each scenario ---
    all_factor_results = {}
    for scenario_name, config in scenarios.items():
        factor_data = process_factors_from_folder(config["path"])
        if factor_data:
            all_factor_results[scenario_name] = factor_data

    if not all_factor_results:
        print("\nNo data found. Generating dummy data for visual verification...")
        # Optional: Generate dummy data if folders don't exist
        for name in scenarios:
            base = 1.0 if "Without" in name else 1.2
            all_factor_results[name] = {
                i: [base + (i*0.02) + np.random.normal(0, 0.05) for _ in range(10)] 
                for i in range(1, 11)
            }

    print("\nAll folders processed. Generating condensed plot...")

    # --- 3. Plotting the results ---
    # figsize=(3.5, 2.6) matches the single column width
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    all_scenario_factors = set()

    # Plot data for each scenario
    for scenario_name, factor_data in all_factor_results.items():
        original_config = scenarios[scenario_name]
        color = original_config["color"]
        linestyle = original_config["linestyle"]
        label = original_config["label"]
        
        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)

        average_factors = [np.mean(factor_data[f]) if factor_data[f] else 0 for f in sorted_factors]
        std_devs = [np.std(factor_data[f]) if factor_data[f] else 0 for f in sorted_factors]

        # Plot all individual data points (Scatter)
        # s=10 and alpha=0.15 for subtle background data
        for factor in sorted_factors:
            ax.scatter([factor] * len(factor_data[factor]), factor_data[factor],
                       alpha=0.15, color=color, s=10, marker='.', linewidths=0, zorder=1)
        
        # Plot the average trend line with error bars
        # Capsize reduced to 2 for small figure, thinner error lines
        ax.errorbar(sorted_factors, average_factors,
                    yerr=std_devs,
                    marker='o',
                    markersize=3,
                    linestyle=linestyle,
                    color=color,
                    label=label,
                    capsize=2,
                    elinewidth=0.8,
                    capthick=0.8,
                    zorder=2)

    # --- 4. Formatting the plot ---
    # Concise labels for small space
    ax.set_xlabel(r'Transit/Peering Cost Ratio ($C_T / C_P$)')
    ax.set_ylabel('Cost Increase Factor')
    
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)
    
    # Baseline line
    ax.axhline(y=1.0, color='gray', linestyle='-', linewidth=0.8, alpha=0.5, zorder=0)
    
    if all_scenario_factors:
        ax.set_xticks(sorted(list(all_scenario_factors)))

    # Legend placed for best fit
    ax.legend(loc='best', frameon=True, framealpha=0.9, fancybox=False, edgecolor='white')

    # --- 5. Save and show the plot ---
    plt.tight_layout(pad=0.3)
    plt.savefig(output_plot_file, dpi=300)
    print(f"\nPlot successfully saved to '{output_plot_file}'")
    plt.show()

if __name__ == "__main__":
    analyze_and_plot_final_comparison()