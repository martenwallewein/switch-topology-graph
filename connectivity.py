import requests
import json
from bs4 import BeautifulSoup
import re

def generate_graph_from_html(url):
    """
    Fetches and parses HTML from a URL to extract network connectivity
    data and returns it as a JSON graph.

    Args:
        url (str): The URL of the traffic graphs page.

    Returns:
        str: A JSON string representing the network graph.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return json.dumps({})

    soup = BeautifulSoup(html_content, 'html.parser')
    
    nodes = [{"id": "switch", "label": "SWITCH", "type": "internal"}]
    edges = []
    peer_nodes = set()
    edge_counter = 0

    # The content is within <dl> tags in the main column
    description_lists = soup.select('div.col-xs-12 dl')

    for dl in description_lists:
        for dt in dl.find_all('dt'):
            entity_name = dt.get_text(strip=True)
            dd = dt.find_next_sibling('dd')

            if not entity_name or not dd:
                continue

            details_text = dd.get_text(strip=True).replace('\xa0', ' ')

            # --- Patterns to extract link information from the <dd> text ---
            multi_link_match = re.search(r'(\d+x)\s+([\d\s]+[GT]b/s)', details_text, re.IGNORECASE)
            plus_link_match = re.search(r'((?:\d+\s+[GT]b/s\s*\+\s*)+(\d+\s+[GT]b/s))', details_text, re.IGNORECASE)
            single_link_match = re.search(r'(\d+\s+[GT]b/s)', details_text, re.IGNORECASE)

            capacities = []
            
            if multi_link_match:
                count = int(multi_link_match.group(1).replace('x', ''))
                capacity_str = multi_link_match.group(2).strip()
                capacities = [capacity_str] * count
            elif plus_link_match:
                capacities = [c.strip() for c in re.findall(r'\d+\s+[GT]b/s', plus_link_match.group(1))]
            elif single_link_match:
                capacities = [single_link_match.group(1).strip()]
                
            if not capacities:
                continue

            # Add peer node if it's new
            if entity_name not in peer_nodes:
                nodes.append({"id": entity_name.lower(), "label": entity_name, "type": "external"})
                peer_nodes.add(entity_name)
                
            # Extract locations from parentheses
            location_match = re.search(r'\(([^)]+)\)', details_text)
            locations = []
            if location_match:
                locations = [loc.strip().replace('1x ', '').replace('at ', '') for loc in location_match.group(1).split(',')]

            # Create edges for each link
            for i, capacity in enumerate(capacities):
                edge_counter += 1
                # Distribute locations to links if available
                location = locations[i] if i < len(locations) else (locations[0] if locations else "N/A")
                edges.append({
                    "id": f"L{edge_counter}",
                    "from": "switch",
                    "to": entity_name.lower(),
                    "capacity": capacity,
                    "location": location.split(';')[0].strip() # Clean up homepage info
                })

    graph = {"nodes": nodes, "edges": edges}
    return json.dumps(graph, indent=4)

if __name__ == '__main__':
    URL = "https://network.switch.ch/pub/graphs/"
    json_output = generate_graph_from_html(URL)
    # store the output in a file
    with open("switch_connectivity.json", "w") as f:
        f.write(json_output)