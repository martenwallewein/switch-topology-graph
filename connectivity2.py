import requests
import json
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

def get_traffic_metrics(url):
    """
    Fetches and parses a detail page to extract traffic metrics.

    Args:
        url (str): The URL of the detail page.

    Returns:
        dict: A dictionary containing 'avg_in' and 'avg_out' traffic metrics.
    """
    metrics = {"avg_in": "N/A", "avg_out": "N/A"}
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all table cells, as they contain the metric labels and values
        table_cells = soup.find_all('td')
        for cell in table_cells:
            text = cell.get_text(strip=True)
            
            # Use regex to find and extract the metrics
            in_match = re.search(r'Average bits in:\s*([\d\.]+\s+[TGMK]?bits/sec)', text, re.IGNORECASE)
            out_match = re.search(r'Average bits out:\s*([\d\.]+\s+[TGMK]?bits/sec)', text, re.IGNORECASE)

            if in_match:
                metrics["avg_in"] = in_match.group(1)
            if out_match:
                metrics["avg_out"] = out_match.group(1)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching detail URL {url}: {e}")
    
    return metrics

def generate_graph_from_html(url):
    """
    Fetches and parses HTML from a URL to extract network connectivity
    data, crawls sub-pages for more metrics, and returns it as a JSON graph.

    Args:
        url (str): The URL of the main traffic graphs page.

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

    description_lists = soup.select('div.col-xs-12 dl')

    for dl in description_lists:
        for dt in dl.find_all('dt'):
            entity_name = dt.get_text(strip=True)
            dd = dt.find_next_sibling('dd')
            link_tag = dt.find('a')

            if not entity_name or not dd:
                continue
                
            # Get traffic metrics from the linked page
            traffic_metrics = {"avg_in": "N/A", "avg_out": "N/A"}
            if link_tag and link_tag.has_attr('href'):
                detail_url = urljoin(url, link_tag['href'])
                traffic_metrics = get_traffic_metrics(detail_url)

            details_text = dd.get_text(strip=True).replace('\xa0', ' ')

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

            if entity_name not in peer_nodes:
                nodes.append({"id": entity_name.lower(), "label": entity_name, "type": "external"})
                peer_nodes.add(entity_name)
                
            location_match = re.search(r'\(([^)]+)\)', details_text)
            locations = []
            if location_match:
                locations = [loc.strip().replace('1x ', '').replace('at ', '') for loc in location_match.group(1).split(',')]

            for i, capacity in enumerate(capacities):
                edge_counter += 1
                location = locations[i] if i < len(locations) else (locations[0] if locations else "N/A")
                edges.append({
                    "id": f"L{edge_counter}",
                    "from": "switch",
                    "to": entity_name.lower(),
                    "capacity": capacity,
                    "location": location.split(';')[0].strip(),
                    "avg_in": traffic_metrics.get("avg_in", "N/A"),
                    "avg_out": traffic_metrics.get("avg_out", "N/A")
                })

    graph = {"nodes": nodes, "edges": edges}
    return json.dumps(graph, indent=4)

if __name__ == '__main__':
    URL = "https://network.switch.ch/pub/graphs/"
    json_output = generate_graph_from_html(URL)
    with open("switch_connectivity_extended.json", "w") as f:
        f.write(json_output)

    print("Successfully generated extended connectivity data in 'switch_connectivity_extended.json'")