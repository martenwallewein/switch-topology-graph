# !/bin/bash

python3 scenario_gen_with_pp.py test-graph.json test.csv -o scenario_small_default.json
python3 scenario_gen_with_pp.py test-graph.json test.csv -o scenario_small_peering.json --prefer_peering