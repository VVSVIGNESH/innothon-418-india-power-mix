#!/usr/bin/env bash
# Reproduces every output on a CPU. Run from the repo root. Total about 10 minutes (Step 2 draws take ~8 min).
set -euo pipefail
python3 -I forecast_2047.py --data-dir . --out-dir outputs     # Step 1: forecast, scenarios, sensitivities
python3 -I step2_base_mix.py                                    # Step 2 base mix FY2025-26 (six sources by region)
python3 -I step2_mix_model.py                                   # Step 2 mix model, 4 scenarios x 6 variants x 150 draws
python3 -I step2_six_vectors.py                                 # fold 'other RE' into the six required sources
python3 -I step2_policy_check.py                                # grid CO2 intensity vs net-zero paths
python3 -I build_dashboard_data.py                              # data files for the dashboard in docs/
