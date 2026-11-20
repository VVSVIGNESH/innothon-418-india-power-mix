# WHY: show our growth-accounting model is defensible by benchmarking it against simpler alternatives on the same data.
# Series: national gross generation (CEA Growth Book 2024, Table 3) + population & GSDP (provided dataset, summed over states).
# Design: train on years <= 2019 (2011, 2016-2019), forecast 2020-2023 (4 held-out years, includes the COVID dip).
import pandas as pd, numpy as np
gen = {2011:922451,2016:1235358,2017:1303455,2018:1371779,2019:1383417,2020:1373187,2021:1484463,2022:1617904,2023:1734375}
d = pd.read_csv("renewable_energy_dataset.csv", usecols=["Year","Population","GSDP (crore INR)"]); d = d[d.Year>=2011].groupby("Year").sum().loc[list(gen)]
d["gen"] = pd.Series(gen); d.columns = ["pop","gdp","gen"]
tr, te = [2011,2016,2017,2018,2019], [2020,2021,2022,2023]
T0 = 2019; n = T0-2011
cagr = lambda s: (s[T0]/s[2011])**(1/n)-1
gg, gp, gy = cagr(d.gen), cagr(d["pop"]), cagr(d.gdp)
beta_train = np.log((d.gen[T0]/d["pop"][T0])/(d.gen[2011]/d["pop"][2011])) / np.log((d.gdp[T0]/d["pop"][T0])/(d.gdp[2011]/d["pop"][2011]))
def A(beta, cond):  # growth accounting: gen grows with pop + beta * income-per-person growth
    out={}
    for t in te:
        k=t-T0
        pop = d["pop"][t] if cond else d["pop"][T0]*(1+gp)**k
        gdp = d.gdp[t] if cond else d.gdp[T0]*(1+gy)**k
        out[t]=d.gen[T0]*(pop/d["pop"][T0])*((gdp/pop)/(d.gdp[T0]/d["pop"][T0]))**beta
    return pd.Series(out)
models = {
 "1 Naive: trend CAGR of generation":            pd.Series({t:d.gen[T0]*(1+gg)**(t-T0) for t in te}),
 "2 Per-person trend x population":              pd.Series({t:d.gen[T0]*(1+(gg-gp)/(1+gp))**(t-T0)*(d["pop"][t]/d["pop"][T0]) for t in te}),
 "3 Ours, beta=1.0, drivers KNOWN (tests structure)": A(1.0,True),
 f"4 Ours, beta fitted ({beta_train:.2f}), drivers KNOWN": A(beta_train,True),
 "5 Ours, beta=1.0, drivers TRENDED (fair forecast)": A(1.0,False),
}
rows=[]
for k,s in models.items():
    e = (s-d.gen[te])/d.gen[te]*100
    rows.append({"model":k, **{str(t):round(e[t],1) for t in te}, "MAPE_%":round(e.abs().mean(),1), "bias_2023_%":round(e[2023],1)})
r=pd.DataFrame(rows); print(r.to_string(index=False)); print(f"\ntrain CAGR: generation {gg:.2%}, pop {gp:.2%}, GDP {gy:.2%}, beta_train {beta_train:.2f}")
r.to_csv("outputs/model_benchmark.csv", index=False)
