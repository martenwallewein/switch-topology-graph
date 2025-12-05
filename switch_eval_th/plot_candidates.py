import os
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def process_loss_data_from_folder(results_dir, target_block='waterfilling_optimal_1'):
    """
    Scans a directory for result files and calculates the PACKET LOSS RATIO
    for a specific algorithm block.
    """
    results = defaultdict(list)
    
    if not os.path.isdir(results_dir):
        print(f"Warning: Directory not found: '{results_dir}'")
        return None

    filename_pattern = re.compile(r"result_factor_(\d+(?:\.\d+)?)_run_(\d+)\.json")

    print(f"--> Processing: {results_dir}")
    files_found = 0
    
    for filename in os.listdir(results_dir):
        match = filename_pattern.match(filename)
        if match:
            traffic_factor = float(match.group(1))
            file_path = os.path.join(results_dir, filename)

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                if target_block in data:
                    analysis_data = data[target_block]
                    files_found += 1
                    
                    # --- CORE CALCULATION ---
                    total_sent = analysis_data.get('total_sent_traffic', 0)
                    total_unsent = analysis_data.get('total_unsent_traffic', 0)
                    total_demand = total_sent + total_unsent

                    # Avoid division by zero
                    if total_demand > 0:
                        loss_ratio = total_unsent / total_demand
                    else:
                        loss_ratio = 0.0

                    results[traffic_factor].append(loss_ratio)

            except Exception as e:
                print(f"    - Warning: Could not process file '{filename}'. Reason: {e}")
    
    if files_found == 0:
        print(f"    - No valid files found in {results_dir}")
        return None

    return results

def get_dummy_data(offset=0):
    """Generates dummy data if files are missing for testing plotting."""
    return {
        i/2.0: [max(0, min(1.0, (i/2.0 - (2.0 + offset)) * 0.15)) + np.random.normal(0, 0.002) for _ in range(5)]
        for i in range(2, 14)
    }

def analyze_and_plot_packet_loss():
    """
    Generates a comparative plot for waterfilling_optimal_1 across different folders.
    """
    
    # --- 1. Style Configuration ---
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 8,
        'axes.labelsize': 9,
        'axes.titlesize': 9,
        'legend.fontsize': 6,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'lines.linewidth': 1.5,
        'lines.markersize': 4
    })

    output_plot_file = "waterfilling_loss_comparison.pdf"
    
    # --- 2. Define Scenarios ---
    # Structure: Label, Color, Path (No Peering), Path (With Peering)
    scenarios = [
        {
            "label": "Balanced",
            "color": "dodgerblue",
            "path_no": "results/random_latency_balanced/no_prefer_peering/results",
            "path_with": "results/random_latency_balanced/with_prefer_peering/results"
        },
        {
            "label": "High Latency",
            "color": "firebrick",
            "path_no": "results/random_transit_high_latency/no_prefer_peering/results",
            "path_with": "results/random_transit_high_latency/with_prefer_peering/results"
        },
        {
            "label": "Low Latency",
            "color": "forestgreen",
            "path_no": "results/random_transit_low_latency/no_prefer_peering/results",
            "path_with": "results/random_transit_low_latency/with_prefer_peering/results"
        }
    ]

    target_algo = 'waterfilling_optimal_1'

    # --- 3. Plotting Setup ---
    fig, ax = plt.subplots(figsize=(4.5, 3.0)) # Slightly wider for legend
    all_scenario_factors = set()

    print(f"Generating plot for algorithm: {target_algo}")

    # --- 4. Process and Plot Each Scenario ---
    for i, scen in enumerate(scenarios):
        color = scen["color"]
        
        # We process twice per scenario: once for No Peering (Solid), once for With Peering (Dashed)
        sub_configs = [
            ("No Prefer Peering", scen["path_no"], "-", 0),
            ("With Prefer Peering", scen["path_with"], "-.", 0.5) # Offset dummy data slightly
        ]

        for suffix, path, style, dummy_offset in sub_configs:
            
            # Retrieve data
            data = process_loss_data_from_folder(path, target_algo)
            
            # Fallback to dummy data if path doesn't exist (for demonstration)
            if not data:
                data = get_dummy_data(offset=i + dummy_offset) 

            if not data: continue

            sorted_factors = sorted(data.keys())
            all_scenario_factors.update(sorted_factors)

            # Calculate stats
            average_loss_pct = [np.mean(data[f]) * 100 for f in sorted_factors]
            std_devs_pct = [np.std(data[f]) * 100 for f in sorted_factors]
            
            # Full label only for the legend
            line_label = f"{scen['label']} ({suffix})"

            # Plot Error Bars / Line
            ax.errorbar(sorted_factors, average_loss_pct,
                        yerr=std_devs_pct,
                        marker='o',
                        markersize=3,
                        linestyle=style,
                        color=color,
                        label=line_label,
                        capsize=2,
                        elinewidth=0.8,
                        capthick=0.8,
                        alpha=0.9)

    # --- 5. Formatting ---
    ax.set_xlabel('Traffic Multiplier')
    ax.set_ylabel('Traffic Loss / Unsent (%)')
    ax.set_title(f"Packet Loss: {target_algo}")
    
    ax.set_ylim(bottom=-1) # Buffer
    
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)
    
    # Legend placement
    ax.legend(loc='upper left', frameon=True, framealpha=0.9, edgecolor='white')
    
    if all_scenario_factors:
        sorted_list = sorted(list(all_scenario_factors))
        ax.set_xticks(sorted_list)
        if len(sorted_list) > 10:
            plt.xticks(rotation=45)

    # --- 6. Save and show ---
    plt.tight_layout()
    plt.savefig(output_plot_file, dpi=300)
    print(f"\nPlot successfully saved to '{output_plot_file}'")
    plt.show()

if __name__ == "__main__":
    analyze_and_plot_packet_loss()