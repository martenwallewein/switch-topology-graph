import subprocess
import os
import sys

def run_workflow():
    """
    Orchestrates a two-step process for multiple, distinct cost model configurations.
    
    This version keeps traffic constant (-t 1.0) and varies the 'latency_inflation' parameter.
    It runs each configuration with and without '--prefer-peering'.
    
    1. Calls a scenario generator script with specific cost parameters and latency inflation.
    2. Calls the scenario runner script for each generated scenario.
    """
    # --- Configuration ---
    # Ensure these match the actual filenames of your scripts
    scenario_generator_script = "scenario_gen_full.py" 
    scenario_runner_script = "run_all_scenarios_final.py"
    graph_file = "final_graph_link_types_balanced.json"
    traffic_file = "max_by_destination.csv"

    # --- Define the experiment configurations ---
    configurations = [
        {
            "name": "worst_case_5",
            "transit_base_cost": 1,
            "peering_base_cost": 1,
            "peering_variable_cost": 1, # Low, but non-zero
            "use_worst_case_links": True,
            "desc": "High Fixed Costs for Transit, Low for Peering (Worst Case Latencies)"
        },
        # You can uncomment other configurations as needed
        #{
        #    "name": "balanced",
        #    "transit_base_cost": 1,
        #    "peering_base_cost": 1,
        #    "peering_variable_cost": 1,
        #    "use_worst_case_links": False,
        #    "desc": "Balanced Costs"
        #}
    ]

    # --- Loop through each configuration ---
    for config in configurations:
        print(f"\n{'='*80}")
        print(f"--- Starting Configuration: {config['desc']} ---")
        print(f"{'='*80}")

        # --- Loop to run with and without the --prefer-peering flag ---
        for prefer_peering_flag in [True]: # Add False to list if needed: [True, False]
            mode_name = "with_prefer_peering" if prefer_peering_flag else "no_prefer_peering"
            mode_desc = "WITH --prefer-peering" if prefer_peering_flag else "WITHOUT --prefer-peering (default)"

            print(f"\n{'-'*70}")
            print(f"--- Running Mode: {mode_desc} ---")
            print(f"{'-'*70}")

            # Define unique output directories for this scenario and mode
            scenario_output_dir = os.path.join("results", config['name'], mode_name, "scenarios")
            results_output_dir = os.path.join("results", config['name'], mode_name, "results")

            # --- 1. Create the output directories ---
            try:
                os.makedirs(scenario_output_dir, exist_ok=True)
                os.makedirs(results_output_dir, exist_ok=True)
                print(f"Output directories in 'results/{config['name']}/{mode_name}/' are ready.")
            except OSError as e:
                print(f"Error creating directories: {e}")
                continue
 
            # --- 2. Loop through Latency Inflation values ---
            # Instead of traffic factor 1-20, we vary inflation from 1.0 to 3.0 in 0.1 steps.
            # Range(0, 21) gives us 21 data points.
            for step in range(0, 21):
                # Calculate inflation: 1.0, 1.1, 1.2 ... 3.0
                latency_inflation = round(1.0 + (step * 0.1), 2)
                
                print(f"\n--- Processing latency_inflation: {latency_inflation} ---")
                
                for run_number in range(1, 10):
                    print(f"\n  - Starting run {run_number}/10 for inflation {latency_inflation}...")
                    
                    # Naming convention changed to reflect inflation
                    base_filename = f"inflation_{latency_inflation}_run_{run_number}"
                    scenario_output_path = os.path.join(scenario_output_dir, f"scenario_{base_filename}.json")
                    result_output_path = os.path.join(results_output_dir, f"result_{base_filename}.json")

                    # --- STEP 1: Generate the scenario file ---
                    print(f"    [1/2] Generating scenario: {scenario_output_path}")
                    generator_command = [
                        sys.executable,
                        scenario_generator_script,
                        graph_file,
                        traffic_file,
                        "-o", scenario_output_path,
                        "-t", "5.0", # Keep traffic constant at 1.0
                        "--transit-base-cost", str(config["transit_base_cost"]),
                        "--peering-base-cost", str(config["peering_base_cost"]),
                        "--peering-variable-cost", str(config["peering_variable_cost"]),
                        "--latency_inflation", str(latency_inflation) # Pass the variable parameter
                    ]

                    # Add flags based on config
                    if config.get("use_worst_case_links", False):
                        generator_command.append("--use_worst_case_links")

                    # Conditionally add the --prefer-peering flag
                    if prefer_peering_flag:
                        generator_command.append("--prefer_peering")

                    try:
                        # Capture output to avoid cluttering console unless error
                        res = subprocess.run(generator_command, check=True, capture_output=True, text=True)
                        # print(res.stdout) # Uncomment if you want to see generator logs
                        print(f"    [1/2] Scenario generation successful (Inflation: {latency_inflation}).")
                        
                    except FileNotFoundError:
                        print(f"    ERROR: The script '{scenario_generator_script}' was not found.")
                        return
                    except subprocess.CalledProcessError as e:
                        print(f"    ERROR during scenario generation for {base_filename}.")
                        print(f"    ----- Error Output -----\n{e.stderr.strip()}\n    ------------------------")
                        continue

                    # --- STEP 2: Run the scenario ---
                    print(f"    [2/2] Running scenario and generating result: {result_output_path}")
                    runner_command = [sys.executable, scenario_runner_script, scenario_output_path, result_output_path]

                    try:
                        subprocess.run(runner_command, check=True, capture_output=True, text=True)
                        print("    [2/2] Scenario run successful.")
                    except FileNotFoundError:
                        print(f"    ERROR: The script '{scenario_runner_script}' was not found.")
                        return
                    except subprocess.CalledProcessError as e:
                        print(f"    ERROR during scenario run for {base_filename}.")
                        print(f"    ----- Error Output -----\n{e.stderr.strip()}\n    ------------------------")
                        continue

    print("\nAll workflow tasks are complete.")

if __name__ == "__main__":
    run_workflow()