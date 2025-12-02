import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_traffic_data_from_folder(results_dir):
    """
    Scans a directory for result files and calculates the spillover traffic ratio
    for 'latency_optimal', 'fair_share_latency_optimal', etc.
    (Logic preserved from input script)
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
    
    # Regex handles integer and float numbers
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

                # Process multiple blocks from the same file
                for block_name in results.keys():
                    if block_name not in data:
                        # Silent info or debug print if needed
                        # print(f"    - Info: '{block_name}' key not found in '{filename}'...")
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

    # Configuration: Scenario path
    scenario = {
        "path": "results/worst_case/with_prefer_peering/results",
    }
    output_plot_file = "congestion_spillover_comparison_compressed2.pdf"
    
    # Plot styles for each analysis block
    # Labels shortened slightly to fit single column width
    plot_configs = {
        "latency_optimal": {
            "label": "Thundering Herd",
            "color": "red",
            "linestyle": "-"
        },
        "fair_share_latency_optimal": {
            "label": "ECMP 2 Paths",
            "color": "dodgerblue",
            "linestyle": "-"
        },
        "fair_share_latency_optimal_3": {
            "label": "ECMP 3 Paths",
            "color": "green",
            "linestyle": "-"
        }
    }

    # --- 2. Process data ---
    all_block_results = process_traffic_data_from_folder(scenario["path"])

    if not all_block_results:
        print("\nNo data found. Generating dummy data for verification...")
        # Optional: Dummy data generation if path doesn't exist
        for block in plot_configs:
            # Simulate different congestion curves
            start = 1.5 if "latency" in block and "fair" not in block else 2.0
            all_block_results[block] = {
                i/2.0: [max(0, (i/2.0 - start) * 0.1) + np.random.normal(0, 0.005) for _ in range(5)]
                for i in range(2, 10)
            }

    print("\nFolder processed. Generating condensed plot...")

    # --- 3. Plotting the results ---
    # Standard single-column size (3.5 inches wide)
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    all_scenario_factors = set()

    for block_name, factor_data in all_block_results.items():
        if not factor_data: 
            continue
            
        config = plot_configs.get(block_name)
        if not config:
            continue
        
        color = config["color"]
        linestyle = config["linestyle"]
        label = config["label"]
        
        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)

        # Convert ratio to percentage
        average_ratios_pct = [np.mean(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]
        std_devs_pct = [np.std(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]
        
        # Scatter points (background, faint)
        for factor in sorted_factors:
            y_values = [v * 100 for v in factor_data[factor]]
            ax.scatter([factor] * len(y_values), y_values,
                       alpha=0.15, color=color, s=10, marker='.', linewidths=0, zorder=1)

        # Error bars and trend line
        ax.errorbar(sorted_factors, average_ratios_pct,
                    yerr=std_devs_pct,
                    marker='o',
                    markersize=3,
                    linestyle=linestyle,
                    color=color,
                    label=label,
                    capsize=2,       # Small caps
                    elinewidth=0.8,  # Thin error lines
                    capthick=0.8,
                    zorder=2)

    # --- 4. Formatting the plot ---
    # Concise labels
    ax.set_xlabel('Traffic Multiplier')
    ax.set_ylabel('Congestion (% of Total Traffic)')
    
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)
    
    # Legend
    ax.legend(loc='best', frameon=True, framealpha=0.9, fancybox=False, edgecolor='white')
    
    # Ticks
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