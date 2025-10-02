import requests
import json
from bs4 import BeautifulSoup
import re

def generate_network_json(url):
    """
    Fetches and parses the network weathermap HTML from a URL,
    extracts the topology including internal and external nodes, and
    returns it as a JSON formatted string.

    Args:
        url (str): The URL of the network weathermap page.

    Returns:
        str: A JSON string representing the network graph.
             Returns an empty JSON object if an error occurs.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        html_content = response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return json.dumps({})

    soup = BeautifulSoup(html_content, 'html.parser')
    weathermap = soup.find('map', {'id': 'weathermap_imap'})

    if not weathermap:
        return json.dumps({"nodes": [], "edges": []})

    nodes = []
    edges = []
    
    # --- Helper dictionaries to track nodes ---
    # To avoid adding duplicate nodes
    all_node_ids = set() 
    # Maps short names like 'ce' or 'ix' to their unique ID like 'N122'
    internal_node_short_name_map = {}

    # 1. First pass: Extract all internal nodes
    for area in weathermap.find_all('area', id=re.compile(r'^NODE')):
        node_id = area['id'].split(':')[1]
        if node_id not in all_node_ids:
            mouseover_text = area.get('onmouseover', '')
            match = re.search(r"overlib\('([^']*)',.+CAPTION,'([^']*)'\);", mouseover_text)
            if match:
                node_label = match.group(1).strip()
                node_short_name = match.group(2).strip()
                
                nodes.append({"id": node_id, "label": node_label, "type": "internal"})
                all_node_ids.add(node_id)
                internal_node_short_name_map[node_short_name] = node_id

    # 2. Second pass: Extract links, infer connections, and add external nodes
    processed_links = set() # To avoid processing paired link areas twice
    for area in weathermap.find_all('area', id=re.compile(r'^LINK')):
        link_id = area['id'].split(':')[1]
        if link_id in processed_links:
            continue
        
        mouseover_text = area.get('onmouseover', '')
        
        # Extract link name to determine connections
        caption_match = re.search(r"CAPTION,'History for ([^']*)'", mouseover_text)
        if not caption_match:
            continue
            
        link_name = caption_match.group(1)
        # e.g., 'ce-cern' splits into ['ce', 'cern']
        parts = link_name.split('-', 1)
        if len(parts) != 2:
            continue
            
        internal_short_name, external_name = parts
        
        # Find the internal node ID from our map
        from_node_id = internal_node_short_name_map.get(internal_short_name)
        if not from_node_id:
            continue

        # The external node's ID will be its name
        to_node_id = external_name
        
        # Add the external node to the nodes list if it's new
        if to_node_id not in all_node_ids:
            nodes.append({"id": to_node_id, "label": to_node_id, "type": "external"})
            all_node_ids.add(to_node_id)
            
        # Extract traffic and capacity details for the edge
        traffic_in = "N/A"
        traffic_out = "N/A"
        link_capacity = "N/A"

        in_out_match = re.search(r'in:([\d.]+\w+)\s+out:([\d.]+\w+)', mouseover_text)
        if in_out_match:
            traffic_in = in_out_match.group(1)
            traffic_out = in_out_match.group(2)

        capacity_match = re.search(r'Linkcapacity:([\d.]+\w+)', mouseover_text)
        if capacity_match:
            link_capacity = capacity_match.group(1)
            
        edges.append({
            "id": link_id,
            "from": from_node_id,
            "to": to_node_id,
            "traffic_in": traffic_in,
            "traffic_out": traffic_out,
            "link_capacity": link_capacity
        })
        processed_links.add(link_id)

    graph = {"nodes": nodes, "edges": edges}
    return json.dumps(graph, indent=4)

if __name__ == '__main__':
    URL = "https://network.switch.ch/pub/international-map/"
    json_output = generate_network_json(URL)
    with open("switch_international.json", "w") as f:
        f.write(json_output)