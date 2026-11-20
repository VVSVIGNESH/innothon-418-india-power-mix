# WHY THIS FILE EXISTS: the challenge asks for six sources (coal, hydro, solar, wind, nuclear, natural gas), but the model also
# tracks a small "other renewables" line (biomass, bagasse, waste, about 0.4% of generation) so that regional totals still add up.
# Here that line is spread pro rata over the six, so every region-year still sums to its Step 1 total. Also writes the P10/P50/P90
# ranges and the regional indicator table that the dashboard reads.
# Inputs: outputs/step2_mix_yearly_central.csv, outputs/step2_mix_yearly_ranges.csv
# Outputs: outputs/step2_mix_six_vectors_central.csv, ..._ranges.csv, step2_regional_strategy_indicators.csv
# Re-cuts the Step 2 outputs into the hackathon's SIX vectors (coal, hydro, solar, wind, nuclear, natural gas).
# 'Other RE' (biomass, bagasse, waste: ~0.4% of generation) is not one of the six, so it is shared out pro rata to the six.
import pandas as pd, numpy as np
SIX = ["coal", "hydro", "solar", "wind", "nuclear", "gas"]
c = pd.read_csv("outputs/step2_mix_yearly_central.csv"); k = ["scenario", "variant", "region", "year"]
tot = c.groupby(k).twh.transform("sum"); oth = c[c.source == "other_re"].set_index(k).twh
c["oth"] = c.set_index(k).index.map(oth)
c = c[c.source.isin(SIX)].copy(); c["twh"] = c.twh * tot[c.index] / (tot[c.index] - c.oth)
c["share_pct"] = 100 * c.twh / c.groupby(k).twh.transform("sum")
c.drop(columns="oth").round(3).to_csv("outputs/step2_mix_six_vectors_central.csv", index=False)
r = pd.read_csv("outputs/step2_mix_yearly_ranges.csv")
o = r[r.source == "other_re"].set_index(k).share_p50; r["o"] = r.set_index(k).index.map(o)
r = r[r.source.isin(SIX)].copy(); f = 100 / (100 - r.o)
for col in ["share_p10", "share_p50", "share_p90", "twh_p10", "twh_p50", "twh_p90"]: r[col] = r[col] * f
r.drop(columns="o").round(3).to_csv("outputs/step2_mix_six_vectors_ranges.csv", index=False)
# regional strategy table: indicators + 2047 main mix
cl = pd.read_csv("region_climate_land.csv", index_col=0); ri = pd.read_csv("resource_indicators_state.csv")
g = ri.groupby("region")[["hydro_exploitable_mw_cea_2017_23", "coal_resource_mt_moc_2025", "wind_120m_gw_niwe"]].sum(min_count=1)
d = c[(c.scenario == "Main (all uncertainty)") & (c.variant.str.startswith("Main")) & (c.year == 2047)].pivot(index="region", columns="source", values="share_pct")[SIX].round(1)
d0 = c[(c.scenario == "Main (all uncertainty)") & (c.variant.str.startswith("Main")) & (c.year == 2027)].pivot(index="region", columns="source", values="share_pct")[SIX].round(1)
out = d.add_suffix("_2047_pct").join(d0.add_suffix("_2027_pct")).join(cl[["ghi_kwh_m2_day", "area_per_capita_ha"]]).join(g)
out.to_csv("outputs/step2_regional_strategy_indicators.csv"); print(out.drop(index="India", errors="ignore").T.to_string())
