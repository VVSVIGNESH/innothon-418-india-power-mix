# Deliverable 3: Data-backed rationale

This document justifies the two modelling choices that matter most: how much electricity India needs to generate by FY2046-47 and region by region (Part A, Step 1), and how that generation is split across coal, hydro, solar, wind, nuclear and natural gas (Part B, Step 2). Part C maps every claim to the file in this repository that holds the evidence.

Every number is **generation (energy, TWh)**. Installed capacity and consumption are not used to forecast or compare. Where capacity-type figures appear (resource potentials as ceilings, policy capacity plans converted to energy), the text says so.

Years are labelled by the financial-year end: 2047 means FY2046-47.

---

## Part A: Step 1 rationale (the 2047 generation forecast)

### A1. What was forecast and the headline

| Quantity (India) | Value |
|---|---|
| FY2025-26 generation (last actual, base year) | 1,840 TWh (reconciled to CEA national totals within about 0.01%) |
| FY2046-47, Main scenario: P10 / P50 / P90 | 4,942 / 6,506 / 8,757 TWh |
| Implied growth, Main median | about 6% a year |
| Low growth (~5%) scenario: P10 / P50 / P90 | 4,239 / 5,119 / 6,196 TWh (about 4.9% a year) |
| Base (~6-6.5%) scenario | 5,096 / 6,423 / 8,104 TWh (about 6.0% a year) |
| High: Viksit Bharat (~7.5-8%) scenario | 6,328 / 8,401 / 11,131 TWh (about 7.2% a year) |

The same forecast is produced for the five CEA regions (North, West, South, East, NorthEast) for every year 2027-2047; see `outputs/forecast_yearly_all.csv`.

### A2. Why this model

1. **History is short.** After excluding FY2020-21 (the COVID year) the regional panel has about 30 region-years. Machine-learning models would fit noise and could not be inspected by a reviewer. A growth-accounting model has one number that matters, the electricity-to-income elasticity, and every other input is a named assumption.
2. **The drivers the brief names are inputs.** Generation growth = elasticity × income growth per person + population growth + a small EV/data-centre uplift. Population and income are drivers; urbanization is tested separately (A5).
3. **Anchoring on actuals.** Each region starts from its latest actual generation, so no regression intercept is extrapolated.
4. **Uncertainty is part of the model.** GDP growth, population, elasticity, the elasticity fade and the uplift are each drawn from a stated range 20,000 times; the spread of the paths is the P10-P90 band.

### A3. Evidence for the elasticity (about 1.0)

- CEA national generation 2011 (922 TWh) and 2023 (1,734 TWh) with population and income give a long-run elasticity of about 0.995 (code: `longrun_beta`). It is sampled with a spread of 0.15 to reflect alternative windows.
- A 6-year regional panel gave a different number and was **rejected as too short** (it is printed as a diagnostic only). Using price-adjusted income changes the estimate, which is why the choice is stated, not hidden.
- The official real-GDP series gives an elasticity of about 0.87 (about 5,640 TWh in 2047). This is disclosed as a sensitivity because the GSDP in the supplied dataset is treated as real.
- The elasticity is allowed to fade by 0-20% by 2047 for efficiency gains; a 40% fade is run as a named downside. The 0-20% range is **our assumption**, not a cited figure.

### A4. Backtest evidence (honest reading)

We compared the model with simpler alternatives on the national series (`model_benchmark.py`, `model_comparison.py`; results in `outputs/model_benchmark.csv`, `outputs/model_comparison_*.csv`).

| Test | Result |
|---|---|
| Rolling-origin backtest, 14 forecasts | Simple trend extrapolation had a mean absolute percentage error of about 5.5%; our structure with trended drivers had 7.2-7.5%; with the true (oracle) drivers it fell to 5.6% |
| Hold-out 2020-2023 | Naive trend 3.0% error; ours with trended drivers 5.7% (bias +4.1% in 2023) |

What this shows: with only 9 national observations, **a plain trend is as good as or better than our model**, and the test is indicative, not conclusive. We keep the driver model because it is the only one that can answer the brief's questions (what if GDP grows faster? what if population or urbanization differ?) and because its error mostly comes from the driver forecasts, not the structure. If a reviewer asks "does your model beat a trend?", the honest answer is "not on this short history; it matches it and adds scenarios".

### A5. Population and urbanization

- Population: UN World Population Prospects 2024 median, 1.464 bn (2025) to about 1.67 bn (2047). The 1.58-1.70 bn range used in the draws is our assumption (the UN interval was not retrieved). Regional differences in population growth come from the supplied 2019-2024 regional data and fade to zero by 2047.
- Urbanization: Census 2011 urban share by region (South 39%, West 38%, North 29%, East 21%, NorthEast 18%) correlates only moderately with income per person (r about 0.51 across states), is a single year, and has no citable 2047 projection (`urban_check.py`). It is therefore **not a model driver**. It appears as a labelled sensitivity (+0.15 pp/yr on top of the EV/data-centre range) and as the dashboard's urbanization slider.

### A6. Sensitivity: what moves the answer most

India FY2046-47 median under one change at a time (baseline about 6,500 TWh):

| Change | Result |
|---|---|
| GDP growth +1 pp | about +22% (7,928 TWh) |
| GDP growth -1 pp | about -18% (5,345 TWh) |
| Elasticity fades 40% | about -15.5% (5,497 TWh) |
| Elasticity does not fade | about +5.9% |
| Faster urbanization (+0.15 pp/yr, assumption) | about +5.8% |
| EV/data-centre uplift 0.3 pp/yr | about +2.9% |
| No EV/data-centre uplift | about -2.8% |

Conclusion: the forecast is most sensitive to long-run GDP growth, which is why it is reported as scenarios and a band, not a single line.

### A7. Limits of Step 1

The 0-20% fade, the population interval and the regional-difference shrink factor (half, capped at 1.5 pp/yr) are assumptions. The structure is not better than a trend on historical backtests (A4). The base-year regional split uses NPP/CEA reports with Bhutan imports excluded.

---

## Part B: Step 2 rationale (the regional generation mix)

*The text below is the team's Step 2 justification document, reproduced unchanged except that its headings are one level lower.*

### Summary

Step 2 splits the Step 1 generation forecast across coal, hydro, solar, wind, nuclear and gas for each of the five CEA regions and every year 2027–2047. In the headline case (current policies, median growth) India's 2047 mix is coal 37%, solar 36%, wind 13%, nuclear 9%, hydro 4% and gas under 1%, with a 10–90% range for coal of 22–52%.

The mix is a conditional plan, not a prediction. Regional patterns trace to data: coal resource, hydro and wind potential, sunshine, land per person and existing infrastructure. The national split depends on stated assumptions, chiefly how fast wind and solar can grow and how much of their potential is usable. A net-zero-aligned variant cuts coal to 16% by 2047.

| Share of generation, 2047 | Coal | Solar | Wind | Nuclear | Hydro | Gas |
| --- | --- | --- | --- | --- | --- | --- |
| India, current policies | 37% | 36% | 13% | 9% | 4% | 0.4% |
| India, net-zero aligned | 16% | 48% | 21% | 11% | 4% | 0.4% |
| North | 29% | 42% | 10% | 9% | 9% | 0% |
| West | 41% | 34% | 15% | 9% | 1% | 1% |
| South | 21% | 43% | 23% | 11% | 3% | 0% |
| East | 66% | 24% | 0% | 7% | 3% | 0% |
| Northeast | 69% | 13% | 0% | 0% | 18% | 1% |

Regional rows are the current-policies variant at median growth. Totals per region come from Step 1; shares sum to 100%.

### Method

Everything is measured in energy generated (GWh or TWh). Installed capacity and consumption are not used to forecast or compare. Capacity-type figures appear only where the organisers allowed them: resource-potential weights and a labelled nuclear scenario, plus policy capacity plans converted to energy.

1. **Start from the base year.** The FY2025-26 mix by region comes from National Power Portal and CEA generation reports and reconciles to Step 1's 1,840 TWh.
2. **Set national paths.** Nuclear ramps to 9% of generation by 2047 (confirmed by the organisers). Hydro grows 1.2–3.2% a year from a five-year normal level. Gas stays near flat. Wind and solar grow as fast as a ramp allows, starting from the latest annual addition of 54 TWh and growing 6–14% a year, capped by a share of generation (30% in 2027 rising to 65% in 2047) that stands in for storage and grid limits. Coal supplies whatever generation is left.
3. **Share each source across regions.** A seven-factor score ranks the regions for each source: cost 22%, resource 22%, infrastructure 14%, environment 13%, policy 10%, land 10%, energy security 9%. Growth goes to high-scoring regions; coal declines first where scores are low.
4. **Balance and bound.** A matrix-balancing step makes each region's sources sum to its Step 1 total and each source's regions sum to its national path, within hydro and wind resource ceilings.

Uncertainty comes from 150 random draws per case that vary demand across Step 1's range, the national rules and the factor weights. Six policy variants run under each of four growth scenarios: Main, Current policies, Net-zero aligned, Viksit Bharat build-out, Nuclear ambition and Without resource weights.

### Regional rationale

Each region's 2047 mix follows from its own resource, climate and land indicators. Indicators are from the sources listed at the end; the Northeast and East wind potential was not assessed in the data used.

| Region | Sunshine (kWh/m²/day) | Land (ha per person) | Hydro potential (MW) | Wind 120 m (GW) | Coal resource (Mt) | 2047 mix (coal / solar / wind / nuclear / hydro) | Why |
| --- | --- | --- | --- | --- | --- | --- | --- |
| North | 4.9 | 0.27 | 46,971 | 128 | 1,062 | 29 / 42 / 10 / 9 / 9 | Large hydro in the Himalayan states and the best solar potential (Rajasthan); almost no coal, so it leans on solar, hydro and nuclear. |
| West | 5.3 | 0.35 | 7,824 | 256 | 132,414 | 41 / 34 / 15 / 9 / 1 | High sunshine and wind (Gujarat, Maharashtra) beside a large coal base (Chhattisgarh, Madhya Pradesh); little hydro left to develop. |
| South | 5.3 | 0.25 | 12,570 | 268 | 27,460 | 21 / 43 / 23 / 11 / 3 | Best sunshine and the largest wind potential, little coal, and established nuclear sites: the cleanest mix. |
| East | 4.7 | 0.16 | 10,115 | not assessed | 238,071 | 66 / 24 / 0 / 7 / 3 | Holds most of India's coal, has the least land per person and lower sunshine, so coal stays central while solar grows. |
| Northeast | 4.4 | 0.56 | 55,930 | not assessed | 1,709 | 69 / 13 / 0 / 0 / 18 | Largest hydro potential but low sunshine and no assessed wind; no nuclear (seismic zone, our assumption). Hydro is limited by forest and resettlement. |

The Northeast's 69% coal is a weakness of the model, not a recommendation: its generation is small and the balancing step leaves coal as the filler. It should be read with caution.

### Policy levers

Each policy is a lever with a source and a stated use. Net-zero by 2070 and the 2022 NDC wording were checked against the official press release; the other items come from secondary sources and should be re-checked against primary documents before citing.

| Lever | Value | Source | How it is used | Status |
| --- | --- | --- | --- | --- |
| Net-zero | 2070 | [PIB, updated NDC](https://pib.gov.in/PressReleasePage.aspx?PRID=1847812) | Net-zero variant: grid CO₂ per kWh must stay under a path from 0.67 t/MWh to zero in 2070 | Target verified; path shape is our assumption |
| Emissions intensity of GDP | −45% by 2030 vs 2005 | [PIB, updated NDC](https://pib.gov.in/PressReleasePage.aspx?PRID=1847812) | Context only: economy-wide and GDP-based, so grid intensity is the generation proxy | Verified |
| Non-fossil capacity share | about 50% by 2030 | [PIB, updated NDC](https://pib.gov.in/PressReleasePage.aspx?PRID=1847812) | Not used: capacity-based | Verified |
| Solar and wind plans | 320 GW + 103 GW by 2031-32; 509 GW + 155 GW by 2035-36 | [Climate Action Tracker summary](https://climateactiontracker.org/countries/india/policies-action/) | Converted to energy (22% solar and 30% wind load factors): floor of 887 TWh in 2032 and 1,388 TWh in 2036 in the policy variants | Via secondary summary; load factors assumed |
| Nuclear | 22.38 GW by 2031-32; 100 GW by 2047 | [PIB feature, Feb 2026](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc2026228806901.pdf); [World Nuclear News](https://world-nuclear-news.org/articles/indian-government-releases-draft-energy-policy) | 9% of generation in 2047 in the main case; 100 GW × 80% = 700 TWh in ambition variants | Targets verified; load factor assumed |
| Coal | no closures planned before 2030 | [Climate Action Tracker](https://climateactiontracker.org/countries/india/policies-action/) | Coal falls at most 1% a year to 2030, then 6% a year | Statement verified; 6% assumed |
| Storage | about 236 GWh batteries by 2030 (2023 plan); storage obligation appears dropped | [Climate Action Tracker](https://climateactiontracker.org/countries/india/policies-action/) | Represented by the cap on wind and solar share of generation; no explicit storage | No numeric storage target found in the draft National Electricity Policy 2026 summaries |
| Carbon pricing | Carbon market currently excludes power | [Climate Action Tracker](https://climateactiontracker.org/countries/india/policies-action/) | Illustrative carbon price in scoring: Rs 1,000/t in net-zero, Rs 500/t in Viksit Bharat variants | Price is our assumption |
| Green hydrogen mission | 5 Mt a year by 2030 | [PIB feature, Feb 2026](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc2026228806901.pdf) | Not added to demand; sensitivity only (about 260 TWh at full delivery, 52 TWh at 20%) | Target verified; energy per kg is a standard engineering figure |
| Viksit Bharat 2047 | High-growth ambition | Step 1 scenario | High-growth demand plus a build-out variant: 12% a year wind and solar growth, 100 GW nuclear, 75% share limit | Build-out parameters are our assumptions |

### Assumption register

The national split depends mainly on the first three assumptions. In the main case, solar and wind reach their 2047 ceilings, so coal's share follows from how much potential is usable: with 60% of solar potential usable, coal falls from 37% to 29%; with 25%, it rises to 51%.

| Assumption | Value | Basis | Type |
| --- | --- | --- | --- |
| Usable share of solar potential | 40% of 3,343 GWp (60% in net-zero, 50% in Viksit Bharat) | NISE national potential; usable share is ours | Assumed |
| Usable share of wind potential | 50% of NIWE 120 m potential, seven states (80% net-zero, 65% Viksit Bharat) | NIWE potential; usable share is ours | Assumed |
| Wind and solar growth | 54 TWh a year, growing 6–14% a year (12% in Viksit Bharat) | Latest annual addition from CEA data | Data start, assumed growth |
| Wind and solar share limit | 30% in 2027 to 65% in 2047 (80% net-zero) | Stand-in for storage and grid limits | Assumed |
| Nuclear | 9% of generation in 2047 | Organisers' reply | Confirmed |
| Hydro | grows 1.2–3.2% a year; ceiling 60% of potential at 60% load factor | CEA potential; load factor basis not verified | Partly assumed |
| Coal retirement | −1% a year to 2030, then −6% a year at most | No closures before 2030 (Climate Action Tracker); 6% ours | Partly assumed |
| Factor weights | cost 22, resource 22, infrastructure 14, environment 13, policy 10, land 10, security 9 (%) | Judgement; varied in the random draws | Assumed |
| Costs (Rs/kWh) | coal 4.8–6.0; solar 2.5–2.7; hydro 4–6; nuclear 3–5.9; gas 6–9; wind 2.7–3.5; firming adder 0.7 | Published for coal, solar, hydro, nuclear; gas and wind assumed | Mixed |
| Emission factors (t/MWh) | coal 0.95, gas 0.45 | IPCC default fuel factors and typical efficiency | Standard values |
| Nuclear sites | none in the Northeast | Seismic zone V | Assumed |
| Northeast solar | at most 30% of its generation | Hilly, cloudy terrain | Assumed |

### Limits and open items

The results are scenario outputs conditional on the assumptions above. These points should be disclosed rather than defended.

- **Coal grows in absolute terms.** In the main growth scenario coal output rises to about 2,430 TWh in 2047 while its share falls. Only the net-zero variant and the low-growth scenario bring it down; under high growth, coal reaches about 4,300 TWh under current policies and about 2,500 TWh even with the net-zero rules, and the front-loaded path is missed in one year.
- **The old main case is below policy.** It reaches 698 TWh of wind and solar in 2032 against 887 TWh implied by the capacity plans, so the current-policies variant is the better headline.
- **Data gaps.** The full NISE state solar table and forest cover could not be retrieved; land is a proxy (Census 2011 area per person); sunshine values are city readings from a secondary page; there are no regional costs; East and Northeast wind potential is not assessed.
- **Unverified inputs.** The 60% load factor behind CEA hydro potential, the capacity plans (from a secondary summary) and the gas and wind costs.
- **Base difference.** Climate Action Tracker reports 2025-26 coal generation of 1,162 TWh; the National Power Portal base used here is about 1,281 TWh. This has not been reconciled.
- **Storage.** No numeric storage target was found in the draft National Electricity Policy 2026 summaries, so none is cited.
- **Northeast gas.** Gas there falls from 23% to under 1% because of the balancing step, not by design.
- **Run size.** Uncertainty uses 150 draws per case.

### Sources

Pages opened for this document:

- [India's updated NDC, PIB press release (3 Aug 2022)](https://pib.gov.in/PressReleasePage.aspx?PRID=1847812)
- [Climate Action Tracker: India policies and action](https://climateactiontracker.org/countries/india/policies-action/)
- [PIB feature: The Evolving Spectrum of Energy Sources (28 Feb 2026)](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc2026228806901.pdf)
- [World Nuclear News: Indian government releases draft energy policy](https://world-nuclear-news.org/articles/indian-government-releases-draft-energy-policy)
- [SCC Online: Draft National Electricity Policy 2026 explained](https://www.scconline.com/blog/post/2026/01/22/draft-national-electricity-policy-2026-explained/)
- [Ember: Coal's diminishing role in India's electricity transition](https://ember-energy.org/app/uploads/2025/10/Coals-diminishing-role-in-Indias-electricity-transition.pdf)
- [Powerline: hydropower tariff trends](https://powerline.net.in/2025/03/06/cost-economics-key-tariff-trends-in-the-hydropower-segment)

Other data: CEA and National Power Portal generation reports; Census of India 2011 Table A-1; Global Solar Atlas readings via a secondary page; CEA, MoC, NIWE and NISE potential figures as compiled in the project data files. Figures from memory or secondary pages are marked as such above.


---

## Part C: Evidence map (claim to file)

| Claim | Where the evidence is |
|---|---|
| 1,840 TWh base year, regional split | `regional_generation_conventional_gwh.csv`, `regional_generation_re_mu.csv`, `outputs/base_mix_fy2025_26_gwh.csv` |
| Step 1 results, bands, scenarios | `outputs/forecast_yearly_all.csv`, `forecast_scenarios.csv`, `forecast_paths_quantiles.csv`; code `forecast_2047.py` |
| Sensitivities | `outputs/forecast_sensitivity.csv`, `forecast_yearly_sensitivity.csv` |
| Elasticity and backtests | `forecast_2047.py` (`longrun_beta`, `backtest`), `model_benchmark.py`, `model_comparison.py`, `outputs/model_benchmark*.csv`, `outputs/model_comparison_*.csv` |
| Urbanization test | `urban_check.py`, `outputs/urban_share_by_region_2011.csv`, `urban_share_by_state_2011.csv`, `census2011_A1.xlsx` |
| Regional resource, climate and land indicators | `resource_indicators_state.csv`, `ghi_states.csv`, `region_climate_land.csv`, `outputs/step2_regional_strategy_indicators.csv` |
| Step 2 mix, ranges, variants | `outputs/step2_mix_six_vectors_central.csv`, `step2_mix_six_vectors_ranges.csv`; code `step2_mix_model.py` |
| Policy levers with sources | `outputs/step2_policy_levers.csv` |
| Policy check (grid CO2 against net-zero paths) | `outputs/step2_policy_check.csv`; code `step2_policy_check.py` |
| Interactive access to all of the above | the dashboard in `docs/` (live link in the README) |

For every assumption, its type, value and the place to change it, see `04_transparent_methodology.md`.
