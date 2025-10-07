#!/bin/bash
set -e 
TICKS=$(date "+%s")
mkdir -p /home/marten/switch-topology-graph/data/switch_connectivity
mkdir -p /home/marten/switch-topology-graph/data/switch_international
mkdir -p /home/marten/switch-topology-graph/data/switch_swiss

cd /home/marten/switch-topology-graph
source venv/bin/activate

python3 connectivity.py # Fetch from https://network.switch.ch/pub/graphs/
python3 international_map.py # Fetch from https://network.switch.ch/pub/international-map/
python3 swiss_map.py # Fetch from https://network.switch.ch/pub/swiss-map/

for file in switch_connectivity.json switch_international.json switch_swiss.json; do
    if [ ! -s $file ]; then
        continue
    fi

    basename=$(basename $file .json)
    mv "$file" "data/$basename/$TICKS.json"

    # $MC cp --quiet --attr "X-Amz-Meta-Mtime=$TICKS" "$file" "$BUCKET/$basename/$TICKS.json" > /dev/null
done
