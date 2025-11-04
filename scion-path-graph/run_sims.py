import os
import subprocess
import argparse
from datetime import datetime

def main():
    """
    A wrapper script to run a simulation multiple times with different
    random seeds, storing each result in a unique file.
    """
    parser = argparse.ArgumentParser(
        description="Run a simulation script for a specified number of rounds with random seeds."
    )
    parser.add_argument(
        "simulation_script",
        help="Path to the Python simulation script to execute (e.g., growth_simulation.py)."
    )
    parser.add_argument(
        "graphml_file",
        help="Path to the input GraphML file for the simulation."
    )
    parser.add_argument(
        "-n", "--num-rounds",
        type=int,
        required=True,
        help="The total number of simulation rounds to perform."
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="simulation_data",
        help="The directory where result files will be stored (default: simulation_data)."
    )
    args = parser.parse_args()

    # --- 1. Create the output directory if it doesn't exist ---
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        print(f"Results will be saved in the '{args.output_dir}/' directory.")
    except OSError as e:
        print(f"Error creating directory {args.output_dir}: {e}")
        return

    # --- 2. Loop through the specified number of rounds ---
    print(f"\nStarting {args.num_rounds} simulation rounds...")
    for i in range(1, args.num_rounds + 1):
        # The seed is simply the round number for reproducibility.
        # Could also be a random number if preferred.
        seed = i
        
        print(f"\n{'='*40}")
        print(f"--- Round {i} of {args.num_rounds} (Seed: {seed}) ---")
        print(f"{'='*40}")

        # --- 3. Define a unique output filename for this round ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"run_{i:03d}_seed_{seed}_{timestamp}.json"
        output_path = os.path.join(args.output_dir, output_filename)

        # --- 4. Construct and run the command for the simulation script ---
        command = [
            "python",
            args.simulation_script,
            args.graphml_file,
            "--seed", str(seed),
            "--output", output_path
        ]

        try:
            # The 'subprocess.run' command executes the child script and waits
            # for it to complete. We capture and print its output in real-time.
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
            
            # Stream the output
            for line in process.stdout:
                print(line, end='')

            process.wait() # Wait for the subprocess to finish

            if process.returncode != 0:
                print(f"\n--- Round {i} failed with exit code {process.returncode} ---")
            else:
                print(f"\n--- Round {i} completed successfully. Results saved to '{output_path}' ---")

        except FileNotFoundError:
            print(f"Error: The script '{args.simulation_script}' was not found.")
            break
        except Exception as e:
            print(f"An error occurred while running the simulation script: {e}")
            break
            
    print(f"\n{'='*40}")
    print("All simulation rounds are complete.")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()