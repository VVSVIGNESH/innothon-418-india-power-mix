# Builds docs/data.json and docs/consts.json (the dashboard's data) from outputs/*.csv and the model modules.
# Run from the repo root:  python3 -I build_dashboard_data.py
import sys, json
from pathlib import Path
sys.path.insert(0, ".")
import pandas as pd
import step2_mix_model as m          # reads CSVs from the current folder; the main block does not run on import
import forecast_2047 as f
Y = list(range(2027, 2048)); OUT = Path("docs"); OUT.mkdir(exist_ok=True)
R = lambda x, n=1: [round(float(v), n) for v in x]
nn = lambda x: [None if pd.isna(v) else round(float(v), 2) for v in x]
c = pd.read_csv("outputs/step2_mix_six_vectors_central.csv"); r = pd.read_csv("outputs/step2_mix_six_vectors_ranges.csv")
fc = pd.read_csv("outputs/forecast_yearly_all.csv"); s = pd.read_csv("outputs/forecast_yearly_sensitivity.csv")
pc = pd.read_csv("outputs/step2_policy_check.csv"); ind = pd.read_csv("outputs/step2_regional_strategy_indicators.csv"); lev = pd.read_csv("outputs/step2_policy_levers.csv")
mix, rng, F, pol = {}, {}, {}, {}
for (sc, va, rg, so), d in c.groupby(["scenario", "variant", "region", "source"]):
    d = d.sort_values("year"); mix.setdefault(sc, {}).setdefault(va, {}).setdefault(rg, {})[so] = R(d.twh)
for (sc, va, rg, so), d in r.groupby(["scenario", "variant", "region", "source"]):
    d = d.sort_values("year")
    rng.setdefault(sc, {}).setdefault(va, {}).setdefault(rg, {})[so] = {"lo": R(d.twh_p10), "hi": R(d.twh_p90), "slo": R(d.share_p10), "shi": R(d.share_p90)}
for (sc, rg), d in fc.groupby(["scenario", "region"]):
    d = d.sort_values("year"); F.setdefault(sc, {})[rg] = {"p10": R(d.p10_twh), "p50": R(d.p50_twh), "p90": R(d.p90_twh), "g": nn(d["p50_yoy_growth_%"])}
sens = {k: R(d.sort_values("year").india_p50_twh) for k, d in s.groupby("case")}
for (sc, va), d in pc.groupby(["scenario", "variant"]):
    d = d.sort_values("year")
    pol.setdefault(sc, {})[va] = {"co2": R(d.grid_co2_t_per_mwh, 3), "lin": R(d.path_linear_to_2070, 3), "front": R(d.path_front_loaded_netzero, 3), "vre": R(d.wind_plus_solar_twh), "coalg": nn(d.coal_yoy_pct)}
data = {"years": Y, "mix": mix, "rng": rng, "fc": F, "sens": sens, "pol": pol, "ind": [{k: (None if pd.isna(v) else v) for k, v in row.items()} for row in ind.to_dict("records")], "lev": lev.to_dict("records")}
json.dump(data, open(OUT / "data.json", "w"), separators=(",", ":"))

# constants for the in-browser model lab (ports of forecast_2047.py and step2_mix_model.py)
socio = f.read_socioeconomic(Path("renewable_energy_dataset.csv"))
gen = f.read_generation(Path("regional_generation_conventional_gwh.csv"), Path("regional_generation_re_mu.csv"))
anchor = gen[gen.fy == "2025-26"].set_index("region").gen_gwh.reindex(f.REGIONS).to_numpy()
dpop, delta = f.regional_rates(socio)
urb = pd.read_csv("outputs/urban_share_by_region_2011.csv").set_index("region")
pop24 = socio[socio.Year == 2024].set_index("region")["pop"].reindex(f.REGIONS) / 1e6
K = {"s1": {"regions": f.REGIONS, "anchor": anchor.tolist(), "dpop": dpop.tolist(), "delta": delta.tolist(), "beta": float(f.longrun_beta(socio)),
            "betaSd": f.BETA_SD, "betaClip": list(f.BETA_CLIP), "gdpStart": list(f.GDP_START), "gdpEnd": list(f.GDP_END), "gdpClip": list(f.GDP_CLIP),
            "fade": list(f.ELASTICITY_FADE), "uplift": list(f.ELECTRIFICATION_UPLIFT), "pop47": list(f.POP_2047_RANGE_BN), "pop25": f.POP_2025_BN,
            "scen": {k: [list(v[0]), list(v[1])] for k, v in f.SCENARIOS.items()},
            "urb": urb.urban_share.reindex(f.REGIONS).tolist(), "pop24": pop24.tolist(), "urbNat": float(urb.Urban.sum() / urb.Total.sum())},
     "s2": {"SRC": m.SRC, "G0": m.G0.tolist(), "h5": m.h5.tolist(), "R": m.R.tolist(), "E": m.E.tolist(), "Sec": m.Sec.tolist(), "I": m.I.tolist(), "LAND": m.LAND.tolist(),
            "costMid": [m.cost_mid[x] for x in m.SRC], "EF": [m.EF[x] for x in m.SRC], "capHyd": m.cap_hyd.tolist(), "windPot": m.wind_pot.tolist(),
            "Wmean": m.W_MEAN.tolist(), "EI0": float(m.EI0), "POL2032": float(m.POL_2032), "POL2036": float(m.POL_2036), "VRE0": float(m.VRE0),
            "PAR": m.PAR_CENTRAL, "VAR": m.VAR, "nucMain": m.NUC_MAIN_SHARE, "nucAmb": m.NUC_AMBITION_GWH, "hydroCF": m.HYDRO_CF, "windCF": m.WIND_CF,
            "windUsable": m.WIND_USABLE, "solCF": m.SOLAR_CF, "solUsable": m.SOLAR_USABLE, "solNat": m.SOLAR_NAT_GWP, "TEMP": m.TEMP, "neSol": m.NE_SOLAR_MAX_SHARE}}
json.dump(K, open(OUT / "consts.json", "w"))
print("wrote docs/data.json and docs/consts.json")
