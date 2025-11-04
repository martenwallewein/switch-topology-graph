import json
import subprocess
import sys
import ipaddress
import os
import time

def run_traceroute_script(ip_address):
    """
    Executes the traceroute_parser.py script for a given IP address
    and captures its output.

    Args:
        ip_address (str): The destination IP address for the traceroute.

    Returns:
        str: The traceroute result from the script's stdout, or an error message.
    """
    try:
        command = ['python3', 'get_traceroute_result.py', ip_address]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return "Error: 'traceroute_parser.py' not found. Ensure it is in the same directory."
    except subprocess.CalledProcessError as e:
        return f"Error executing traceroute script for {ip_address}:\n{e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred while tracing {ip_address}: {e}"

def main():
    """
    Main function to load peer data, run traceroutes, and append each result
    as a new line to a .jsonl output file.
    """
    if len(sys.argv) != 2 or sys.argv[1].lower() not in ['v4', 'v6']:
        print("Usage: python process_peers.py <v4|v6>")
        sys.exit(1)

    ip_version_arg = sys.argv[1].lower()
    ip_address_key = 'ipaddr4' if ip_version_arg == 'v4' else 'ipaddr6'
    input_filename = 'ip_prefixes.json'
    output_filename = f'traceroute_results_{ip_version_arg}.jsonl'

    # Load the input JSON file
    try:
        with open(input_filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{input_filename}'. Please check its format.")
        sys.exit(1)

    # If the output file already exists, you might want to remove it to start fresh.
    if os.path.exists(output_filename):
        print(f"Output file '{output_filename}' already exists. Removing it to start fresh.")
        os.remove(output_filename)

    print(f"Processing traceroutes for {ip_version_arg.upper()} addresses...")
    print(f"Results will be appended to '{output_filename}' as they are generated.")

    # Open the output file in append mode.
    with open(output_filename, 'a') as outfile:
        # Iterate through each provider and their network entries
        for provider, entries in data.items():
            print(f"\nProvider: {provider}")
            for entry in entries:
                if ip_address_key in entry and entry[ip_address_key]:
                    try:
                        network = ipaddress.ip_network(entry[ip_address_key], strict=False)
                        ip_to_trace = str(network.network_address)
                    except ValueError:
                        print(f"  Skipping invalid IP format: {entry[ip_address_key]}")
                        continue

                    print(f"  Tracing to {ip_to_trace} for ASN {entry.get('asn', 'N/A')}...")

                    traceroute_result = run_traceroute_script(ip_to_trace)

                    # Create a new dictionary for the result
                    result_entry = entry.copy()
                    result_entry['provider'] = provider # Add provider info for context
                    result_entry['traceroute_result'] = traceroute_result

                    # Write the result as a single line (JSON object) to the file
                    outfile.write(json.dumps(result_entry) + '\n')
                    outfile.flush() # Ensure it's written to disk immediately
                    print(f"  Result for {ip_to_trace} saved.")
                else:
                    print(f"  Skipping entry for ASN {entry.get('asn', 'N/A')} (no '{ip_address_key}' found).")
                
                time.sleep(30)  # To avoid overwhelming the traceroute service

    print(f"\nProcessing complete. All results saved in '{output_filename}'.")

if __name__ == "__main__":
    main()