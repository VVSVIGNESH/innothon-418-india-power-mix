# STEP 2: region-specific generation mix for every year 2027-2047 (energy generated, TWh/GWh only).
# Run:  python3 -I step2_mix_model.py        (CPU only, ~1-2 minutes)
#
# HOW IT WORKS (plain words)
#  1. Step 1 gives each region's TOTAL generation each year (P10/P50/P90).  Step 2 only decides the SPLIT by source.
#  2. NATIONAL source paths: nuclear, hydro, gas and other-RE follow simple, bounded rules (history, 9% nuclear
#     statement, resource ceilings).  Solar+wind grow as fast as a feasibility ramp allows (they are the cheapest
#     new energy) and coal is the balancing source: whatever total generation is still missing.
#  3. REGIONAL split: every source's national energy is shared across regions with a six-factor score
#     (cost, resource, environment, security, infrastructure, policy).
#  4. A matrix-balancing step (RAS) forces two things at once: each region's sources add to that region's Step-1
#     total, and each source's regions add to its national path.  Resource ceilings are respected.
#  5. Uncertainty: 300 random draws vary demand (Step-1 P10-P90), the national rules and the score weights.
import numpy as np, pandas as pd
from pathlib import Path

RNG_SEED = 2047
N_DRAWS = 150
D = Path(".")
OUT = Path("outputs"); OUT.mkdir(exist_ok=True)
REG = ["North", "West", "South", "East", "NorthEast"]
SRC = ["coal", "gas", "nuclear", "hydro", "solar", "wind", "other_re"]
YEARS = list(range(2027, 2048))
K = {y: y - 2026 for y in YEARS}          # years after the FY2025-26 base

# ---------------------------------------------------------------- inputs (all generation-based) ----------------
base = pd.read_csv(D / "outputs/base_mix_fy2025_26_gwh.csv", index_col=0).loc[REG]
G0 = np.array([[base.loc[r, f"{s}_gwh"] for r in REG] for s in SRC])            # source x region, GWh, FY2025-26
tot = pd.read_csv(D / "outputs/forecast_yearly_all.csv")                         # Step-1 totals
res = pd.read_csv(D / "resource_indicators_state.csv")
conv = pd.read_csv(D / "regional_generation_conventional_gwh.csv"); rere = pd.read_csv(D / "regional_generation_re_mu.csv")

# normal-year hydro: 5-year mean (FY2021-22..FY2025-26) of large + small hydro, so one wet/dry year is not extrapolated.
h5 = (conv[conv.fy >= "2021-22"].groupby(["fy", "region"]).hydro_gwh.sum().unstack()
      + rere.set_index(["fy", "region"]).small_hydro_mu.unstack()).mean().reindex(REG).to_numpy()

# ---------------------------------------------------------------- physical / published constants ---------------
# Direct CO2 factors, t/MWh = IPCC 2006 default fuel factor / plant efficiency (coal 94.6 kg/GJ at ~34%; gas 56.1 at ~45%).
EF = {"coal": 0.95, "gas": 0.45, "nuclear": 0, "hydro": 0, "solar": 0, "wind": 0, "other_re": 0}
# Published cost points, Rs/kWh (low, high); 'A' = assumption because no public figure was retrieved.
COST = {"coal": (4.78, 6.0),     # Ember 2025: existing fleet avg 4.78, new plants ~6
        "gas": (6.0, 9.0),       # A: not retrieved
        "nuclear": (3.0, 5.92),  # KKNPP 1-2 Rs3.0-4.1, KKNPP 3-4 indicative Rs5.92 (press report of CERC/NPCIL figures)
        "hydro": (4.0, 6.0),     # Powerline 2025, new hydro levelised
        "solar": (2.48, 2.70),   # SECI/State auctions 2025 lowest bids (trade-press headlines)
        "wind": (2.7, 3.5),      # A: hybrid auctions 2.67-2.69 seen; standalone wind not retrieved
        "other_re": (5.0, 7.0)}  # A
VRE_FIRMING = 0.7   # Rs/kWh: solar-plus-storage 2.9-3.6 vs plain solar ~2.5 (Ember) -> storage/firming adder for solar and wind
cost_mid = {s: 0.5 * sum(COST[s]) + (VRE_FIRMING if s in ("solar", "wind") else 0) for s in SRC}

# ---------------------------------------------------------------- regional indicator tables ---------------------
def reg_sum(col):
    return res.groupby("region")[col].sum(min_count=1).reindex(REG)
coal_res = reg_sum("coal_resource_mt_moc_2025").fillna(0).to_numpy()
hyd_pot = reg_sum("hydro_exploitable_mw_cea_2017_23").fillna(0).to_numpy()
wind_pot = reg_sum("wind_120m_gw_niwe").fillna(0).to_numpy()
sol_pot = reg_sum("solar_gwp_nise_2025")
# Solar: NISE table only reached 7 states (North, West, South). East/NorthEast missing -> assumed at the lowest observed regional value.
sol_pot = sol_pot.fillna(sol_pot.min()).to_numpy()

def rel(x):  # region share of national potential, rescaled so the best region = 1
    x = np.asarray(x, float); return x / x.max() if x.max() > 0 else np.zeros_like(x)

# resource factor R[s, r] in 0..1
R = np.zeros((len(SRC), len(REG)))
R[SRC.index("coal")] = rel(coal_res)
R[SRC.index("hydro")] = rel(hyd_pot)
R[SRC.index("wind")] = rel(wind_pot)
cl = pd.read_csv(D / "region_climate_land.csv", index_col=0).loc[REG]         # Global Solar Atlas GHI (state mean) and Census-2011 land per person
ghi = cl.ghi_kwh_m2_day.to_numpy()
R[SRC.index("solar")] = 0.2 + 0.8 * (ghi - ghi.min()) / (ghi.max() - ghi.min())   # PHYSICAL solar resource: irradiance, no capacity units
R[SRC.index("gas")] = rel(G0[SRC.index("gas")])               # no gas-resource table: use existing gas-fleet presence
R[SRC.index("nuclear")] = np.array([0.6, 0.8, 0.8, 0.4, 0.0])  # A: site suitability (coastal/river water, seismic zone); NorthEast = 0 (seismic zone V)
R[SRC.index("other_re")] = rel(G0[SRC.index("other_re")])

# infrastructure factor: how established the source already is in the region (generation share of its mix vs national)
tot0 = G0.sum(axis=0); nat_sh = G0.sum(axis=1) / G0.sum()
I = np.clip((G0 / tot0) / np.maximum(nat_sh[:, None], 1e-9) / 2, 0, 1)   # 0.5 = same intensity as India; 1 = twice

# land-availability factor Land[s, r]: how land-hungry each source is x how much land each region has per person.
LAND_INTENSITY = {"coal": 0.5, "gas": 0.1, "nuclear": 0.1, "hydro": 0.8, "solar": 1.0, "wind": 0.4, "other_re": 0.9}   # A: relative ranking (solar largest footprint; reservoirs next)
apc = cl.area_per_capita_ha.to_numpy(); land_avail = (apc - apc.min()) / (apc.max() - apc.min())                       # 0 = most crowded region, 1 = most land per person
LAND = np.array([[1 - LAND_INTENSITY[s_] * (1 - la) for la in land_avail] for s_ in SRC])

# environment factor E[s]: 1 - emissions/max, minus a flat ecology penalty for hydro (forest, resettlement) -- assumption
E = np.array([1 - EF[s] / 0.95 for s in SRC]); E[SRC.index("hydro")] -= 0.25; E[SRC.index("nuclear")] -= 0.10  # nuclear: waste/siting penalty (A)
# security factor Sec[s, r]: domestic energy availability.  coal = region's own coal; gas imported; wind/solar/hydro domestic flows.
Sec = np.zeros((len(SRC), len(REG)))
Sec[SRC.index("coal")] = 0.3 + 0.7 * rel(coal_res)
Sec[SRC.index("gas")] = np.array([0.2, 0.2, 0.2, 0.2, 0.6])   # NorthEast gas is domestic (Assam/Tripura); elsewhere mostly imported LNG
Sec[SRC.index("nuclear")] = 0.6
for s in ("hydro", "solar", "wind", "other_re"): Sec[SRC.index(s)] = 1.0

def cost_factor():
    c = np.array([cost_mid[s] for s in SRC]); return 1 - (c - c.min()) / (c.max() - c.min())
CF = cost_factor()

# resource ceilings (GWh) -- energy ceilings derived from published potential (allowed by organisers as weights/sanity ceilings)
HYDRO_CF, HYDRO_USABLE = 0.60, 0.60          # CEA quotes hydro potential at ~60% load factor (to be re-verified); 60% of it assumed buildable by 2047 (forest, resettlement, viability)
WIND_CF, WIND_USABLE = 0.30, 0.50            # A
SOLAR_CF, SOLAR_USABLE, SOLAR_NAT_GWP = 0.20, 0.40, 3343   # NISE 2025 national 3,343 GWp (ground-mounted, wasteland); usable share is an assumption
cap_hyd = hyd_pot * HYDRO_CF * HYDRO_USABLE * 8.76          # MW*8.76 = GWh at CF 1
cap_wind = wind_pot * WIND_CF * WIND_USABLE * 8760          # GW*8760 = GWh
CAP_SOLAR_NAT = SOLAR_NAT_GWP * SOLAR_CF * SOLAR_USABLE * 8760

# ---------------------------------------------------------------- policy factor over time ----------------------
def policy(s, k):   # net-zero-2070 direction: non-fossil gains, coal loses, gas loses less (generation-based, no capacity target used)
    f = k / 21
    return {"coal": 0.5 - 0.5 * f, "gas": 0.5 - 0.25 * f}.get(s, 0.5 + 0.5 * f)

def scores(w, k, use_resource=True, CFv=None):
    CFv = CF if CFv is None else CFv
    w = np.array(w, float).copy()
    if not use_resource: w[1] = 0
    w = w / w.sum()
    S = np.zeros((len(SRC), len(REG)))
    for i, s in enumerate(SRC):
        S[i] = w[0] * CFv[i] + w[1] * R[i] + w[2] * E[i] + w[3] * Sec[i] + w[4] * I[i] + w[5] * policy(s, k) + w[6] * LAND[i]
    return S
# ---------------------------------------------------------------- policy levers (see outputs/step2_policy_levers.csv) -----
EF_COAL, EF_GAS = EF["coal"], EF["gas"]
EI0 = (G0[0].sum() * EF_COAL + G0[1].sum() * EF_GAS) / G0.sum()        # FY2025-26 direct CO2 intensity of the grid, t/MWh
SOL_CF_POLICY, WIND_CF_POLICY = 0.22, 0.30   # A: load factors used ONLY to turn published capacity plans into energy (generation-equivalent)
# NEP 2023 / CEA NGAP 2026 (as summarised by Climate Action Tracker): solar 320 GW + wind 103 GW by 2031-32; 509 GW + 155 GW by 2035-36
POL_2032 = (320 * SOL_CF_POLICY + 103 * WIND_CF_POLICY) * 8760 / 1000 * 1000   # GWh/yr: GW x CF x 8760 h = GWh
POL_2036 = (509 * SOL_CF_POLICY + 155 * WIND_CF_POLICY) * 8760 / 1000 * 1000
VRE0 = G0[4].sum() + G0[5].sum()
def policy_floor(y):
    if y <= 2032: return VRE0 + (POL_2032 - VRE0) * (y - 2026) / 6
    if y <= 2036: return POL_2032 + (POL_2036 - POL_2032) * (y - 2032) / 4
    return 0.0
def cf_vec(price):   # cost factor with an optional carbon price (Rs per tCO2) added to coal and gas
    c = np.array([cost_mid[s_] + price * EF[s_] / 1000 for s_ in SRC]); return 1 - (c - c.min()) / (c.max() - c.min())
W_MEAN = np.array([0.22, 0.22, 0.13, 0.09, 0.14, 0.10, 0.10])   # cost, resource, environment, security, infrastructure, policy, land
NE_SOLAR_MAX_SHARE = 0.30
TEMP = 4.0                                                  # sharpness of regional preference

# ---------------------------------------------------------------- matrix balancing with caps -------------------
def ras(X0, rows, cols, caps, it=200):
    X = X0.copy(); fixed = np.zeros_like(X, bool)
    for _ in range(12):                         # re-run when a ceiling binds
        free = ~fixed
        Xf = np.where(free, X0, 0.0)
        r_t = rows - np.where(fixed, X, 0).sum(axis=1); c_t = cols - np.where(fixed, X, 0).sum(axis=0)
        # a source or region left with nothing to take
        for _ in range(it):
            rs = Xf.sum(axis=1, keepdims=True); Xf = np.where(rs > 0, Xf * (r_t[:, None] / np.where(rs > 0, rs, 1)), 0)
            cs = Xf.sum(axis=0, keepdims=True); Xf = np.where(cs > 0, Xf * (c_t[None, :] / np.where(cs > 0, cs, 1)), 0)
        X = np.where(fixed, X, Xf)
        over = (X > caps + 1e-6) & ~fixed
        if not over.any(): break
        X = np.where(over, caps, X); fixed |= over
    return X

# ---------------------------------------------------------------- one run --------------------------------------
def run(T, par, w, use_resource=True):
    """T: dict year -> array(5) region totals GWh.  par: dict of national-rule parameters.  Returns dict year-> source x region."""
    out = {}; prev = G0.copy(); prev[3] = h5; nat_prev = prev.sum(axis=1)   # start hydro from its normal-year level
    vre_inc = par["A0"]            # GWh per year of new wind+solar energy (grows by lam each year)
    cfv = cf_vec(par.get("carbon", 0.0))
    capw = wind_pot * WIND_CF * par.get("wind_usable", WIND_USABLE) * 8760        # wind ceiling by region
    capS = SOLAR_NAT_GWP * SOLAR_CF * par.get("sol_usable", SOLAR_USABLE) * 8760   # national solar ceiling
    for y in YEARS:
        k = K[y]; rows = T[y]; Tn = rows.sum()
        # ---- national paths for the non-balancing sources ----
        if par.get("nuc2032"):   # policy path: ~22.4 GW by 2031-32 (PIB, Feb 2026), then straight line to the 2047 value
            nuc = (G0[2].sum() + (par["nuc2032"] - G0[2].sum()) * (k / 6) ** 1.5) if k <= 6 else par["nuc2032"] + (par["nuc2047"] - par["nuc2032"]) * (k - 6) / 15
        else:
            nuc = G0[2].sum() + (par["nuc2047"] - G0[2].sum()) * (k / 21) ** par["nuc_exp"]
        hyd = min(h5.sum() * (1 + par["g_hyd"]) ** k, 0.98 * cap_hyd.sum())
        gas = G0[1].sum() * (1 + par["g_gas"]) ** k
        oth = G0[6].sum() * (1 + par["g_oth"]) ** k
        # ---- wind + solar: ramp-limited growth, capped by the integration share and the solar ceiling ----
        vre_inc *= (1 + par["lam"]) if k > 1 else 1
        vre_prev = nat_prev[4] + nat_prev[5]
        vre_ramp = vre_prev + vre_inc
        if par.get("floor"): vre_ramp = max(vre_ramp, policy_floor(y))              # NEP/NGAP capacity plans, converted to energy
        iota = par["iota0"] + (par["iota47"] - par["iota0"]) * k / 21                # storage/grid lever: max wind+solar share of generation
        vre_cap = min(iota * Tn, 0.98 * capw.sum() + capS)
        coal_min = nat_prev[0] * (0.99 if y <= 2030 else 0.94)                       # no coal closures before 2030; afterwards at most -6%/yr (assumption)
        vre_room = Tn - nuc - hyd - gas - oth - coal_min
        vre = max(min(vre_ramp, vre_cap, vre_room), 0.0)
        if par.get("ei_p") is not None:                                              # net-zero lever: grid CO2 intensity must stay under the path
            cap_ei = EI0 * max(1 - (y - 2026) / 44, 0) ** par["ei_p"]
            coal_max = (cap_ei * Tn - gas * EF_GAS) / EF_COAL
            if Tn - nuc - hyd - gas - oth - vre > coal_max:
                vre = max(min(max(vre, Tn - nuc - hyd - gas - oth - coal_max), vre_cap, vre_room), 0.0)
        sol_share = par["sol_share"]
        wnd = min(vre * (1 - sol_share), 0.98 * capw.sum())          # wind cannot pass its resource ceiling; surplus goes to solar
        sol = min(vre - wnd, capS)                                    # solar ceiling: any remainder is left to coal
        coal = Tn - nuc - hyd - gas - oth - sol - wnd
        cols = np.array([coal, gas, nuc, hyd, sol, wnd, oth])
        # ---- regional score shares (increments allocated by score; coal declines in low-score regions first) ----
        S = scores(w, k, use_resource, cfv); A = np.exp(TEMP * S)
        X0 = np.zeros_like(prev)
        for i in range(len(SRC)):
            d = cols[i] - prev[i].sum()
            if d >= 0:      # growth goes where the score is high (nuclear only where a site is possible)
                a_ = A[i] * (R[i] > 0) if i == 2 else A[i]
                X0[i] = prev[i] + d * a_ / a_.sum()
            else:           # decline is taken first where the score is low and the current output is large
                a_ = np.exp(-TEMP * S[i]) * np.maximum(prev[i], 1e-9)
                X0[i] = np.maximum(prev[i] + d * a_ / a_.sum(), 0)
        caps = np.full_like(X0, 1e12)
        caps[3] = cap_hyd; caps[5] = capw
        # integration cap on solar per region: wind + solar <= iota * region total (applied through solar's cap)
        caps[4] = np.minimum(iota, NE_SOLAR_MAX_SHARE * np.array([9, 9, 9, 9, 1.0])) * rows   # NorthEast: hilly/cloudy -> solar limited to 30% of its generation (assumption)
        cur = ras(X0, cols, rows, caps)   # row targets = national source totals, column targets = regional Step-1 totals
        out[y] = cur; prev = cur; nat_prev = cur.sum(axis=1)
    return out

# ---------------------------------------------------------------- scenarios / draws ----------------------------
def totals_by_u(scn, u):
    """Region totals at demand quantile u (0.1->P10, 0.5->P50, 0.9->P90, linear in between and beyond)."""
    d = tot[tot.scenario == scn]; out = {}
    for y in YEARS:
        row = d[d.year == y].set_index("region")
        q = np.array([[row.loc[r, "p10_twh"], row.loc[r, "p50_twh"], row.loc[r, "p90_twh"]] for r in REG]) * 1000
        if u <= 0.5: x = q[:, 1] + (q[:, 1] - q[:, 0]) * (u - 0.5) / 0.4
        else: x = q[:, 1] + (q[:, 2] - q[:, 1]) * (u - 0.5) / 0.4
        out[y] = np.maximum(x, 1.0)
    return out

PAR_CENTRAL = dict(A0=54000.0, lam=0.10, iota0=0.30, iota47=0.65, sol_share=0.65, g_hyd=0.022, g_gas=0.005, g_oth=0.015,
                   nuc_exp=1.5)
NUC_MAIN_SHARE = 0.09           # generation-share statement: ~9% of electricity by 2047 (organisers' reply / policy documents)
NUC_AMBITION_GWH = 700_000.0    # 100 GW x ~80% load factor, separate policy-ambition scenario (organisers confirmed it is allowed if labelled)

VAR = {   # policy variants: overrides of the national rules
    "Main (policy-weighted, nuclear ~9%)": {},
    "Current policies (NEP/NGAP targets)": {"floor": True, "nuc2032": 157_000.0},
    "Net-zero aligned": {"floor": True, "nuc2032": 157_000.0, "nuc700": True, "ei_p": 1.5, "carbon": 1000.0, "iota47": 0.80,
                         "sol_usable": 0.6, "wind_usable": 0.8, "lam": 0.12},
    "Viksit Bharat build-out": {"floor": True, "nuc2032": 157_000.0, "nuc700": True, "iota47": 0.75, "sol_usable": 0.5,
                                "wind_usable": 0.65, "lam": 0.12, "carbon": 500.0},
    "Nuclear ambition (100 GW)": {"nuc700": True},
    "Without resource-potential weights": {},
}
def central_par(variant, main_total_2047):
    p = dict(PAR_CENTRAL); ov = VAR[variant]; p.update({k_: v for k_, v in ov.items() if k_ != "nuc700"})
    p["nuc2047"] = NUC_AMBITION_GWH if ov.get("nuc700") else NUC_MAIN_SHARE * main_total_2047
    return p

def draw_par(rng, variant, main_total_2047):
    p = central_par(variant, main_total_2047); ov = VAR[variant]
    lam0 = ov.get("lam", 0.10); i0 = ov.get("iota47", 0.65)
    p["lam"] = rng.uniform(lam0 - 0.04, lam0 + 0.04); p["iota47"] = rng.uniform(i0 - 0.10, i0 + 0.10); p["sol_share"] = rng.uniform(0.55, 0.75)
    p["g_hyd"] = rng.uniform(0.012, 0.032); p["g_gas"] = rng.uniform(-0.010, 0.020); p["g_oth"] = rng.uniform(0.0, 0.03)
    p["nuc_exp"] = rng.uniform(1.2, 2.0)
    p["nuc2047"] = (NUC_AMBITION_GWH * rng.uniform(0.9, 1.0) if ov.get("nuc700") else rng.uniform(0.07, 0.10) * main_total_2047)
    return p

def tidy(res_by_year, scn, var, kind):
    rows = []
    for y, X in res_by_year.items():
        for ri, r in enumerate(REG):
            for si, s in enumerate(SRC): rows.append((scn, var, r, y, s, X[si, ri]))
        for si, s in enumerate(SRC): rows.append((scn, var, "India", y, s, X[si].sum()))
    return pd.DataFrame(rows, columns=["scenario", "variant", "region", "year", "source", "gwh"])

if __name__ == "__main__":
    scenarios = sorted(tot.scenario.unique())
    variants = {v: (v != "Without resource-potential weights") for v in VAR}
    central_rows, draw_rows = [], []
    rng = np.random.default_rng(RNG_SEED)
    for scn in scenarios:
        T50 = totals_by_u(scn, 0.5); main2047 = sum(T50[2047])
        main_ref = sum(totals_by_u("Main (all uncertainty)", 0.5)[2047])    # nuclear is a build-limited quantity: anchor to the Main median, not each scenario
        for var, use_res in variants.items():
            central_rows.append(tidy(run(T50, central_par(var, main_ref), W_MEAN, use_res), scn, var, "central"))
            chunk = []
            for d in range(N_DRAWS):
                u = rng.uniform(0.0, 1.0); w = rng.dirichlet(W_MEAN * 40)
                T = totals_by_u(scn, u); r = run(T, draw_par(rng, var, main_ref), w, use_res)
                df = tidy(r, scn, var, "draw"); df["draw"] = d; chunk.append(df)
            draw_rows.append(pd.concat(chunk))
            print("done", scn, var, flush=True)
    central = pd.concat(central_rows)
    central["twh"] = central.gwh / 1000
    central["share_pct"] = 100 * central.twh / central.groupby(["scenario", "variant", "region", "year"]).twh.transform("sum")
    central[["scenario", "variant", "region", "year", "source", "twh", "share_pct"]].round(3).to_csv(OUT / "step2_mix_yearly_central.csv", index=False)

    draws = pd.concat(draw_rows); draws["twh"] = draws.gwh / 1000
    draws["share_pct"] = 100 * draws.twh / draws.groupby(["scenario", "variant", "region", "year", "draw"]).twh.transform("sum")
    g = draws.groupby(["scenario", "variant", "region", "year", "source"])
    rng_df = pd.concat({"twh_p10": g.twh.quantile(0.1), "twh_p50": g.twh.quantile(0.5), "twh_p90": g.twh.quantile(0.9),
                        "share_p10": g.share_pct.quantile(0.1), "share_p50": g.share_pct.quantile(0.5), "share_p90": g.share_pct.quantile(0.9)}, axis=1).reset_index()
    rng_df.round(3).to_csv(OUT / "step2_mix_yearly_ranges.csv", index=False)
    print("written")
