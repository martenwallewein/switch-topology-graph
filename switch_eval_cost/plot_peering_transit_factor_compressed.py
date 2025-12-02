import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt

def process_factors_from_folder(results_dir):
    """
    Scans a directory for result files and calculates the cost increase factor.
    (Logic unchanged from original)
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
                    pass 

            except Exception as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")

    return increase_factors_by_factor


def analyze_and_plot_final_comparison():
    """
    Analyzes results and generates a condensed, academic-style plot.
    """
    
    # --- 1. Style Configuration for LaTeX/Academic Paper ---
    # Sets font sizes to be readable at approx 3.5 inches wide
    plt.rcParams.update({
        'font.family': 'serif',          # Serif font matches LaTeX body text usually
        'font.size': 8,                  # Base font size
        'axes.labelsize': 9,             # Axis labels slightly larger
        'axes.titlesize': 9,
        'legend.fontsize': 7,            # Legend slightly smaller
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'lines.linewidth': 1.5,
        'lines.markersize': 4
    })

    # Shortened names for the legend to fit narrow column
    scenarios = {
        "Switch Traffic Data (Balanced Peering/Transit)": {
            "path": "results/balanced/no_prefer_peering/results",
            "color": "#2ca02c", # Standard Matplotlib Green
            "linestyle": "-", 
            "label": "Balanced (Real)" 
        },
        "Hypothetical: High Peering / Low Transit": {
            "path": "results/high_peering/no_prefer_peering/results",
            "color": "#1f77b4", # Standard Matplotlib Blue
            "linestyle": "--",
            "label": "High Peering"
        },
        "Hypothetical: Low Peering / High Transit": {
            "path": "results/low_peering/no_prefer_peering/results",
            "color": "#ff7f0e", # Standard Matplotlib Orange
            "linestyle": ":",
            "label": "Low Peering"
        }
    }
    
    # Save as PDF (Vector graphics) for best LaTeX quality
    output_plot_file = "scenario_comparison_column.pdf"

    # --- 2. Process data ---
    all_factor_results = {}
    for scenario_name, config in scenarios.items():
        factor_data = process_factors_from_folder(config["path"])
        if factor_data:
            all_factor_results[scenario_name] = factor_data

    if not all_factor_results:
        print("\nNo data found. Generating dummy plot for visual verification...")
        # (Optional) Create dummy data if folders don't exist for testing
        # remove this block if you only want real data
        import random
        for name in scenarios:
            all_factor_results[name] = {i: [1.0 + (i*0.05) + random.uniform(-0.1, 0.1) for _ in range(5)] for i in range(1, 11)}

    print("\nGenerating condensed plot...")

    # --- 3. Plotting ---
    # figsize=(3.5, 2.6) is roughly the width of 1 column in a 2-column article
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    
    all_scenario_factors = set()

    for original_name, factor_data in all_factor_results.items():
        config = scenarios[original_name]
        color = config["color"]
        linestyle = config["linestyle"]
        label = config["label"]
        
        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)

        average_factors = [sum(factor_data[f]) / len(factor_data[f]) if factor_data[f] else 0 for f in sorted_factors]

        # Scatter points: smaller size (s=10) and low alpha for clarity
        for factor in sorted_factors:
            ax.scatter([factor] * len(factor_data[factor]), factor_data[factor],
                       alpha=0.15, color=color, s=10, marker='.', linewidths=0)
        
        # Mean line
        ax.plot(sorted_factors, average_factors,
                marker='o',
                markersize=3,
                linestyle=linestyle,
                color=color,
                label=label)

    # --- 4. Formatting ---
    # Condensed Axis Labels
    ax.set_xlabel(r'Transit/Peering Cost Ratio ($C_T / C_P$)')
    ax.set_ylabel('Cost Increase Factor')
    
    # Grid
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)
    
    # Baseline
    ax.axhline(y=1.0, color='gray', linestyle='-', linewidth=0.8, alpha=0.5, zorder=0)

    # X-Axis Ticks
    if all_scenario_factors:
        ax.set_xticks(sorted(list(all_scenario_factors)))
    
    # Legend: Placed "best" to avoid covering data, frame reduced
    ax.legend(loc='best', frameon=True, framealpha=0.9, fancybox=False, edgecolor='white')

    # Tight Layout is crucial for small figures to prevent clipping
    plt.tight_layout(pad=0.3)
    
    plt.savefig(output_plot_file, dpi=300)
    print(f"\nPlot saved to '{output_plot_file}'")

    plt.show() # Comment out if running on a headless server

if __name__ == "__main__":
    analyze_and_plot_final_comparison()