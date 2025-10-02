import requests
import json
from bs4 import BeautifulSoup
import re

def generate_swiss_network_json(url):
    """
    Fetches and parses the Swiss network weathermap HTML from a URL,
    extracts the complete topology by resolving name aliases, and returns
    it as a JSON formatted string.

    Args:
        url (str): The URL of the Swiss network weathermap page.

    Returns:
        str: A JSON string representing the network graph.
             Returns an empty JSON object if an error occurs.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
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
    
    node_ids = set()
    node_short_name_to_id_map = {}

    # This alias map resolves the mismatch between link names and node caption names
    alias_map = {
        'ez': 'ethz',
        'ce': 'cern',
        'lug': 'cscs',
        'zh': 'uzh',
        'be': 'unibe',
        'ba': 'unibas',
        'ls': 'unil',
        'el': 'epfl',
        'ge': 'unige',
        'fr': 'unifr',
        'bi': 'biel',
        'ne': 'unine',
        'sg': 'unisg',
        'ff': 'frauenfeld',
        'ix': 'equinix',
        'del': 'hes-so headoffice',
        'yv': 'heig-vd',
        'gl': 'clinique valmont',
        'si': 'sion',
        'vi': 'sbb visp',
        'cr': 'fhgr chur',
        'kl': 'meteoSchweiz', # Inferred from context
        'gr': 'hft-so', # Inferred from context
        'ma': 'supsi',
        'my': 'rero',
        'bl': 'lrg',
        'avp': 'hes-so//master',
        'c1': 'chuv',
        'c2': 'chuv', # CHUV has two different nodes
        'hep': 'hep-vd',
        'jfj': 'hsfjg',
        'ra': 'ost-rj',
        'li': 'unili',
    }

    # 1. First pass: Extract all nodes and build the primary name-to-ID map
    for area in weathermap.find_all('area', id=re.compile(r'^NODE')):
        node_id = area['id'].split(':')[1]
        if node_id not in node_ids:
            mouseover_text = area.get('onmouseover', '')
            match = re.search(r"overlib\('([^']*)',.+CAPTION,'([^']*)'\);", mouseover_text)
            if match:
                node_label = match.group(1).strip()
                node_short_name = match.group(2).strip()
                
                nodes.append({"id": node_id, "label": node_label, "short_name": node_short_name})
                node_ids.add(node_id)
                node_short_name_to_id_map[node_short_name.lower()] = node_id

    # 2. Second pass: Extract links, using the alias map to find the correct nodes
    processed_links = set()
    for area in weathermap.find_all('area', id=re.compile(r'^LINK')):
        link_id = area['id'].split(':')[1]
        if link_id in processed_links:
            continue
        
        mouseover_text = area.get('onmouseover', '')
        caption_match = re.search(r"CAPTION,'History for ([^']*)'", mouseover_text)
        if not caption_match:
            continue
            
        link_name = caption_match.group(1)
        parts = link_name.split('-', 1)
        if len(parts) != 2:
            continue
            
        from_short, to_short = parts[0].lower(), parts[1].lower()
        
        # Use the alias map to find the canonical short name, otherwise use the name itself
        from_lookup = alias_map.get(from_short, from_short)
        to_lookup = alias_map.get(to_short, to_short)
        
        from_node_id = node_short_name_to_id_map.get(from_lookup)
        to_node_id = node_short_name_to_id_map.get(to_lookup)

        if not from_node_id or not to_node_id:
            # If a connection still can't be found, print a warning and skip
            # print(f"Warning: Could not find nodes for link '{link_name}'. Looked for '{from_lookup}' and '{to_lookup}'.")
            continue
            
        # Extract traffic and capacity details
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
    URL = "https://network.switch.ch/pub/swiss-map/"
    json_output = generate_swiss_network_json(URL)
    with open("switch_swiss.json", "w") as f:
        f.write(json_output)