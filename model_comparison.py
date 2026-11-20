# WHY: compare our growth-accounting model against alternative approaches using ROLLING-ORIGIN backtests
# (re-fit using only data up to an origin year, forecast the later years), on the national annual series.
# Data: national generation (CEA Growth Book 2024 Table 3); population & GSDP from the provided dataset (GSDP treated as real, beta=1 as decided).
# Years are FY start years (2011 = FY2011-12). Only 9 observations exist: 2011, 2016..2023 -> results are indicative, not conclusive.
import pandas as pd, numpy as np
gen = {2011:922451,2016:1235358,2017:1303455,2018:1371779,2019:1383417,2020:1373187,2021:1484463,2022:1617904,2023:1734375}
d = pd.read_csv("renewable_energy_dataset.csv", usecols=["Year","Population","GSDP (crore INR)"]); d=d[d.Year>=2011].groupby("Year").sum().loc[list(gen)]
d.columns=["pop","gdp"]; d["gen"]=pd.Series(gen)
L=np.log
def lin(x,y,deg=1):                      # polynomial fit in log space, returns predictor
    c=np.polyfit(x,y,deg); return lambda t: np.polyval(c,t)
def forecast_all(origin):
    tr=d.loc[:origin]; yrs=np.array(tr.index,float); te=[t for t in d.index if t>origin]; out={}
    # 1 endpoint CAGR of generation
    g=(tr.gen.iloc[-1]/tr.gen.iloc[0])**(1/(origin-2011)); out["1 Trend: endpoint CAGR"]=[tr.gen.iloc[-1]*g**(t-origin) for t in te]
    # 2 OLS log-linear trend on all training points
    f=lin(yrs,L(tr.gen)); out["2 Trend: OLS log-linear"]=[np.exp(f(t)) for t in te]
    # 3 recent-window CAGR (2016->origin) : window sensitivity
    if origin>=2018:
        g3=(tr.gen[origin]/tr.gen[2016])**(1/(origin-2016)); out["3 Trend: recent window (2016-)"]=[tr.gen[origin]*g3**(t-origin) for t in te]
    # 4 flexible: quadratic log trend (can accelerate/decelerate) - overfit check
    if len(tr)>=4: f4=lin(yrs,L(tr.gen),2); out["4 Flexible: quadratic log trend"]=[np.exp(f4(t)) for t in te]
    # 5 per-person trend x population trend
    fp=lin(yrs,L(tr.gen/tr["pop"])); fpop=lin(yrs,L(tr["pop"])); out["5 Per-person trend x pop trend"]=[np.exp(fp(t)+fpop(t)) for t in te]
    # 6 income-elasticity regression (fit beta on train), drivers trended by OLS
    xi=L(tr.gdp/tr["pop"]); yi=L(tr.gen/tr["pop"]); b,a=np.polyfit(xi,yi,1)
    fgdp=lin(yrs,L(tr.gdp)); 
    out[f"6 Regression: ln(gen/pop)~ln(gdp/pop)"]=[np.exp(a+b*(fgdp(t)-fpop(t))+fpop(t)) for t in te]
    # 7/8 OURS: growth accounting, beta=1 (our choice), drivers extrapolated by endpoint CAGR / OLS
    gp=(tr["pop"].iloc[-1]/tr["pop"].iloc[0])**(1/(origin-2011)); gy=(tr.gdp.iloc[-1]/tr.gdp.iloc[0])**(1/(origin-2011))
    ours=lambda pop,gdp,t: tr.gen[origin]*(pop/tr["pop"][origin])*(((gdp/pop)/(tr.gdp[origin]/tr["pop"][origin]))**1.0)
    out["7 OURS: beta=1, drivers=endpoint CAGR"]=[ours(tr["pop"][origin]*gp**(t-origin),tr.gdp[origin]*gy**(t-origin),t) for t in te]
    out["8 OURS: beta=1, drivers=OLS trend"]=[ours(np.exp(fpop(t)),np.exp(fgdp(t)),t) for t in te]
    # 9 ORACLE ceiling for our structure: beta=1 with actual (known) drivers - isolates structure from driver forecasting
    out["9 (oracle) OURS beta=1, actual drivers"]=[ours(d["pop"][t],d.gdp[t],t) for t in te]
    return te,out
rows=[]
for origin in [2018,2019,2020,2021]:
    te,out=forecast_all(origin)
    for m,p in out.items():
        for t,pp in zip(te,p): rows.append({"origin":origin,"model":m,"year":t,"h":t-origin,"err_%":(pp/d.gen[t]-1)*100})
r=pd.DataFrame(rows)
s=r.groupby("model").agg(MAPE=("err_%",lambda x:x.abs().mean()), bias=("err_%","mean"), worst=("err_%",lambda x:x.abs().max()), n=("err_%","size"))
s["MAPE_h<=2"]=r[r.h<=2].groupby("model")["err_%"].apply(lambda x:x.abs().mean()); s["MAPE_h>=3"]=r[r.h>=3].groupby("model")["err_%"].apply(lambda x:x.abs().mean())
print(s.round(1).sort_values("MAPE").to_string()); r.round(2).to_csv("outputs/model_comparison_rolling.csv",index=False); s.round(2).to_csv("outputs/model_comparison_summary.csv")
