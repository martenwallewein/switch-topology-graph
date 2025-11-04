import requests
from bs4 import BeautifulSoup
import sys

def get_traceroute_results(ip_address):
    """
    Fetches and parses the traceroute results from SWITCH's online tool.

    Args:
        ip_address (str): The destination IP address for the traceroute.

    Returns:
        str: The traceroute results as a string, or an error message if not found.
    """
    url = f"https://network.switch.ch/pub/tools/traceroute/?destination={ip_address}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        soup = BeautifulSoup(response.text, 'html.parser')

        # The traceroute results are within a <pre> tag with the class "indented"
        traceroute_pre = soup.find('pre', class_='indented')

        if traceroute_pre:
            return traceroute_pre.get_text()
        else:
            return "Could not find the traceroute results in the HTML response."

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python traceroute_parser.py <ip_address>")
        sys.exit(1)

    destination_ip = sys.argv[1]
    results = get_traceroute_results(destination_ip)
    print(results)