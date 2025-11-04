import json
import time
import requests

API_KEY = "dGrDcZlC.Yt5sG8GHHvNgQzxdTVvIY3MQ29a7clGI"

def get_ip_prefixes(networks):
    """
    Retrieves and displays IPv4 and IPv6 prefixes for a list of networks
    using the PeeringDB API.

    Args:
        networks: A list of dictionaries, where each dictionary represents a network
                  with an 'id' and 'label'.
    """

    network_asns = {
        "geant": 21320, # 20965,
        "colt": 8220,
        "arelion": 1299,
        "cogent": 174,
        "gtt": 3257,
        "ams-ix": 1200,
        "cixp": 513,  # CIXP is operated by CERN
        "cernlight": 513, # Assuming CERNlight is part of CERN's network
        "de-cix": 6695,
        "equinix": 24115, # This is one of Equinix's ASNs, they have several
        "swissix": 42476,
        "cern": 513,
        "belw": 6893,
        "google": 15169,
        "microsoft": 8075,
        "belwü": 553,
        "amazon": 16509,
        "facebook": 32934,
        "akamai": 20940,
        "swisscom": 3303,
        "init7": 13030,
        "liberty global": 6830,
    }

    ip_prefixes = {}
    for network in networks:
        network_id = network.get("id", "").lower().replace("é", "e").replace("ü", "u")
        network_label = network.get("label")
        asn = network_asns.get(network_id)

        if not asn:
            print(f"--- {network_label} (ASN not found in our list) ---")
            continue

        print(f"--- {network_label} (AS{asn}) ---")

        
        try:
            response = requests.get(f"https://www.peeringdb.com/api/net?asn={asn}&depth=2", headers = {"Authorization": "Api-Key " + API_KEY})
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()

            if data.get("data"):
                net_data = data["data"][0]
                prefixes = net_data.get("netixlan_set", [])

                #ip_prefixes[network_id] = {
                #    "v4": [p for p in prefixes if p.get("ipaddr4")],
                #    "v6": [p for p in prefixes if p.get("ipaddr6")]
                #}
                ip_prefixes[network_id] = [p for p in prefixes]

                print("Got prefixes from PeeringDB: " + len(prefixes).__str__())
            else:
                print("  No prefix information found in PeeringDB.")

        except requests.exceptions.RequestException as e:
            print(f"  Error fetching data: {e}")
        except (KeyError, IndexError):
            print("  Could not parse prefix information from the API response.")
        print("-" * (len(network_label) + 10))
        time.sleep(1)  # To avoid hitting API rate limits

    # dump the collected prefixes into file
    with open("ip_prefixes.json", "w") as f:
        json.dump(ip_prefixes, f, indent=4)


if __name__ == "__main__":
    switch_connections = [
        {"id": "geant", "label": "GÉANT", "type": "external"},
        {"id": "colt", "label": "Colt", "type": "external"},
        {"id": "arelion", "label": "Arelion", "type": "external"},
        {"id": "cogent", "label": "Cogent", "type": "external"},
        {"id": "gtt", "label": "GTT", "type": "external"},
        {"id": "ams-ix", "label": "AMS-IX", "type": "external"},
        {"id": "cixp", "label": "CIXP", "type": "external"},
        {"id": "cernlight", "label": "CERNLight", "type": "external"},
        {"id": "de-cix", "label": "DE-CIX", "type": "external"},
        {"id": "equinix", "label": "Equinix", "type": "external"},
        {"id": "swissix", "label": "SwissIX", "type": "external"},
        {"id": "cern", "label": "CERN", "type": "external"},
        {"id": "belwü", "label": "BelWü", "type": "external"},
        {"id": "google", "label": "Google", "type": "external"},
        {"id": "microsoft", "label": "Microsoft", "type": "external"},
        {"id": "amazon", "label": "Amazon", "type": "external"},
        {"id": "facebook", "label": "Facebook", "type": "external"},
        {"id": "akamai", "label": "Akamai", "type": "external"},
        {"id": "swisscom", "label": "Swisscom", "type": "external"},
        {"id": "init7", "label": "Init7", "type": "external"},
        {"id": "liberty global", "label": "Liberty Global", "type": "external"},
    ]
    get_ip_prefixes(switch_connections)