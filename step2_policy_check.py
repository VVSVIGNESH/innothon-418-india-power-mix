# WHY THIS FILE EXISTS: the Step 2 variants claim to follow policy (net-zero 2070, NEP/NGAP wind+solar plans).
# Instead of just saying so, this script tests it: for every scenario/variant/year it computes the grid's direct CO2
# intensity (t per MWh, from coal and gas generation only) and compares it with two straight-from-today paths to zero in 2070
# (a straight line, and a front-loaded one). It also reports wind+solar energy and the yearly change in coal.
# Input: outputs/step2_mix_yearly_central.csv   Output: outputs/step2_policy_check.csv (read by the dashboard's policy check chart)
# Checks every Step 2 variant against the policy levers (generation-based). Writes outputs/step2_policy_check.csv
import pandas as pd, numpy as np
c = pd.read_csv("outputs/step2_mix_yearly_central.csv"); c = c[c.region == "India"]
EF = {"coal": 0.95, "gas": 0.45}
p = c.pivot_table(index=["scenario", "variant", "year"], columns="source", values="twh").reset_index()
p["total"] = p[["coal", "gas", "nuclear", "hydro", "solar", "wind", "other_re"]].sum(axis=1)
p["grid_co2_t_per_mwh"] = (p.coal * EF["coal"] + p.gas * EF["gas"]) / p.total
EI0 = 0.668; x = (p.year - 2026) / 44
p["path_linear_to_2070"] = EI0 * (1 - x); p["path_front_loaded_netzero"] = EI0 * (1 - x) ** 1.5
p["meets_linear"] = p.grid_co2_t_per_mwh <= p.path_linear_to_2070 + 1e-9
p["meets_front_loaded"] = p.grid_co2_t_per_mwh <= p.path_front_loaded_netzero + 1e-9
p["wind_plus_solar_twh"] = p.solar + p.wind
p["coal_yoy_pct"] = p.groupby(["scenario", "variant"]).coal.pct_change() * 100
p.round(3).to_csv("outputs/step2_policy_check.csv", index=False)
for scn in p.scenario.unique():
    print("\n==", scn)
    for v, d in p[p.scenario == scn].groupby("variant"):
        g = d.set_index("year")
        print(f"{v[:36]:<36} EI2032 {g.grid_co2_t_per_mwh[2032]:.2f} EI2047 {g.grid_co2_t_per_mwh[2047]:.2f} | linear-2070 met in {int(g.meets_linear.sum())}/21 yrs, front-loaded {int(g.meets_front_loaded.sum())}/21 | "
              f"W+S 2032 {g.wind_plus_solar_twh[2032]:.0f} (plan 887) 2036 {g.wind_plus_solar_twh[2036]:.0f} (plan 1388) | nuc2032 {g.nuclear[2032]:.0f} | coal 2047 {g.coal[2047]:.0f} TWh, peak {int(g.coal.idxmax())}")
