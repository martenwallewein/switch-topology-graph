# Tooling to generate a graph out of SWITCHs online metrics
Metrics are observed from: https://network.switch.ch/pub/

## Building the graph

To generate internal, international and connectivity graphs, run the following scripts:

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python3 connectivity.py # Fetch from https://network.switch.ch/pub/graphs/
python3 international_map.py # Fetch from https://network.switch.ch/pub/international-map/
python3 swiss_map.py # Fetch from https://network.switch.ch/pub/swiss-map/
```

This generates three subgraphs:
(1) switch_connectivity.json
(2) switch_international.json
(3) switch_swiss.json

Since they are not directly related, we can aggregate the full graph using LLMs. Pase the content from `prompt-full-graph.txt`, replace the content of (1), (2) and (3) and let AI aggregate the full graph.

## Plotting the graph
Install graphviz:

*   **On macOS (using Homebrew):**
    ```bash
    brew install graphviz
    ```

*   **On Debian/Ubuntu:**
    ```bash
    sudo apt-get update
    sudo apt-get install graphviz libgraphviz-dev pkg-config
    ```

*   **On Red Hat/Fedora/CentOS:**
    ```bash
    sudo yum install graphviz-devel
    ```
*   **On Windows:**
    1.  Download an installer from the official [Graphviz download page](https://graphviz.org/download/).
    2.  Run the installer.
    3.  **Crucially**, add the Graphviz `bin` directory to your system's PATH environment variable. The default location is usually `C:\Program Files\Graphviz\bin`.
    
Install requirements:
```sh
pip install -r requirements.txt
```

Run draw script:
```sh
python3 draw_graph.py
```
