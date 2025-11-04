import pandas as pd
import argparse

def aggregate_traffic_by_type(csv_file_path):
    """
    Loads traffic data from a CSV and aggregates it into peering and transit totals.

    Args:
        csv_file_path (str): The path to the traffic data CSV file.

    Returns:
        A tuple containing the total peering traffic and total transit traffic in Gbps.
    """
    # Based on the provided link details, we can classify the destinations
    # in the CSV file as either peering or transit.
    
    # Note: 'gttce' and 'gttzh' from the CSV are considered variations of 'gtt'.
    TRANSIT_PROVIDERS = [
        'cogent',
        'gttce',
        'gttzh',
        'level3',
        'lumen',
        'telia',
        'geant',
    ]

    PEERING_PROVIDERS = [
        'cern',
        'interxion',
        'swissix',
        'amsix',
        'belwue2',
        'cixp',
        'decix',
        'tix'
    ]

    try:
        # Load the CSV file into a pandas DataFrame
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
        return None, None
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        return None, None

    # Initialize totals
    total_peering_traffic = 0.0
    total_transit_traffic = 0.0
    unclassified_providers = []

    # Iterate over each row in the DataFrame to classify and sum the traffic
    for index, row in df.iterrows():
        provider = row['to']
        traffic_out = row['traffic_out_gbps']

        if provider in TRANSIT_PROVIDERS:
            total_transit_traffic += traffic_out
        elif provider in PEERING_PROVIDERS:
            total_peering_traffic += traffic_out
        else:
            # Keep track of any providers in the CSV that we haven't classified
            unclassified_providers.append(provider)

    if unclassified_providers:
        print(f"Warning: The following providers from the CSV were not classified: {', '.join(unclassified_providers)}")

    return total_peering_traffic, total_transit_traffic

def main():
    """Main function to parse arguments and run the aggregation."""
    parser = argparse.ArgumentParser(description="Aggregate traffic into peering and transit totals from a CSV file.")
    parser.add_argument("csv_file", help="Path to the traffic data CSV file.")
    
    args = parser.parse_args()

    peering_total, transit_total = aggregate_traffic_by_type(args.csv_file)

    if peering_total is not None and transit_total is not None:
        # Print the results in a formatted way
        print("\n--- Traffic Aggregation Summary ---")
        print(f"Total Peering Traffic: {peering_total:.2f} Gbps")
        print(f"Total Transit Traffic: {transit_total:.2f} Gbps")
        print("---------------------------------\n")

if __name__ == "__main__":
    main()