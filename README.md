# India Power Mix Explorer: generation forecast to 2047 and regional mix

ExxonMobil Innothon 2026 · Team 418 · Presenter: Vignesh

- **Live dashboard:** https://vvsvignesh.github.io/innothon-418-india-power-mix/
- **Everything here is generation (energy, TWh).** Installed capacity and consumption are not used to forecast or compare. Capacity plans appear in one place only: policy targets are converted to energy with stated load factors (see `outputs/step2_policy_levers.csv`).

## 1. Problem

Forecast India's electricity generation requirement to 2047 for the nation and the five CEA regions (North, West, South, East, NorthEast), propose a realistic region-specific generation mix across coal, hydro, solar, wind, nuclear and natural gas, and present both in an interactive dashboard that reviewers can trace and stress-test.

## 2. Approach

**Step 1: forecast (`forecast_2047.py`).** Each region's FY2025-26 generation (1,840 TWh for India, reconciled to CEA national totals within about 0.01%) is grown every year by

`growth = elasticity × income growth per person + population growth + EV/data-centre uplift`

- Elasticity of electricity to income: about 1.0 (CEA national data 2011-2023), allowed to fade by 0–20% by 2047.
- Income and GDP growth start near 7% and fade to 5.5% (both uncertain). Population follows the UN WPP 2024 median path (1.464 bn in 2025 to about 1.67 bn in 2047, with a 1.58–1.70 bn range that is our assumption).
- Regional differences in income and population growth are kept at half strength and fade to zero by 2047.
- 20,000 Monte Carlo draws give P10/P50/P90 bands. Four growth scenarios (Main, Low ~5%, Base ~6-6.5%, High: Viksit Bharat ~7.5-8%) and eight one-at-a-time sensitivities are provided.
- Urbanization is **not** a model driver (Census 2011 is one year and has no citable 2047 projection). It is exposed as a labelled assumption/sensitivity.

**Step 2: regional mix (`step2_mix_model.py`).**
1. National paths per source: nuclear ramps to about 9% of generation by 2047 (or 700 TWh for 100 GW in the ambition variants); hydro grows 1.2–3.2% a year from a five-year normal; gas −1% to +2% a year; wind plus solar grow as fast as a feasibility ramp and a grid/storage integration ceiling (30% to 65% of generation) allow; coal balances the rest (no closures before 2030, then at most −6% a year).
2. Regional split: each source's energy is shared across regions by a seven-factor score (cost 22%, resource 22%, environment 13%, security 9%, infrastructure 14%, policy direction 10%, land 10%) built from regional resource potential, solar irradiance, land per person, existing fleet and costs.
3. A matrix-balancing (RAS) step makes each region's sources add to its Step 1 total and each source's regions add to its national path, respecting hydro, wind and NorthEast solar ceilings.
4. 150 Monte Carlo draws vary demand, national rules and weights to give bands.
5. Six policy variants: Main, Current policies (NEP/NGAP targets), Net-zero aligned, Viksit Bharat build-out, Nuclear ambition (100 GW), and Without resource-potential weights. Each runs under all four growth scenarios.

**Step 3: dashboard (`docs/`).** A single static page (no server, no GPU) with:
- India map of the five regions (map metrics: generation, growth, source share or TWh, population, generation per person, urban share)
- Step 1 forecast with P10–P90 bands, scenario overlay and sensitivity cases
- Step 2 mix over time (area, bars or lines), regional mix in any year, source explorer with uncertainty, policy variants side by side, grid CO₂ policy check
- Filters: year (2027–2047) and year range, region, growth scenario, policy variant, compare variant, sources, units, population 2047, urbanization uplift
- A **model lab** that re-runs JavaScript ports of both models on your inputs (GDP growth, elasticity, fade, uplift, population, score weights, nuclear target, wind+solar ceiling, carbon price and more), with live P5–P95/P10–P90/P25–P75 bands, and an option to feed the lab results into every view
- Written reasoning for each region and source

## 3. Key results (Main scenario and variant)

| | 2025-26 | 2046-47 (P10 / P50 / P90) |
|---|---|---|
| India generation, TWh | 1,840 | 4,942 / 6,506 / 8,757 |

India mix in 2047 (central): coal 37%, solar 36%, wind 13%, nuclear 9%, hydro 4%, gas 0.4%. Coal still rises in absolute terms before it falls in some variants; the integration ceiling, not demand, decides how fast wind and solar can displace it. See the dashboard for regions, years and the other variants.

Biggest sensitivities of 2047 India generation: GDP growth ±1 pp (about −18% / +22%), elasticity fade 40% (about −15%), EV/data-centre uplift (about ±3%).

## 4. How to run it (for a new user)

**You need:** Python 3.10 or newer and about 200 MB of free disk. No GPU and no internet are needed to rerun the models (the data is in this repo). I tested with Python 3.13, numpy 2.5, pandas 3.0 and scipy 1.18; older versions in `requirements.txt` should also work.

### Option A: just look at the dashboard (no install)
Open the live link at the top of this README. Nothing to install.

### Option B: view the dashboard on your own computer
```bash
git clone https://github.com/VVSVIGNESH/innothon-418-india-power-mix.git
cd innothon-418-india-power-mix
python3 -m http.server -d docs 8000
```
Open http://localhost:8000 in a browser. The page reads its data files with `fetch`, so it must be opened through a web server like this; double-clicking `docs/index.html` will show an error.

### Option C: reproduce all the numbers from the raw data
```bash
git clone https://github.com/VVSVIGNESH/innothon-418-india-power-mix.git
cd innothon-418-india-power-mix
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run_all.sh                         # Windows: run the commands inside run_all.sh one by one
```
Scripts must be run **from the repo root**, because they read the CSV files in that folder and write to `outputs/`.

`run_all.sh` runs these steps in order (about 10 minutes in total, almost all of it in step 3):

| # | Command | What it does | Time | Main output |
|---|---|---|---|---|
| 1 | `python3 -I forecast_2047.py --data-dir . --out-dir outputs` | Step 1: 20,000-draw forecast, scenarios and sensitivities | seconds | `outputs/forecast_yearly_all.csv`, `forecast_sensitivity.csv` |
| 2 | `python3 -I step2_base_mix.py` | Splits FY2025-26 generation into the six sources by region | seconds | `outputs/base_mix_fy2025_26_gwh.csv` |
| 3 | `python3 -I step2_mix_model.py` | Step 2: regional mix, 4 growth scenarios × 6 policy variants × 150 draws | about 8 min | `outputs/step2_mix_yearly_central.csv`, `step2_mix_yearly_ranges.csv` |
| 4 | `python3 -I step2_six_vectors.py` | Folds the small "other renewables" line into the six sources | seconds | `outputs/step2_mix_six_vectors_*.csv`, `step2_regional_strategy_indicators.csv` |
| 5 | `python3 -I step2_policy_check.py` | Grid CO₂ intensity against the net-zero paths | seconds | `outputs/step2_policy_check.csv` |
| 6 | `python3 -I build_dashboard_data.py` | Packs the outputs for the dashboard | seconds | `docs/data.json`, `docs/consts.json` |

**Quick test (about a minute):** run steps 1 and 2 only, then open `outputs/forecast_yearly_all.csv`. For `Main (all uncertainty)`, India, year 2047, the median (`p50_twh`) should be about 6,506 TWh (P10 about 4,942, P90 about 8,757). To speed up step 3 while experimenting, lower `N_DRAWS` near the top of `step2_mix_model.py` (it is 150).

The scripts use fixed random seeds, so reruns reproduce the same numbers. The optional validation scripts (`model_benchmark.py`, `model_comparison.py`, `urban_check.py`) can be run the same way, from the repo root.

### Changing the models
- **Assumptions** are named constants at the top of `forecast_2047.py` (GDP growth, elasticity fade, EV/data-centre uplift, population range) and `step2_mix_model.py` (score weights `W_MEAN`, nuclear share, integration ceiling, cost points, policy variants in `VAR`). Change a value, rerun the steps from that script onwards, and then step 6.
- **Dashboard code** is in `dashboard_src/` (`index.src.html`, `lab.js`, `lab_ui.js`). After editing, run `cd dashboard_src && python3 build.py` and copy the new `index.html` into `docs/`.

### Deploying your own copy
Push the repo to GitHub, then Settings, Pages, "Deploy from a branch", branch `main`, folder `/docs`. The site is live at `https://<your-username>.github.io/<repo-name>/` after a minute or two.

### Troubleshooting
- *"No such file or directory: ...csv"*: you are not in the repo root. `cd` to the folder that contains `forecast_2047.py`.
- *Dashboard shows "Could not load model data"*: open it through `python3 -m http.server`, not by double-clicking the file.
- *`./run_all.sh: Permission denied`*: run `bash run_all.sh`.
- *Step 3 takes too long*: lower `N_DRAWS` (see above); results will have slightly wider noise in the bands.

## 5. Where each deliverable lives in the repository

| # | Deliverable | Where to find it |
|---|---|---|
| 1 | 2047 generation forecast model | `forecast_2047.py` (model); `outputs/forecast_*.csv` (national and 5-region P10/P50/P90 by year, scenarios, sensitivities) |
| 2 | Regional generation strategy | `step2_base_mix.py`, `step2_mix_model.py`, `step2_six_vectors.py`, `step2_policy_check.py`; results in `outputs/step2_*.csv`; shown in the dashboard's Mix and Map views |
| 3 | Data-backed rationale | `documentation/03_data_backed_rationale.md` (evidence for Step 1 and Step 2, evidence map from each claim to a file); `outputs/step2_policy_levers.csv` (policy levers with sources); validation in `model_benchmark.py`, `model_comparison.py`, `urban_check.py` |
| 4 | Transparent methodology (assumptions, methodological choices, uncertainty statements) | `documentation/04_transparent_methodology.md` (data inventory, equations, parameters, assumption register, uncertainty statements, limitations); also this README, the "why" comments in each script and the named constants at the top of each script |
| 5 | Interactive dashboard | Live: https://vvsvignesh.github.io/innothon-418-india-power-mix/ ; files in `docs/`; source in `dashboard_src/` |

## 5a. Repository layout

| Path | What it is |
|---|---|
| `documentation/` | Deliverable 3 and 4 documents |
| `forecast_2047.py` | Step 1 model |
| `step2_base_mix.py`, `step2_mix_model.py`, `step2_six_vectors.py`, `step2_policy_check.py`, `step2_summary.py` | Step 2 model and checks |
| `model_benchmark.py`, `model_comparison.py`, `urban_check.py` | Validation: our model against simpler alternatives on held-out years, and the urbanization test (why urbanization is a sensitivity, not a driver) |
| `build_dashboard_data.py` | Builds the dashboard's data files from `outputs/` |
| `outputs/` | All model outputs, including `step2_policy_levers.csv` (each policy lever with its source) |
| `docs/` | The deployed dashboard (`index.html`, `data.json`, `geo.json`, `consts.json`) |
| `dashboard_src/` | Dashboard source (`index.src.html`, `lab.js`, `lab_ui.js`); `python3 build.py` inlines the scripts into `index.html` |
| `*.csv`, `census2011_A1.xlsx` | Input data (see below) |

## 5b. Why each step was taken

| Choice | Reason |
|---|---|
| Growth-accounting model with Monte Carlo, not machine learning | Only about 30 region-years of history; a model with one defensible number (the elasticity) is inspectable and the spread of draws is the uncertainty band the brief asks for (`forecast_2047.py` header) |
| Grow from FY2025-26 actuals | Avoids extrapolating a regression intercept (`forecast_2047.py`) |
| Elasticity about 1.0, fading 0–20% | CEA 2011–2023 gives about 1.0; the fade allows for efficiency gains. A 6-year regional panel was tested and rejected as too short (`forecast_2047.py`, `model_benchmark.py`) |
| Urbanization as a sensitivity only | Census 2011 is a single year and has no citable 2047 projection (`urban_check.py`) |
| National source paths first, regions second | Policies and physical ceilings act nationally; the regional score then decides where each source goes |
| Coal as the balancing source | Whatever demand the other sources cannot meet must be met by something dispatchable; coal is the existing fleet |
| Wind+solar integration ceiling | Stands in for storage and grid build-out, for which no numeric target was found |
| Matrix balancing (RAS) | Forces regional totals to equal Step 1 and national source totals to equal the national path at the same time |
| Variants for policy | NEP/NGAP, net-zero 2070 and Viksit Bharat are shown as scenarios with their levers listed (`outputs/step2_policy_levers.csv`) rather than baked into one answer |

## 6. Data and sources

- Regional generation by source: National Power Portal monthly reports and CEA renewable generation reports (FY2018-19 to FY2025-26).
- State GSDP and population: the dataset supplied for the challenge (`renewable_energy_dataset.csv`).
- National generation 2011-2023 (elasticity): CEA, Growth of Electricity Sector in India.
- Population projections: UN World Population Prospects 2024. Urban share: Census of India 2011, Table A-1.
- Solar irradiance by state: Global Solar Atlas values (`ghi_states.csv`). Resource potential: CEA hydro, Ministry of Coal, NIWE wind (120 m).
- Policy: India's updated NDC (PIB), draft National Electricity Policy 2026 and CEA plans as reported by secondary sources, PIB nuclear statement (Feb 2026). Cost points: Ember, SECI auctions, trade press.

## 7. Assumptions and limits (disclosed)

- The 0–20% elasticity fade, the 2047 population interval, the seven score weights, load factors and several cost points (gas, standalone wind) are our assumptions and are labelled as such in the code and the dashboard.
- Wind and solar are limited by an integration ceiling that stands in for storage and grid build-out; it sets the national split. No numeric storage target was found in the draft policy.
- Capacity-plan targets come from secondary summaries and are converted to energy with load factors (solar 22%, wind 30%). Primary-source check pending.
- State-level solar potential and forest cover could not be retrieved; solar uses irradiance and forest cover is omitted. East and NorthEast wind potential is not in the data, so those regions get almost no wind.
- The 60% hydro load factor is not yet verified, our FY2025-26 coal base differs slightly from the Climate Action Tracker figure, and NorthEast gas is an artefact of small numbers.
- The in-browser model lab uses JavaScript random numbers, so results differ slightly from the saved Python run (India 2047 median 6,500 vs 6,506 TWh at default inputs).
- Regional population in the dashboard is derived by scaling the supplied 2024 regional shares to the UN national path.

## 8. Impact

The dashboard lets reviewers trace any number to its inputs, change the assumptions that matter (growth, elasticity, population, urbanization, score weights, nuclear target, integration ceiling, carbon price) and see regional trade-offs and the grid CO₂ intensity against a net-zero 2070 path, instead of reading a single fixed forecast.

## 9. Authorship and tools

The analysis, assumptions and design choices were worked out by the team. Claude (an AI assistant from Anthropic) was used to help write and test the code and the dashboard and to draft these documents; the team reviewed the outputs and takes responsibility for them.
