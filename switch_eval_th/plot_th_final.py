import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import UnivariateSpline

def process_traffic_data_from_folder(results_dir, json_key):
    """
    Scans a directory for result files and calculates the ratio of
    spillover traffic to total sent traffic.
    
    Args:
        results_dir (str): Path to the folder.
        json_key (str): The specific block in the JSON to analyze 
                        (e.g., 'latency_optimal' or 'fair_share_latency_optimal').
    """
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found, skipping: '{results_dir}'")
        return None

    spillover_ratios_by_factor = defaultdict(list)
    
    filename_pattern = re.compile(r"result_factor_(\d+(?:\.\d+)?)_run_(\d+)\.json")

    print(f"--> Processing folder: {results_dir} | Key: {json_key}")
    for filename in os.listdir(results_dir):
        match = filename_pattern.match(filename)
        if match:
            traffic_factor = float(match.group(1))
            file_path = os.path.join(results_dir, filename)

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                if json_key not in data:
                    continue
                
                analysis_data = data[json_key]
                total_sent_traffic = analysis_data.get('total_sent_traffic', 0)
                congestion_analysis = analysis_data.get('congestion_analysis', {})

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


def smooth_curve(x, y, smoothing_strength=1.0, num_points=300):
    """
    Smooth a curve using a cubic smoothing spline.

    Args:
        x (list or np.ndarray): X values
        y (list or np.ndarray): Y values
        smoothing_strength (float): Higher = smoother
        num_points (int): Number of interpolated points

    Returns:
        x_smooth, y_smooth
    """
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    if len(x) < 4:
        # Not enough points for a proper cubic spline; fall back to original data
        return x, y

    # Ensure strictly increasing x
    sort_idx = np.argsort(x)
    x = x[sort_idx]
    y = y[sort_idx]

    # Smoothing spline
    spline = UnivariateSpline(x, y, s=smoothing_strength)
    x_smooth = np.linspace(x.min(), x.max(), num_points)
    y_smooth = spline(x_smooth)

    # Avoid tiny negative artifacts from smoothing
    y_smooth = np.clip(y_smooth, 0, None)

    return x_smooth, y_smooth


def analyze_and_plot_congestion():
    """
    Analyzes results from multiple scenario folders and generates a comparative plot
    showing the spillover traffic ratio against the traffic increase factor.
    """
    
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

    scenarios = {
        "Selfish (Prefer Peering)": {
            "path": "results/best_case/with_prefer_peering/results",
            "json_key": "latency_optimal",
            "color": "red",
            "linestyle": "--",
            "label": "Selfish (Prefer Peering)"
        },
        "Selfish (Path Unlocking)": {
            "path": "results/best_case/no_prefer_peering/results",
            "json_key": "latency_optimal",
            "color": "blue",
            "linestyle": "-",
            "label": "Selfish (Path Unlocking)"
        },
        "Fair Share (Prefer Peering)": {
            "path": "results/best_case/with_prefer_peering/results",
            "json_key": "fair_share_latency_optimal_3",
            "color": "green",
            "linestyle": "-.",
            "label": "Cooperative (Prefer Peering)"
        },
        "Fair Share (Path Unlocking)": {
            "path": "results/best_case/no_prefer_peering/results",
            "json_key": "fair_share_latency_optimal_3",
            "color": "purple",
            "linestyle": "-.",
            "label": "Cooperative (Path Unlocking)"
        }
    }

    output_plot_file = "congestion_spillover_comparison_compressed.pdf"

    all_factor_results = {}
    for scenario_name, config in scenarios.items():
        factor_data = process_traffic_data_from_folder(config["path"], config["json_key"])
        if factor_data:
            all_factor_results[scenario_name] = factor_data

    if not all_factor_results:
        print("\nNo data found. Generating dummy data for visual verification...")
        for name in scenarios:
            all_factor_results[name] = {
                i / 2.0: [max(0, (i / 2.0 - 1.5) * 0.1) + np.random.normal(0, 0.01) for _ in range(5)]
                for i in range(2, 10)
            }

    print("\nGenerating condensed congestion plot...")

    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    all_scenario_factors = set()

    for scenario_name, factor_data in all_factor_results.items():
        config = scenarios[scenario_name]
        color = config["color"]
        linestyle = config["linestyle"]
        label = config["label"]
        
        sorted_factors = sorted(factor_data.keys())
        all_scenario_factors.update(sorted_factors)

        average_ratios = [np.mean(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]
        std_devs = [np.std(factor_data[f]) * 100 if factor_data[f] else 0 for f in sorted_factors]

        # Scatter raw runs
        for factor in sorted_factors:
            y_values = [v * 100 for v in factor_data[factor]]
            ax.scatter(
                [factor] * len(y_values),
                y_values,
                alpha=0.15,
                color=color,
                s=10,
                marker='.',
                linewidths=0,
                zorder=1
            )

        # Optional: show error bars at actual sample points
        ax.errorbar(
            sorted_factors,
            average_ratios,
            yerr=std_devs,   # comment this out if you don't want error bars
            fmt='o',
            markersize=3,
            color=color,
            capsize=2,
            elinewidth=0.8,
            capthick=0.8,
            alpha=0.8,
            zorder=2
        )

        # Smooth line through the means
        x_smooth, y_smooth = smooth_curve(
            sorted_factors,
            average_ratios,
            smoothing_strength=2.0,   # increase for more smoothing
            num_points=300
        )

        ax.plot(
            x_smooth,
            y_smooth,
            linestyle=linestyle,
            color=color,
            label=label,
            zorder=3
        )

    ax.set_xlabel('Traffic Multiplier')
    ax.set_ylabel('Congestion (% of Total Traffic)')
    ax.set_ylim(0, 25)

    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)

    if all_scenario_factors:
        sorted_list = sorted(list(all_scenario_factors))
        ax.set_xticks(sorted_list)
        if len(sorted_list) > 8:
            plt.xticks(rotation=45)

    ax.legend(loc='best', frameon=True, framealpha=0.9, fancybox=False, edgecolor='white')

    plt.tight_layout(pad=0.3)
    plt.savefig(output_plot_file, dpi=300)
    print(f"\nPlot successfully saved to '{output_plot_file}'")
    plt.show()


if __name__ == "__main__":
    analyze_and_plot_congestion()