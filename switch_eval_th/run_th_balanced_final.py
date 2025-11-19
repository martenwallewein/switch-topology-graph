import subprocess
import os
import sys

def run_workflow():
    """
    Orchestrates a two-step process for multiple, distinct cost model configurations.
    This version runs each configuration twice: with and without '--prefer-peering'.
    1. Calls a scenario generator script with specific cost parameters for each model.
    2. Calls the scenario runner script for each generated scenario.
    """
    # --- Configuration ---
    scenario_generator_script = "scenario_gen_full.py"
    scenario_runner_script = "run_all_scenarios_final.py"
    graph_file = "final_graph_link_types_balanced.json"
    traffic_file = "max_by_destination.csv"

    # --- Define the 4 different experiment configurations to run ---
    # Assumes scenario_gen_with_pp.py accepts:
    # --transit-base-cost, --peering-base-cost, --peering-variable-cost
    configurations = [
        #{
        #    "name": "balanced",
        #    "transit_base_cost": 1,
        #    "peering_base_cost": 1,
        #    "peering_variable_cost": 1, # Low, but non-zero
        #    "desc": "High Fixed Costs for Transit, Low for Peering",
        #    "use_worst_case_links": False
        #},
        {
            "name": "worst_case",
            "transit_base_cost": 1,
            "peering_base_cost": 1,
            "peering_variable_cost": 1, # Low, but non-zero
            "use_worst_case_links": True,
            "desc": "High Fixed Costs for Transit, Low for Peering"
        },
        #{
        #    "name": "commitment_based_transit",
        #    "transit_base_cost": 15000, # Higher fixed cost representing a CIR commit
        #    "peering_base_cost": 500,
        #    #"peering_variable_cost": 0.1,
        #    "desc": "Commitment-Based Transit (High Base Cost + Variable)"
        #},
        #{
        #    "name": "peering_with_port_fees",
        #    "transit_base_cost": 5000,
        #    "peering_base_cost": 2000, # Higher fixed cost for peering ports
        #    #"peering_variable_cost": 0, # True "settlement-free" peering
        #    "desc": "Zero-Cost Peering with High Port Fees"
        #},
        #{
        #    "name": "paid_peering",
        #    "transit_base_cost": 5000,
        #    "peering_base_cost": 500,
            #"peering_variable_cost": 1.0, # Peering has a significant variable cost
          #  "desc": "Paid Peering (Both have variable costs)"
        #}
    ]

    # --- Loop through each configuration ---
    for config in configurations:
        print(f"\n{'='*80}")
        print(f"--- Starting Configuration: {config['desc']} ---")
        print(f"{'='*80}")

        # --- NEW: Loop to run with and without the --prefer-peering flag ---
        for prefer_peering_flag in [False]: # [True, False]:
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
 
            # --- 2. Loop through the cost factors and repetitions ---
            for traffic_factor in range(1, 21):
                print(f"\n--- Processing traffic_factor: {traffic_factor} ---")
                for run_number in range(1, 10):
                    print(f"\n  - Starting run {run_number}/10 for factor {traffic_factor}...")
                    base_filename = f"factor_{traffic_factor}_run_{run_number}"
                    scenario_output_path = os.path.join(scenario_output_dir, f"scenario_{base_filename}.json")
                    result_output_path = os.path.join(results_output_dir, f"result_{base_filename}.json")

                    # --- STEP 1: Generate the scenario file with specific cost params ---
                    print(f"    [1/2] Generating scenario: {scenario_output_path}")
                    generator_command = [
                        sys.executable,
                        scenario_generator_script,
                        graph_file,
                        traffic_file,
                        "-o", scenario_output_path,
                        "-t", str(traffic_factor), # This factor shows how much the traffic is scaled
                        "--transit-base-cost", str(config["transit_base_cost"]),
                        "--peering-base-cost", str(config["peering_base_cost"]),
                        "--peering-variable-cost", str(config["peering_variable_cost"]),
                        "--use_worst_case_links" if config.get("use_worst_case_links", False) else ""
                    ]

                    # --- NEW: Conditionally add the --prefer-peering flag ---
                    if prefer_peering_flag:
                        generator_command.append("--prefer_peering")

                    try:
                        res = subprocess.run(generator_command, check=True, capture_output=True, text=True)
                        print(res.stdout)
                        print("    [1/2] Scenario generation successful.")
                        
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