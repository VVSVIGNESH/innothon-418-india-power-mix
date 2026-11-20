# STEP 2 / part A: FY2025-26 base mix per CEA region, in the hackathon's six sources (+ a small 'other RE' line).
# WHY: the hackathon asks for coal, hydro, solar, wind, nuclear, natural gas. Our step-1 files hold thermal as one number
# and hydro in two places (large hydro in NPP data, small hydro in CEA RE data), so we re-cut them here.
# Everything is ENERGY GENERATED (GWh) - no capacity, no consumption.
import pandas as pd
conv = pd.read_csv("regional_generation_conventional_gwh.csv"); re_ = pd.read_csv("regional_generation_re_mu.csv")
gas = pd.read_csv("gas_stations_fy2025_26.csv")
fy = "2025-26"
c = conv[conv.fy == fy].set_index("region"); r = re_[re_.fy == fy].set_index("region")
g = gas.groupby("region").gen_gwh_fy2025_26.sum().reindex(c.index).fillna(0)
# NPP 'thermal' = coal + lignite + gas + diesel.  Gas comes from NPP station reports 12-14 (gas & liquid fuel);
# coal/lignite = thermal - gas.  Diesel is not separated (it is a few hundred GWh nationally) and stays inside 'coal'.
out = pd.DataFrame({
    "coal_gwh": c.thermal_gwh - g,
    "gas_gwh": g,
    "nuclear_gwh": c.nuclear_gwh,
    "hydro_gwh": c.hydro_gwh + r.small_hydro_mu,          # large (NPP) + small (CEA RE)
    "solar_gwh": r.solar_mu,
    "wind_gwh": r.wind_mu,
    "other_re_gwh": r.biomass_mu + r.bagasse_mu + r.other_re_mu,
}).loc[["North", "West", "South", "East", "NorthEast"]]
out["total_gwh"] = out.sum(axis=1)
out.loc["India"] = out.sum()
out.round(1).to_csv("outputs/base_mix_fy2025_26_gwh.csv")
share = out.drop(columns="total_gwh").div(out.total_gwh, axis=0) * 100
print((out / 1000).round(1).to_string()); print("\nShares %:"); print(share.round(1).to_string())
print("\nGas national check vs NPP gas total 26,026.36 GWh:", round(g.sum(), 2))
