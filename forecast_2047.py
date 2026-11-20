#!/usr/bin/env python3
"""
forecast_2047.py  --  Step 1 of the Innothon solution: national + regional
GENERATION forecast for FY2046-47 with an uncertainty range.

Runs on CPU only (numpy + pandas), takes a few seconds.  No machine learning
frameworks, on purpose -- see "WHY THIS MODEL" below.

RULES FROM THE BRIEF
  * Target variable is energy GENERATED (GWh).  Installed capacity and
    consumption are NOT used anywhere in this file (the capacity columns of
    renewable_energy_dataset.csv are never read).
  * Population and GSDP are used only as DRIVERS of generation.

WHY THIS MODEL  (a "growth-accounting" panel model with Monte Carlo)
  1. We have very little history: 5 regions x ~6 usable years = 30 points.
     Neural nets / gradient boosting would memorise noise with so few points,
     and a judge cannot inspect them.  A log-log regression has ONE number
     that matters (the income elasticity) and it is easy to defend.
  2. Generation per person rises with income.  So
         ln(generation per capita) = region effect + beta * ln(real income per capita)
     beta is the income elasticity: "1% richer -> beta % more electricity".
  3. Forecast = start from the latest ACTUAL generation of each region and grow
     it with   growth = beta_t * (income-per-capita growth) + (population growth).
     Anchoring on actuals avoids extrapolating a regression intercept.
  4. Everything we cannot measure (future GDP growth, population, how fast the
     elasticity fades, EV / data-centre / hydrogen uplift) is a labelled
     assumption below, drawn from a range thousands of times (Monte Carlo).
     The spread of the results IS the uncertainty band the brief asks for.

Usage:
    python forecast_2047.py --data-dir ./data --out-dir ./outputs
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# =============================================================================
# 0. ASSUMPTIONS  (every judgement call is a named knob so it can be defended,
#    changed, or turned into a slider on the dashboard)
# =============================================================================
SEED = 2047
N_DRAWS = 20_000            # Monte Carlo paths; 20k is plenty and still instant on a CPU
N_STEPS = 21                # FY2025-26 (last actual) -> FY2046-47
REGIONS = ["North", "West", "South", "East", "NorthEast"]

# Dataset "Year" -> financial year.  The dataset does not say whether Year=2018
# means FY2018-19 or calendar 2018.  We assume it labels the FY STARTING that year.
# Set to -1 or 1 to test how much this matters.
YEAR_SHIFT = 0

# The dataset README calls GSDP "nominal", but the numbers behave like a REAL
# (constant-price) series: the all-India total is ~86 lakh crore in 2011 (India's
# GDP in 2011-12 prices was ~87), it grows ~5.3%/yr 2011-2023 (nominal would be
# roughly double), and it dips in 2020 like real GDP did.  So we do NOT deflate.
# (A first run that deflated by 4.5%/yr gave a negative elasticity -- a clear sign
# the deflation was wrong.)  We still expose the knob and print how beta responds
# if this reading were mistaken.
DEFLATOR_INFLATION = 0.0

# FY2020-21: COVID shock, and CEA's regional RE totals for that year are not yet
# collected.  Excluding it also stops one abnormal year from bending beta.
EXCLUDE_FY = {"2020-21"}

# --- Future drivers (assumptions to be cited / sourced before submission) ----
POP_2025_BN = 1.464                 # VERIFIED: UN WPP 2024, India 2025 median = 1,463,865,525 (UN Data Portal, total population by sex)
POP_2047_RANGE_BN = (1.58, 1.70)    # UN WPP 2024 2047 MEDIAN = 1,666,628,147 (verified). The 1.58-1.70 band is OUR assumption: UN lower/upper interval not yet retrieved
# Real GDP growth.  Published views span a wide range, so the main band is deliberately wide:
#   * Economic Survey 2024-25: ~8% real growth needed for a decade or two to reach "Viksit Bharat" by 2047
#   * NITI Aayog CEO: 6.5% is NOT enough, ~8% is needed;  another NITI member earlier: 6-6.2% would do
#   * Recent actuals: 9.2% (FY24), 6.5% (FY25); new GDP series gave ~7.6% for FY26
# The band below straddles 6% to 8%; growth fades over time as the economy matures.
GDP_START = (0.070, 0.010)          # growth now:  mean, sd  (draws roughly 5%-9%)
GDP_END = (0.055, 0.010)            # growth by 2047: mean, sd (draws roughly 3.5%-7.5%)
GDP_CLIP = (0.03, 0.10)             # keep draws physically sensible
# Named scenarios (narrow sd) so the dashboard can show "what if India really does reach ~8%?"
SCENARIOS = {
    "Low growth (~5%)":            ((0.060, 0.004), (0.040, 0.004)),
    "Base (~6-6.5%)":              ((0.068, 0.004), (0.055, 0.004)),
    "High: Viksit Bharat (~7.5-8%)": ((0.080, 0.004), (0.070, 0.004)),
}
# WHY 0-20%: the CSEP working paper "On India's Electricity Consumption" finds the long-run
# elasticity of electricity use to economic output has been close to 1, and links likely
# future change to electrification/decarbonisation (which pushes elasticity UP), not to rising
# income.  So the central case keeps beta ~1.0.  The 0-20% fade is only an allowance for
# efficiency gains, shown as downside risk.  A stronger 40% fade is run as a named low
# scenario below (ELASTICITY_FADE_LOW), not in the default band.
ELASTICITY_FADE = (0.0, 0.2)        # by 2047 the elasticity is 0-20% lower
ELASTICITY_FADE_LOW = 0.4           # low-scenario fade
BETA_CLIP = (0.3, 1.3)              # keep sampled betas in a plausible range
# WHY a long-window elasticity instead of the 6-year panel: over 2018-2024 the
# dataset's GSDP grows only ~3%/yr (actual real GDP grew ~5%), so income looks too
# flat and the panel beta is inflated, unstable and no better than a naive forecast
# (see the backtest printout).  Over 2011-2023 both ends of the GSDP series are
# sound, so we measure beta there.  Two national anchor points, CEA Growth Book 2024
# Table 3 (utilities, incl. RE): FY2011-12 and FY2023-24 total generation, GWh.
NATIONAL_GEN_GWH = {2011: 922_451, 2023: 1_734_375}
BETA_SD = 0.15                      # spread across alternative windows (roughly 0.9 to 1.3)
ELECTRIFICATION_UPLIFT = (0.0, 0.003)  # extra growth/yr (0-0.3pp) from EVs, data centres, green H2; ramps in over 5 yrs
REGIONAL_SHRINK = 0.5               # only half of a region's past out/under-performance is assumed to persist
DIFF_CLIP = 0.015                   # ...and never more than +/-1.5pp/yr

# =============================================================================
# 1. DATA  (state -> CEA region mapping matches the regions used by NPP / CEA
#    reports, so the socio-economic panel lines up with the generation data)
# =============================================================================
STATE_TO_REGION = {
    # Northern
    "Chandigarh": "North", "Delhi": "North", "Haryana": "North", "Himachal Pradesh": "North",
    "Jammu And Kashmir": "North", "Punjab": "North", "Rajasthan": "North",
    "Uttar Pradesh": "North", "Uttarakhand": "North",
    # Western (CEA puts Chhattisgarh and Madhya Pradesh here, NOT in a "Central" zone)
    "Chhattisgarh": "West", "Goa": "West", "Gujarat": "West", "Madhya Pradesh": "West",
    "Maharashtra": "West",
    # Southern
    "Andhra Pradesh": "South", "Karnataka": "South", "Kerala": "South", "Lakshadweep": "South",
    "Puducherry": "South", "Tamil Nadu": "South", "Telangana": "South",
    # Eastern
    "Andaman And Nicobar Islands": "East", "Bihar": "East", "Jharkhand": "East",
    "Odisha": "East", "Sikkim": "East", "West Bengal": "East",
    # North-Eastern
    "Arunachal Pradesh": "NorthEast", "Assam": "NorthEast", "Manipur": "NorthEast",
    "Meghalaya": "NorthEast", "Mizoram": "NorthEast", "Nagaland": "NorthEast",
    "Tripura": "NorthEast",
}

# Regional RE generation TOTALS (MU = GWh) for years where CEA's old-format
# report gives region totals but not the split by source.  Source: CEA monthly
# RE report, March 2020 (cumulative April-March).  Read via a text summary, but
# the regions sum to the printed All-India totals.
RE_REGION_TOTALS_ONLY = {
    "2018-19": {"North": 24672.03, "West": 38168.02, "South": 60926.55, "East": 2708.02, "NorthEast": 284.49},
    "2019-20": {"North": 27189.51, "West": 41137.31, "South": 67009.28, "East": 2719.01, "NorthEast": 281.91},
}


def read_socioeconomic(path: Path) -> pd.DataFrame:
    """Population and GSDP by region and year.  Capacity columns are never read."""
    d = pd.read_csv(path, usecols=["State", "Year", "Population", "GSDP (crore INR)"])
    d = d.rename(columns={"Population": "pop", "GSDP (crore INR)": "gsdp_cr"})
    unknown = set(d.State) - set(STATE_TO_REGION)
    assert not unknown, f"states missing from region map: {unknown}"
    d["region"] = d.State.map(STATE_TO_REGION)
    # WHY >= 2011: the GSDP series jumps ~2.3x between 2010 and 2011 (base-year
    # change, not growth).  Mixing the two series would fake a huge growth rate.
    d = d[d.Year >= 2011]
    return d.groupby(["region", "Year"], as_index=False)[["pop", "gsdp_cr"]].sum()


def read_generation(conv_csv: Path, re_csv: Path) -> pd.DataFrame:
    """Total regional generation (GWh) = thermal+nuclear+large hydro (NPP) + RE excl. large hydro (CEA)."""
    conv = pd.read_csv(conv_csv)
    conv["conv_gwh"] = conv[["thermal_gwh", "nuclear_gwh", "hydro_gwh"]].sum(axis=1)
    re_ = pd.read_csv(re_csv)
    # 1 MU (million units) == 1 GWh.  Large hydro is excluded here because the NPP
    # hydro column already contains it -- counting it twice would inflate totals.
    re_["re_gwh"] = re_[[c for c in re_.columns if c.endswith("_mu")]].sum(axis=1)
    extra = pd.DataFrame([{"fy": fy, "region": r, "re_gwh": v}
                          for fy, dd in RE_REGION_TOTALS_ONLY.items() for r, v in dd.items()])
    re_all = pd.concat([re_[["fy", "region", "re_gwh"]], extra], ignore_index=True)
    g = conv.merge(re_all, on=["fy", "region"], how="left")  # FY2020-21 stays NaN on purpose
    g["gen_gwh"] = g.conv_gwh + g.re_gwh
    return g


def build_panel(gen: pd.DataFrame, socio: pd.DataFrame) -> pd.DataFrame:
    g = gen.copy()
    g["year"] = g.fy.str[:4].astype(int) + YEAR_SHIFT
    p = g.merge(socio, left_on=["region", "year"], right_on=["region", "Year"], how="inner")
    p = p[~p.fy.isin(EXCLUDE_FY)].dropna(subset=["gen_gwh"]).copy()
    return p.drop(columns=["Year"])


# =============================================================================
# 2. INCOME ELASTICITY  (the only thing we estimate from data)
# =============================================================================
def add_xy(p: pd.DataFrame, infl: float) -> pd.DataFrame:
    p = p.copy()
    p["y"] = np.log(p.gen_gwh * 1e6 / p["pop"])                       # ln(kWh generated per person)
    p["x"] = np.log(p.gsdp_cr * 1e7 / p["pop"]) - infl * (p.year - 2018)  # ln(REAL income per person)
    return p


def fit_beta(p: pd.DataFrame, infl: float) -> float:
    """
    'Within' (fixed-effects) estimator: subtract each region's own average from
    both variables, then regress.  WHY: regions differ hugely in level (Western
    has heavy industry, North-East almost none).  Subtracting the regional mean
    stops those permanent differences from being mistaken for the effect of income,
    so beta is learned only from how each region changes over time.
    """
    p = add_xy(p, infl)
    xw = p.x - p.groupby("region").x.transform("mean")
    yw = p.y - p.groupby("region").y.transform("mean")
    return float((xw * yw).sum() / (xw ** 2).sum())


def bootstrap_beta(p: pd.DataFrame, infl: float, rng: np.random.Generator, B: int = 2000) -> np.ndarray:
    """
    Resample whole YEARS (not single rows).  WHY: shocks such as weather or policy hit
    all regions in the same year, so rows within a year are not independent.
    Resampling years gives honest (wider) uncertainty on beta.
    """
    years = np.sort(p.year.unique())
    out = []
    for _ in range(B):
        pick = rng.choice(years, size=len(years), replace=True)
        sub = pd.concat([p[p.year == y] for y in pick], ignore_index=True)
        # same region appears several times -> keep region-demeaning valid
        try:
            out.append(fit_beta(sub, infl))
        except ZeroDivisionError:
            continue
    return np.array([b for b in out if np.isfinite(b)])


def longrun_beta(socio: pd.DataFrame) -> float:
    """
    Elasticity from the whole 2011->2023 span: growth of generation per person divided
    by growth of income per person.  WHY: with only two endpoints there is no
    short-term noise to mislead us, and 12 years of change is far more informative than
    6.  The matching real-world check: electricity growth ~ GDP growth in India, i.e. ~1.
    """
    nat = socio.groupby("Year")[["pop", "gsdp_cr"]].sum()
    a, b = 2011, 2023
    d_gen = np.log(NATIONAL_GEN_GWH[b] / NATIONAL_GEN_GWH[a])
    d_pop = np.log(nat.loc[b, "pop"] / nat.loc[a, "pop"])
    d_gdp = np.log(nat.loc[b, "gsdp_cr"] / nat.loc[a, "gsdp_cr"])
    return float((d_gen - d_pop) / (d_gdp - d_pop))


def backtest(p: pd.DataFrame, infl: float, train_max_year: int = 2022) -> dict:
    """
    Honest test: fit on early years, then predict later years we already know.
    We compare against a naive 'nothing changes' forecast.  If the model cannot
    beat 'nothing changes', it should not be trusted.  (Uses the REAL later income
    and population, so this tests the elasticity, not our GDP guesses.)
    """
    tr = add_xy(p[p.year <= train_max_year], infl)
    te = add_xy(p[p.year > train_max_year], infl)
    beta = fit_beta(p[p.year <= train_max_year], infl)
    last = tr[tr.year == tr.year.max()].set_index("region")[["y", "x"]].rename(columns={"y": "y0", "x": "x0"})
    te = te.join(last, on="region")
    te["pred_model"] = np.exp(te.y0 + beta * (te.x - te.x0)) * te["pop"] / 1e6
    te["pred_naive"] = np.exp(te.y0) * te["pop"] / 1e6   # same kWh/person as the last training year
    return {
        "beta_train": beta,
        "mape_model_%": float(100 * (te.pred_model / te.gen_gwh - 1).abs().mean()),
        "mape_naive_%": float(100 * (te.pred_naive / te.gen_gwh - 1).abs().mean()),
        "n_test": len(te),
    }


# =============================================================================
# 3. HISTORICAL RATES USED TO SHAPE THE FUTURE
# =============================================================================
def regional_rates(socio: pd.DataFrame):
    piv_pop = socio.pivot(index="Year", columns="region", values="pop")[REGIONS]
    piv_gs = socio.pivot(index="Year", columns="region", values="gsdp_cr")[REGIONS]
    w = piv_pop.loc[2024] / piv_pop.loc[2024].sum()   # population weights

    # Population: regional growth 2019->2024.  Only the DIFFERENCE between a region and
    # the national average is kept; the national level comes from the UN-style range.
    g_pop = np.log(piv_pop.loc[2024] / piv_pop.loc[2019]) / 5
    dpop = (g_pop - (w * g_pop).sum()).to_numpy()

    # Income per person: 2012->2023 (2024 GSDP looks stale: national total dips).  The
    # deflator cancels when we take a region MINUS the national rate, so this part is
    # independent of the inflation assumption.
    inc = piv_gs / piv_pop
    c = np.log(inc.loc[2023] / inc.loc[2012]) / 11
    nat = np.log((piv_gs.loc[2023].sum() / piv_pop.loc[2023].sum()) / (piv_gs.loc[2012].sum() / piv_pop.loc[2012].sum())) / 11
    delta = np.clip(REGIONAL_SHRINK * (c - nat), -DIFF_CLIP, DIFF_CLIP).to_numpy()
    return dpop, delta


# =============================================================================
# 4. MONTE CARLO FORECAST
# =============================================================================
def simulate(anchor, dpop, delta, betas, rng, n=N_DRAWS, gdp_shift=0.0,
             fade_override=None, uplift_override=None, beta_override=None,
             gdp_start=None, gdp_end=None):
    """
    Returns generation paths (GWh), shape (draws, regions, years).
    Each draw picks ONE plausible future (one GDP path, one population total, one
    elasticity ...) and grows each region from its latest actual generation.
    """
    R, T = len(REGIONS), N_STEPS
    t = np.arange(1, T + 1)
    frac = (t - 1) / (T - 1)            # 0 at the start, 1 at 2047
    fade = 1 - t / T                    # regional differences shrink to ~0 by 2047

    # population: national CAGR from the sampled 2047 total; regions differ by dpop (fading)
    P47 = rng.uniform(*POP_2047_RANGE_BN, n)
    g_pn = np.log(P47 / POP_2025_BN) / 22
    gp = g_pn[:, None, None] + dpop[None, :, None] * fade[None, None, :]

    # real GDP growth: starts high, fades linearly; both ends are uncertain
    gs, ge = (gdp_start or GDP_START), (gdp_end or GDP_END)   # scenarios override the default band
    g0 = np.clip(rng.normal(gs[0] + gdp_shift, gs[1], n), *GDP_CLIP)
    g1 = np.clip(rng.normal(ge[0] + gdp_shift, ge[1], n), *GDP_CLIP)
    g_gdp = g0[:, None] + (g1 - g0)[:, None] * frac[None, :]
    gy = (g_gdp - g_pn[:, None])[:, None, :] + delta[None, :, None] * fade[None, None, :]  # income PER PERSON

    # elasticity: bootstrap draw, then fades over time (efficiency / saturation)
    beta = rng.choice(np.clip(betas, *BETA_CLIP), n) if beta_override is None else np.full(n, beta_override)
    f = rng.uniform(*ELASTICITY_FADE, n) if fade_override is None else np.full(n, fade_override)
    e = beta[:, None, None] * (1 - f[:, None, None] * frac[None, None, :])

    # structural uplift not visible in history: EVs, data centres, green hydrogen
    u = rng.uniform(*ELECTRIFICATION_UPLIFT, n) if uplift_override is None else np.full(n, uplift_override)
    ramp = np.minimum(1, t / 5)

    growth = e * gy + gp + u[:, None, None] * ramp[None, None, :]
    return anchor[None, :, None] * np.exp(np.cumsum(growth, axis=2))


def main(data_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    socio = read_socioeconomic(data_dir / "renewable_energy_dataset.csv")
    gen = read_generation(data_dir / "regional_generation_conventional_gwh.csv",
                          data_dir / "regional_generation_re_mu.csv")
    panel = build_panel(gen, socio)
    print(f"Panel: {len(panel)} region-years, FYs used: {sorted(panel.fy.unique())}")

    # ---- elasticity + honesty checks ---------------------------------------
    # (a) DIAGNOSTIC ONLY: the short panel estimate.  Kept in the printout to show why we reject it.
    beta_hat = fit_beta(panel, DEFLATOR_INFLATION)
    pb = bootstrap_beta(panel, DEFLATOR_INFLATION, rng)
    q = np.percentile(pb, [5, 50, 95])
    print(f"[diagnostic] 6-year panel beta = {beta_hat:.2f}  (bootstrap 5/50/95%: {q[0]:.2f} / {q[1]:.2f} / {q[2]:.2f}) -> NOT used")
    # (b) USED: the long-window national elasticity, with an honest spread around it.
    beta_long = longrun_beta(socio)
    betas = np.random.default_rng(SEED).normal(beta_long, BETA_SD, 2000)
    print(f"[used] long-run beta 2011->2023 = {beta_long:.2f}, sampled with sd {BETA_SD}")
    for infl in (0.0, 0.01, 0.02):
        print(f"  beta if price growth were {infl:.1%}/yr: {fit_beta(panel, infl):.2f}")
    print("Backtest (train <=2022, test later years):", {k: round(v, 3) for k, v in backtest(panel, DEFLATOR_INFLATION).items()})

    # ---- forecast ------------------------------------------------------------
    anchor = (gen[gen.fy == "2025-26"].set_index("region").gen_gwh.reindex(REGIONS)).to_numpy()
    dpop, delta = regional_rates(socio)
    paths = simulate(anchor, dpop, delta, betas, np.random.default_rng(SEED))
    nat = paths.sum(axis=1)

    years = [f"{2026 + i}-{str(2027 + i)[2:]}" for i in range(N_STEPS)]
    rows = []
    for name, arr in [("India", nat)] + [(r, paths[:, i, :]) for i, r in enumerate(REGIONS)]:
        qs = np.percentile(arr, [10, 50, 90], axis=0) / 1000   # GWh -> TWh
        for k, fy in enumerate(years):
            rows.append({"region": name, "fy": fy, "year": 2027 + k, "p10_twh": qs[0, k], "p50_twh": qs[1, k], "p90_twh": qs[2, k]})
    pd.DataFrame(rows).round(1).to_csv(out_dir / "forecast_paths_quantiles.csv", index=False)

    print(f"\nFY2025-26 anchor (actual, excl. Bhutan imports): {anchor.sum() / 1000:,.0f} TWh")
    print("FY2046-47 forecast, TWh  (P10 / P50 / P90):")
    for name, arr in [("India", nat[:, -1])] + [(r, paths[:, i, -1]) for i, r in enumerate(REGIONS)]:
        a = np.percentile(arr, [10, 50, 90]) / 1000
        print(f"  {name:<10} {a[0]:>8,.0f} / {a[1]:>8,.0f} / {a[2]:>8,.0f}")
    cagr = np.percentile(np.log(nat[:, -1] / anchor.sum()) / (N_STEPS), [10, 50, 90])
    print(f"Implied national CAGR (P10/P50/P90): {cagr[0]:.2%} / {cagr[1]:.2%} / {cagr[2]:.2%}")

    # ---- sensitivity: which assumption moves the answer most? ------------------
    print("\nSensitivity of median India FY2046-47 (TWh) to one assumption at a time:")
    base = np.median(nat[:, -1]) / 1000
    scen = {
        "baseline": {},
        "elasticity does not fade": {"fade_override": 0.0},
        "elasticity fades 40% (low scenario)": {"fade_override": ELASTICITY_FADE_LOW},
        "no EV/data-centre uplift": {"uplift_override": 0.0},
        "uplift 0.3pp/yr": {"uplift_override": 0.003},
        # WHY: urbanization is NOT a model driver (Census 2011 is a single year, r=0.51 with income, no citable
        # 2047 projection -- see urban_check.py).  This is a flagged ASSUMPTION: urban growth adds an extra
        # 0.15pp/yr on top of the top of the EV/data-centre range (0.30pp), i.e. 0.45pp/yr total.
        "faster urbanization (+0.15pp/yr, assumption)": {"uplift_override": 0.0045},
        "GDP growth -1pp": {"gdp_shift": -0.01},
        "GDP growth +1pp": {"gdp_shift": 0.01},
    }
    sens = []
    sens_yearly = []   # WHY: dashboard year filter needs each sensitivity case for every year, not only 2047
    for label, kw in scen.items():
        sim_nat = simulate(anchor, dpop, delta, betas, np.random.default_rng(SEED), **kw).sum(axis=1)
        m = np.median(sim_nat[:, -1]) / 1000
        for k_, med_ in enumerate(np.median(sim_nat, axis=0) / 1000):
            sens_yearly.append({"case": label, "fy": years[k_], "year": 2027 + k_, "india_p50_twh": round(med_, 1)})
        sens.append({"scenario": label, "india_2046_47_median_twh": round(m, 0), "vs_baseline_%": round(100 * (m / base - 1), 1)})
        print(f"  {label:<28} {m:>8,.0f}  ({100 * (m / base - 1):+.1f}%)")
    pd.DataFrame(sens).to_csv(out_dir / "forecast_sensitivity.csv", index=False)
    pd.DataFrame(sens_yearly).to_csv(out_dir / "forecast_yearly_sensitivity.csv", index=False)

    # ---- named GDP scenarios (everything else keeps its uncertainty) ----------
    print("\nNamed GDP scenarios, India FY2046-47 TWh (P10 / P50 / P90) and implied CAGR:")
    srows = []
    yrows = []   # WHY: year-by-year P10/P50/P90 per scenario and region, so the dashboard can filter any year 2027-2047
    for label, (gs, ge) in SCENARIOS.items():
        p = simulate(anchor, dpop, delta, betas, np.random.default_rng(SEED), gdp_start=gs, gdp_end=ge)
        n_ = p.sum(axis=1)[:, -1]
        a = np.percentile(n_, [10, 50, 90]) / 1000
        cg = np.log(np.median(n_) / anchor.sum()) / N_STEPS
        print(f"  {label:<32} {a[0]:>7,.0f} / {a[1]:>7,.0f} / {a[2]:>7,.0f}   CAGR {cg:.2%}")
        for nm_, arr_ in [("India", p.sum(axis=1))] + [(r_, p[:, j_, :]) for j_, r_ in enumerate(REGIONS)]:
            q_ = np.percentile(arr_, [10, 50, 90], axis=0) / 1000
            for k_ in range(N_STEPS):
                yrows.append({"scenario": label, "region": nm_, "fy": years[k_], "year": 2027 + k_,
                              "p10_twh": q_[0, k_], "p50_twh": q_[1, k_], "p90_twh": q_[2, k_]})
        for i, r in enumerate(REGIONS):
            b = np.percentile(p[:, i, -1], [10, 50, 90]) / 1000
            srows.append({"scenario": label, "region": r, "p10_twh": b[0], "p50_twh": b[1], "p90_twh": b[2]})
        srows.append({"scenario": label, "region": "India", "p10_twh": a[0], "p50_twh": a[1], "p90_twh": a[2]})
    pd.DataFrame(srows).round(0).to_csv(out_dir / "forecast_scenarios.csv", index=False)
    # main case (all uncertainty at once) added to the same long file so one filter covers everything
    for nm_, arr_ in [("India", nat)] + [(r_, paths[:, j_, :]) for j_, r_ in enumerate(REGIONS)]:
        q_ = np.percentile(arr_, [10, 50, 90], axis=0) / 1000
        for k_ in range(N_STEPS):
            yrows.append({"scenario": "Main (all uncertainty)", "region": nm_, "fy": years[k_], "year": 2027 + k_,
                          "p10_twh": q_[0, k_], "p50_twh": q_[1, k_], "p90_twh": q_[2, k_]})
    yl = pd.DataFrame(yrows)
    yl["p50_yoy_growth_%"] = yl.groupby(["scenario", "region"]).p50_twh.pct_change() * 100
    yl.round(1).to_csv(out_dir / "forecast_yearly_all.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("./data"))
    ap.add_argument("--out-dir", type=Path, default=Path("./outputs"))
    a = ap.parse_args()
    main(a.data_dir, a.out_dir)
