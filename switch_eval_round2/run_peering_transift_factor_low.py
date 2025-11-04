import subprocess
import os
import sys

def run_workflow():
    """
    Orchestrates a two-step process:
    1. Calls scenario_gen_csv.py to generate scenario files with varying cost factors.
    2. Calls run_all_scenarios.py using each generated scenario file as input.
    """
    # --- Configuration ---
    # Scripts to be executed
    scenario_generator_script = "scenario_gen_csv.py"
    scenario_runner_script = "run_all_scenarios.py"

    # Input files for the generator script
    graph_file = "final_graph_link_types_low.json"
    traffic_file = "avg_by_destination.csv"

    # Output directories for the generated files
    scenario_output_dir = "peering_transit_factor_low/scenarios"
    results_output_dir = "peering_transit_factor_low/results"

    # --- 1. Create the output directories if they don't exist ---
    try:
        os.makedirs(scenario_output_dir, exist_ok=True)
        os.makedirs(results_output_dir, exist_ok=True)
        print(f"Output directories '{scenario_output_dir}/' and '{results_output_dir}/' are ready.")
    except OSError as e:
        print(f"Error creating directories: {e}")
        return

    # --- 2. Loop through the cost factors and repetitions ---
    for cost_factor in range(2, 21):  # Loops from 2 to 20
        print(f"\n{'='*50}")
        print(f"--- Processing all runs for cost_difference_factor: {cost_factor} ---")
        print(f"{'='*50}")
        for run_number in range(1, 11):  # Loops 10 times (from 1 to 10)
            print(f"\n  - Starting run {run_number}/10 for factor {cost_factor}...")

            # --- 3. Define unique file paths for this iteration ---
            base_filename = f"factor_{cost_factor}_run_{run_number}"
            scenario_output_path = os.path.join(scenario_output_dir, f"scenario_{base_filename}.json")
            result_output_path = os.path.join(results_output_dir, f"result_{base_filename}.json")

            # --- STEP 1: Generate the scenario file ---
            print(f"    [1/2] Generating scenario: {scenario_output_path}")
            generator_command = [
                sys.executable,  # Use the same python interpreter running this script
                scenario_generator_script,
                graph_file,
                traffic_file,
                "-o", scenario_output_path,
                "-c", str(cost_factor)
            ]

            try:
                subprocess.run(
                    generator_command,
                    check=True,       # Raise an exception on non-zero exit codes
                    capture_output=True,
                    text=True
                )
                print(f"    [1/2] Scenario generation successful.")
            except FileNotFoundError:
                print(f"    ERROR: The script '{scenario_generator_script}' was not found.")
                return
            except subprocess.CalledProcessError as e:
                print(f"    ERROR during scenario generation for {base_filename}.")
                print(f"    ----- Error Output -----\n{e.stderr.strip()}\n    ------------------------")
                continue # Skip to the next run

            # --- STEP 2: Run the scenario with the second script ---
            print(f"    [2/2] Running scenario and generating result: {result_output_path}")
            runner_command = [
                sys.executable,
                scenario_runner_script,
                scenario_output_path,   # Input is the file we just created
                result_output_path      # Output is the properly named result file
            ]

            try:
                subprocess.run(
                    runner_command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"    [2/2] Scenario run successful.")
            except FileNotFoundError:
                print(f"    ERROR: The script '{scenario_runner_script}' was not found.")
                return
            except subprocess.CalledProcessError as e:
                print(f"    ERROR during scenario run for {base_filename}.")
                print(f"    ----- Error Output -----\n{e.stderr.strip()}\n    ------------------------")
                continue # Skip to the next run

    print("\nAll workflow tasks are complete.")

if __name__ == "__main__":
    run_workflow()