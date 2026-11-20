# Deliverable 4: Transparent methodology

This document states every modelling step, every assumption and every uncertainty statement behind the forecast, the regional mix and the dashboard, and says where in the repository to find or change each one. If a number appears in a chart, you should be able to trace it back through this document to a file and a line of code.

Years are labelled by the financial-year end (2047 means FY2046-47). All quantities are **generation (energy)**, in GWh or TWh.

## 1. Scope and ground rules

| Rule | How it is respected |
|---|---|
| Generation is the basis; capacity and consumption are not used to forecast or compare | The capacity columns of the supplied dataset are never read. Capacity-type numbers appear in exactly three places, each labelled: resource potentials (hydro MW, wind GW, solar GWp) used as **ceilings and score weights**; a labelled 100 GW nuclear scenario; and policy capacity plans converted to energy with stated load factors |
| Everything must run on a CPU | numpy and pandas only. Step 1 takes seconds, Step 2 about 8 minutes, the dashboard runs in the browser |
| Assumptions must be explicit and defensible | Each is a named constant (Section 7 lists them all) and a slider or variant in the dashboard where practical |
| Uncertainty must be stated | Monte Carlo bands for both steps, scenarios, sensitivities and policy variants (Section 6) |

## 2. Data inventory

| File (repo root unless noted) | Content | Source | Used for |
|---|---|---|---|
| `regional_generation_conventional_gwh.csv` | Regional thermal, nuclear, large hydro generation, FY2018-19 to FY2025-26 | National Power Portal monthly reports | Base year, base mix |
| `regional_generation_re_mu.csv` | Regional solar, wind, small hydro, other RE generation, FY2021-22 to FY2025-26 | CEA renewable energy generation reports | Base year, base mix |
| `gas_stations_fy2025_26.csv` | Gas station generation FY2025-26 | National Power Portal station reports | Splits gas out of thermal |
| `renewable_energy_dataset.csv` | State GSDP and population by year | Supplied with the challenge | Regional income and population drivers (generation and capacity columns are not used) |
| Constants in `forecast_2047.py` | National generation 2011 (922,451 GWh) and 2023 (1,734,375 GWh) | CEA, Growth of Electricity Sector in India | Long-run elasticity |
| Constants in `forecast_2047.py` | Population 2025: 1.464 bn; 2047 median about 1.67 bn | UN World Population Prospects 2024 | Population path |
| `census2011_A1.xlsx`, `outputs/urban_share_by_*.csv` | Urban population by state, 2011 | Census of India 2011, Table A-1 | Urbanization test and slider |
| `resource_indicators_state.csv` | Coal resource (Mt), hydro exploitable potential (MW), wind potential at 120 m (GW) by state | Ministry of Coal 2025, CEA 2017-23, NIWE | Resource factor and ceilings |
| `ghi_states.csv`, `region_climate_land.csv` | Solar irradiance by state/region; land per person | Global Solar Atlas values via a secondary page; Census 2011 area per person | Solar resource factor, land factor |
| `outputs/step2_policy_levers.csv` | Each policy lever, value, source, how used, status | Table of sources in Part B of `03_data_backed_rationale.md` | Policy variants |

Data gaps that are disclosed, not hidden: the state-level NISE solar potential table and forest cover could not be retrieved (solar uses irradiance; forest cover is omitted); East and NorthEast wind potential is not in the data; regional costs do not exist, so costs are national.

## 3. Step 1: generation forecast (`forecast_2047.py`)

### 3.1 Steps in order

1. **Build the base year.** Take each region's FY2025-26 generation (North 466,159; West 653,441; South 425,088; East 274,198; NorthEast 21,225 GWh; India 1,840,111 GWh). This is reconciled to CEA national totals within about 0.01%. Bhutan imports are excluded.
2. **Estimate the income elasticity** from national generation 2011 and 2023 with population and income: about 0.995. A 6-year regional panel estimate is computed only as a diagnostic and **not used** (too short). FY2020-21 is excluded from panel work (COVID).
3. **Set the drivers for each region:** income growth per person, population growth, and a small electrification uplift (Section 3.2).
4. **Simulate 20,000 paths.** Each draw picks one possible future (one GDP path, one 2047 population, one elasticity and fade, one uplift) and grows each region from its base-year generation.
5. **Summarise** the paths into P10, P50 and P90 per region and year.
6. **Repeat** for four growth scenarios and eight one-at-a-time sensitivities.

### 3.2 The equation

For region *i* and year step *t* = 1..21 (FY2026-27 to FY2046-47):

```
growth(i,t)  = e(t) * gy(i,t) + gp(i,t) + u * ramp(t)
generation(i,t) = generation(i,0) * exp( sum of growth(i,s) for s = 1..t )
```

| Term | Definition | Why |
|---|---|---|
| `e(t)` | `beta * (1 - fade * frac(t))`, with `frac = (t-1)/20` | Elasticity of electricity to income, fading over time for efficiency gains |
| `gy(i,t)` | `(g_gdp(t) - g_pop) + delta_i * (1 - t/21)` | Income growth **per person**: national GDP growth minus population growth, plus a regional difference that shrinks to zero by 2047 |
| `g_gdp(t)` | Straight line from `g0` (now) to `g1` (2047), both random | GDP growth starts high and eases as the economy matures |
| `gp(i,t)` | `g_pop + dpop_i * (1 - t/21)` | Population growth: national rate from the 2047 population draw, `g_pop = ln(P2047 / 1.464) / 22`, plus a regional difference that fades |
| `u * ramp(t)` | `u` extra growth per year, `ramp = min(1, t/5)` | EV, data-centre and similar electrification not visible in history; ramps in over five years |

Regional differences (`delta_i`, `dpop_i`) are computed from 2012-2023 income per person and 2019-2024 population by region. Only the **difference from the national rate** is kept, and income differences are cut by half (`REGIONAL_SHRINK = 0.5`) and capped at +/-1.5 pp a year (`DIFF_CLIP`), because only part of past out- or under-performance is assumed to persist.

### 3.3 Parameters and distributions

| Parameter | Value | Type | Where |
|---|---|---|---|
| Draws | 20,000 | Setting | `N_DRAWS` |
| Seed | 2047 | Setting | `SEED` |
| Elasticity `beta` | Normal(0.995, 0.15), clipped to 0.3-1.3 | Estimated (mean), assumed (spread) | `longrun_beta`, `BETA_SD`, `BETA_CLIP` |
| Elasticity fade | Uniform(0, 20%) by 2047; 40% in the low-fade sensitivity | **Assumption** | `ELASTICITY_FADE`, `ELASTICITY_FADE_LOW` |
| GDP growth now `g0` | Normal(7.0%, 1.0 pp), clipped 3-10% | Assumption | `GDP_START`, `GDP_CLIP` |
| GDP growth 2047 `g1` | Normal(5.5%, 1.0 pp), clipped 3-10% | Assumption | `GDP_END` |
| Population 2025 | 1.464 bn | UN WPP 2024 | `POP_2025_BN` |
| Population 2047 | Uniform(1.58, 1.70) bn around the UN median 1.667 bn | UN median; the interval is our assumption | `POP_2047_RANGE_BN` |
| Electrification uplift `u` | Uniform(0, 0.3 pp a year) | Assumption | `ELECTRIFICATION_UPLIFT` |
| Regional difference shrink | 0.5, capped at 1.5 pp | Assumption | `REGIONAL_SHRINK`, `DIFF_CLIP` |

### 3.4 Scenarios

| Scenario | GDP growth start | GDP growth 2047 | Result (India 2047, P10 / P50 / P90 TWh) |
|---|---|---|---|
| Main (all uncertainty) | N(7.0%, 1.0) | N(5.5%, 1.0) | 4,942 / 6,506 / 8,757 |
| Low growth (~5%) | N(6.0%, 0.4) | N(4.0%, 0.4) | 4,239 / 5,119 / 6,196 |
| Base (~6-6.5%) | N(6.8%, 0.4) | N(5.5%, 0.4) | 5,096 / 6,423 / 8,104 |
| High: Viksit Bharat (~7.5-8%) | N(8.0%, 0.4) | N(7.0%, 0.4) | 6,328 / 8,401 / 11,131 |

In the named scenarios everything else (elasticity, fade, population, uplift) keeps its uncertainty; only the GDP path is pinned.

### 3.5 Sensitivities

Eight one-at-a-time cases (`forecast_yearly_sensitivity.csv`): baseline, no elasticity fade, 40% fade, no uplift, uplift 0.3 pp, faster urbanization (+0.15 pp on top of uplift, assumption), GDP growth -1 pp, +1 pp.

### 3.6 Validation

`model_benchmark.py` and `model_comparison.py` compare the model with trend extrapolation on held-out years. **Result: simple trends are as accurate or better on the 9 national observations available** (mean error about 5.5% versus 7.2-7.5% for our structure with trended drivers; 5.6% with the true drivers). We keep the driver structure because it answers the scenario questions the brief asks; see `03_data_backed_rationale.md`, Part A4.

## 4. Step 2: regional generation mix (`step2_mix_model.py`)

### 4.1 Steps in order

1. **Base mix** (`step2_base_mix.py`). Split FY2025-26 generation by region into coal, gas, nuclear, hydro (large plus small), solar, wind and a small "other RE" line (biomass, bagasse, waste, about 0.4%). Gas comes from station reports; coal is thermal minus gas (diesel stays inside coal).
2. **Take the regional totals from Step 1** (P50 for the central run; a random point between P10 and P90 for each draw).
3. **Set national paths** for each source (Section 4.2). Coal takes whatever generation is left, so national totals always match Step 1.
4. **Score each region for each source** with seven factors (Section 4.3). Increments of a source go to regions in proportion to `exp(4 * score)`; decreases are taken first where the score is low and current output is large.
5. **Balance** the table with a matrix-balancing step (RAS, 200 iterations per round, up to 12 rounds when a ceiling binds), so that every region's sources add to its Step 1 total and every source's regions add to its national path, within ceilings.
6. **Repeat** for 4 growth scenarios x 6 policy variants x (1 central + 150 random draws).
7. **Tidy** (`step2_six_vectors.py`): spread the small "other RE" line pro rata over the six required sources; write central values and P10/P50/P90 ranges.
8. **Check** (`step2_policy_check.py`): grid CO2 intensity against net-zero paths.

### 4.2 National paths

| Source | Rule | Parameters |
|---|---|---|
| Nuclear | `base + (target - base) * (k/21)^p`, `k` = years after 2026 | Target 9% of 2047 generation in the Main variant (the organisers' statement; draws 7-10%), or 700 TWh (100 GW at about 80%) in the ambition variants; exponent `p` = 1.5 (draws 1.2-2.0). Policy variants follow 157 TWh (22.38 GW) by 2032, then a straight line to the target |
| Hydro | `normal-year level * (1+g)^k`, capped at 98% of the ceiling | Base is the five-year mean (FY2021-22 to FY2025-26) so one wet or dry year is not extrapolated; `g` = 2.2% (draws 1.2-3.2%) |
| Gas | `base * (1+g)^k` | `g` = 0.5% (draws -1% to +2%) |
| Other RE | `base * (1+g)^k` | `g` = 1.5% (draws 0-3%) |
| Wind + solar | Previous year's output plus a yearly increment that starts at 54 TWh and grows 10% a year (draws 6-14%); at least the policy floor in the policy variants; never above the integration ceiling and never so large that coal would fall faster than allowed | Integration ceiling: 30% of generation in 2027 rising linearly to 65% in 2047 (draws 55-75%); also limited by the physical ceilings in Section 4.4 |
| Solar / wind split | Solar takes 65% (draws 55-75%) of wind+solar; wind is capped by its ceiling and any surplus goes to solar | |
| Coal | Balancing: `total - all other sources` | No closures before 2030 (decline at most 1% a year), then at most 6% a year (assumption) |
| Net-zero cap (Net-zero variant only) | Grid CO2 intensity must stay below `EI0 * (1 - (year-2026)/44)^1.5` | `EI0` = 0.668 t/MWh (FY2025-26); the exponent shapes how front-loaded the path is (our assumption) |

### 4.3 The seven-factor score

`score(source, region) = sum of weight * factor` with weights **cost 22%, resource 22%, environment 13%, energy security 9%, infrastructure 14%, policy direction 10%, land 10%** (`W_MEAN`). Each factor is on a 0-1 scale.

| Factor | Definition | Basis |
|---|---|---|
| Cost | `1 - (cost - lowest) / (highest - lowest)` over sources, using the midpoint of each cost range (Rs/kWh) | Coal 4.78-6.0 (Ember 2025); gas 6-9 (assumption); nuclear 3.0-5.92 (press reports); hydro 4-6 (Powerline 2025); solar 2.48-2.70 (SECI/state auctions 2025); wind 2.7-3.5 (assumption); other RE 5-7 (assumption). Solar and wind carry a 0.7 Rs/kWh firming adder. With a carbon price the cost of coal and gas rises by `price * emission factor / 1000` |
| Resource | Region's share of national potential, rescaled so the best region is 1. Coal: Mt; hydro: MW; wind: GW at 120 m. **Solar: irradiance**, `0.2 + 0.8 * (GHI - min)/(max - min)` (physical, no capacity). Gas and other RE: current generation. Nuclear: 0.6, 0.8, 0.8, 0.4, 0 for North, West, South, East, NorthEast | Resource-potential weights are allowed by the organisers; the nuclear site values are **our assumption** (coastal or river water, seismic zone; NorthEast is seismic zone V) |
| Environment | `1 - emission factor / 0.95`, minus 0.25 for hydro (forest, resettlement) and 0.10 for nuclear (waste, siting) | Emission factors: coal 0.95, gas 0.45 t/MWh (IPCC default fuel factor divided by plant efficiency); penalties are our assumption |
| Energy security | Coal: `0.3 + 0.7 *` region's relative coal resource; gas: 0.2 (0.6 in NorthEast, where gas is domestic); nuclear 0.6; hydro, solar, wind, other RE: 1 | Assumption |
| Infrastructure | How established the source already is in the region: `(regional share / national share) / 2`, capped at 1 | Computed from the base mix |
| Policy direction | Coal `0.5 - 0.5 f`, gas `0.5 - 0.25 f`, all others `0.5 + 0.5 f`, with `f = k/21` | Net-zero-2070 direction; assumption |
| Land | `1 - intensity * (1 - land available)`; land available is the region's area per person rescaled 0-1; intensity: solar 1.0, other RE 0.9, hydro 0.8, coal 0.5, wind 0.4, gas 0.1, nuclear 0.1 | Census 2011 area per person; intensities are our relative ranking |

The sharpness of the regional preference is `TEMP = 4`.

### 4.4 Ceilings

| Ceiling | Value | Basis |
|---|---|---|
| Hydro, by region | exploitable potential (MW) x 0.60 load factor x 0.60 usable x 8.76 | CEA potential; the 60% load factor is **not yet verified**; 60% usable is our assumption |
| Wind, by region | potential at 120 m (GW) x 0.30 load factor x 0.50 usable x 8,760 | NIWE potential; the rest is assumed |
| Solar, national | 3,343 GWp x 0.20 load factor x 0.40 usable x 8,760 | NISE 2025 national potential; usable share assumed |
| Solar, by region | At most the integration ceiling times the region's generation; at most 30% in the NorthEast | Hilly, cloudy terrain (assumption) |

### 4.5 Policy variants

Each variant overrides some of the settings above. Every variant is run under all four growth scenarios.

| Variant | Overrides |
|---|---|
| Main (policy-weighted, nuclear about 9%) | None (the defaults above) |
| Current policies (NEP/NGAP targets) | Wind+solar floor of 887 TWh in 2032 and 1,388 TWh in 2036 (320 GW + 103 GW and 509 GW + 155 GW converted with load factors of 22% solar and 30% wind); nuclear path via 157 TWh in 2032 |
| Net-zero aligned | The above plus the grid CO2 cap, carbon price Rs 1,000/t, integration ceiling to 80% by 2047, 60% solar and 80% wind potential usable, ramp 12%/yr, nuclear 700 TWh |
| Viksit Bharat build-out | The policy floor, nuclear 700 TWh, integration ceiling 75%, 50% solar and 65% wind potential usable, ramp 12%/yr, carbon price Rs 500/t |
| Nuclear ambition (100 GW) | Nuclear 700 TWh in 2047 |
| Without resource-potential weights | The resource weight is set to zero and the others renormalised |

Nuclear is anchored to the Main-scenario median 2047 total in every scenario, because it is build-limited rather than demand-driven.

## 5. Dashboard methodology (`docs/`, source in `dashboard_src/`)

| Part | How it works |
|---|---|
| Saved views | All charts, the map, the KPI tiles, tables and the policy check read `docs/data.json`, built by `build_dashboard_data.py` from `outputs/*.csv`. Nothing is computed on a server |
| Map | State outlines (public-domain GeoJSON), simplified and grouped into the five regions; Lakshadweep is shown as schematic dots; the colour scale runs from the lowest to the highest region for the chosen metric |
| Model lab | JavaScript ports of the Step 1 and Step 2 equations (`lab.js`), driven by constants exported to `docs/consts.json`. Step 1 uses 4,000 draws by default; Step 2's central run is instant, and its band uses 20 to 80 draws |
| "Use Model-lab results in all views" | Replaces the saved scenario and variant with the lab's result for the selected scenario and variant; other variants stay saved |
| Validation of the ports | With the Main settings the live Step 1 India 2047 median is within about 0.1% of the Python value (6,500 vs 6,506 TWh) and the live Step 2 mix matches the Python central mix within about 1 TWh. Random numbers differ, so bands differ slightly |
| Population per region | Derived: the supplied 2024 regional shares scaled to the UN national path, with each region's growth difference. Indicative only |
| Urbanization slider | Adds extra growth per year, optionally weighted by each region's 2011 urban share relative to the national share. This is a labelled assumption, not an estimate |

## 6. Uncertainty statements

- **P10-P90 band (Step 1).** Ten per cent of the 20,000 simulated futures end below the P10 and ten per cent above the P90. It reflects uncertainty in the inputs listed in Section 3.3. It is **not** a statistical confidence interval of the model, and it does not include uncertainty about the model structure or future policy shocks.
- **Scenario spread.** Low, Base and High pin the GDP path; the remaining uncertainty is still sampled.
- **P10-P90 band (Step 2).** Ten per cent of 150 draws fall outside it. Draws vary the demand quantile (within Step 1's range), the national rules (Section 4.2 ranges) and the score weights (Dirichlet with the default weights x 40). The ranges are assumptions; they are not estimated from data.
- **Conditional, not predictive.** The mix is a plan conditional on the assumptions, not a forecast of what will happen. The national split is driven mostly by the wind and solar ceilings (how much of the potential is usable and how fast wind and solar can grow); the regional pattern is driven by the score.
- **Backtest.** The history is too short (9 national observations) to claim that the model is more accurate than a trend; see Section 3.6.

## 7. Assumption register

| # | Assumption | Value | Type | Where to change it |
|---|---|---|---|---|
| 1 | Elasticity fade | 0-20% by 2047 | Assumed | `forecast_2047.py`: `ELASTICITY_FADE`; dashboard lab slider |
| 2 | GDP growth path | 7.0% to 5.5% (sd 1.0) | Assumed | `GDP_START`, `GDP_END`; lab sliders |
| 3 | 2047 population interval | 1.58-1.70 bn | Assumed (median from UN) | `POP_2047_RANGE_BN`; lab sliders |
| 4 | Electrification uplift | 0-0.3 pp/yr | Assumed | `ELECTRIFICATION_UPLIFT`; lab slider |
| 5 | Urbanization effect | none by default; slider 0-0.5 pp/yr | Assumed | lab slider; sensitivity in `forecast_2047.py` |
| 6 | Regional difference persistence | half, capped at 1.5 pp | Assumed | `REGIONAL_SHRINK`, `DIFF_CLIP` |
| 7 | Nuclear in 2047 | 9% of generation, or 700 TWh | Organisers' statement; 700 TWh is a labelled scenario | `NUC_MAIN_SHARE`, `NUC_AMBITION_GWH`; lab slider |
| 8 | Wind+solar ramp | 54 TWh start, 6-14% growth | Data start, assumed growth | `PAR_CENTRAL`; lab slider |
| 9 | Integration ceiling | 30% to 65% of generation (80% net-zero) | Assumed stand-in for storage and grid | `PAR_CENTRAL`, `VAR`; lab slider |
| 10 | Usable share of solar / wind potential | 40% / 50% | Assumed | `SOLAR_USABLE`, `WIND_USABLE`; lab sliders |
| 11 | Hydro ceiling and growth | 60% load factor (unverified), 60% usable, 1.2-3.2% a year | Partly assumed | `HYDRO_CF`, `HYDRO_USABLE`; lab slider |
| 12 | Coal decline limits | -1% a year to 2030, then -6% | Statement verified; the 6% is assumed | `coal_min` in `run()` |
| 13 | Score weights | 22/22/13/9/14/10/10 | Judgement | `W_MEAN`; lab sliders |
| 14 | Costs | see Section 4.3 | Published for coal, solar, hydro, nuclear; assumed for gas, wind, other RE | `COST` |
| 15 | Emission factors | coal 0.95, gas 0.45 t/MWh | Standard values | `EF` |
| 16 | Nuclear site suitability | 0.6, 0.8, 0.8, 0.4, 0 | Assumed | `R[nuclear]` |
| 17 | NorthEast solar cap | 30% of its generation | Assumed | `NE_SOLAR_MAX_SHARE` |
| 18 | Load factors for converting policy plans | solar 22%, wind 30% | Assumed | `SOL_CF_POLICY`, `WIND_CF_POLICY` |
| 19 | Carbon price | Rs 1,000/t (net-zero), Rs 500/t (Viksit Bharat) | Assumed, illustrative | `VAR` |
| 20 | Net-zero path shape | exponent 1.5 | Assumed (the 2070 target is verified) | `ei_p` |

## 8. Known limitations

1. The 60% hydro load factor and the capacity plans (from secondary summaries) are not yet checked against primary sources.
2. The FY2025-26 coal base used here (about 1,281 TWh) differs from the Climate Action Tracker figure (1,162 TWh) and has not been reconciled.
3. East and NorthEast wind potential is absent from the data, so those regions receive almost no wind. NorthEast gas falls from 23% to under 1% because of the balancing step, not by design; NorthEast shares should be read with caution because the region is small.
4. State-level solar potential and forest cover could not be retrieved; solar uses irradiance and forest cover is omitted.
5. No numeric storage target was found in the draft National Electricity Policy 2026 summaries, so storage is represented only by the integration ceiling.
6. In the Main growth scenario coal still rises in absolute terms (to about 2,430 TWh in 2047) while its share falls. Only the net-zero variant and the low-growth scenario reduce it in absolute terms.
7. The model lab and the Python models use different random numbers, so bands differ slightly.

## 9. Reproducibility

- Fixed seeds (`SEED = 2047` in Step 1, `RNG_SEED = 2047` in Step 2) give identical results on rerun.
- `run_all.sh` regenerates every output in about 10 minutes on a CPU; the exact commands, the quick test and the expected numbers are in the README.
- Every assumption in Section 7 is a named constant at the top of its script, so a reviewer can change a value, rerun, and compare.

## 10. Glossary

| Term | Meaning |
|---|---|
| Generation | Electricity produced, in GWh or TWh (1 TWh = 1,000 GWh). The basis of this work |
| CEA regions | North, West, South, East and NorthEast, as grouped by the Central Electricity Authority |
| Elasticity | Percentage change in electricity generation per person for a 1% change in income per person |
| P10 / P50 / P90 | The values below which 10%, 50% and 90% of the simulated outcomes fall |
| Monte Carlo | Running a model many times with randomly drawn inputs to see the spread of outcomes |
| RAS (matrix balancing) | Scaling the rows and columns of a table until both sets of totals match |
| Integration ceiling | The maximum share of generation that wind and solar can take, standing in for storage and grid limits |
| NEP / NGAP | National Electricity Plan / the CEA's generation addition plan |
