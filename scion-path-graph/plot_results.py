import os
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def load_simulation_data(data_directory: str) -> pd.DataFrame:
    """
    Loads all JSON simulation files from a directory into a single pandas DataFrame.

    Args:
        data_directory: The path to the folder containing the result files.

    Returns:
        A pandas DataFrame with the combined data from all simulation runs.
    """
    all_data_points = []
    
    # Check if the directory exists
    if not os.path.isdir(data_directory):
        print(f"Error: Directory not found at '{data_directory}'")
        return pd.DataFrame() # Return an empty DataFrame

    print(f"Loading data from '{data_directory}'...")
    
    # Iterate over all files in the directory
    for filename in os.listdir(data_directory):
        if filename.endswith(".json"):
            file_path = os.path.join(data_directory, filename)
            try:
                with open(file_path, 'r') as f:
                    # Each file contains a list of dictionaries (steps)
                    run_data = json.load(f)
                    all_data_points.extend(run_data)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse JSON from file: {filename}")
            except Exception as e:
                print(f"Warning: An error occurred while reading {filename}: {e}")

    if not all_data_points:
        print("Warning: No valid data was loaded.")
        return pd.DataFrame()

    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(all_data_points)
    print(f"Successfully loaded {len(df)} data points from {len(os.listdir(data_directory))} files.")
    return df

def plot_results(df: pd.DataFrame, output_image_path: str):
    """
    Generates and saves a plot from the simulation data.

    Args:
        df: DataFrame containing the aggregated simulation results.
        output_image_path: The path where the plot image will be saved.
    """
    if df.empty:
        print("Cannot generate plot because no data was loaded.")
        return

    # Set the visual style for the plot
    sns.set_theme(style="darkgrid")

    # Create a figure and axes for the plot
    plt.figure(figsize=(8, 6))

    # --- Create the line plot using seaborn ---
    # Seaborn automatically groups by the x-axis value ('subgraph_size'),
    # calculates the mean of the y-axis values for each group,
    # and plots a line with a 95% confidence interval shaded around it.
    ax = sns.lineplot(
        data=df,
        x='subgraph_size',
        y='average_paths_per_node_pair',
        marker='o',  # Add markers to each data point on the line
        errorbar=('ci', 95) # ci = Confidence Interval
    )

    # --- Customize the plot ---
    #ax.set_title(
    #    'Network Path Availability vs. Network Size',
    #    fontsize=16,
    #    fontweight='bold',
    #    pad=20
    #)
    ax.set_xlabel('Network Size (Number of Nodes)', fontsize=12)
    ax.set_ylabel('Average Paths per Node Pair', fontsize=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Improve layout
    plt.tight_layout()

    # --- Save and show the plot ---
    try:
        plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
        plt.savefig("sim_results.pdf", dpi=300, bbox_inches='tight')
        print(f"\nPlot successfully saved to '{output_image_path}'")
    except Exception as e:
        print(f"Error: Could not save the plot. {e}")
        
    # Display the plot
    plt.show()

def main():
    """Main function to parse arguments and run the plotting script."""
    parser = argparse.ArgumentParser(
        description="Load simulation data from a directory and plot the results."
    )
    parser.add_argument(
        "data_directory",
        help="The directory where the JSON result files from the simulation are stored."
    )
    parser.add_argument(
        "-o", "--output",
        default="simulation_growth_plot.png",
        help="The filename for the output plot image (default: simulation_growth_plot.png)."
    )
    args = parser.parse_args()
    
    # Load the data
    simulation_df = load_simulation_data(args.data_directory)
    
    # Generate the plot
    plot_results(simulation_df, args.output)

if __name__ == "__main__":
    main()