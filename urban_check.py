# Urbanization check. WHY: helpers asked whether urbanization adds value. Source: Census of India 2011,
# Table A-1 (provided by the team lead from the official release). Urban share = urban pop / total pop, by state,
# rolled up to CEA regions, then compared with income per person (GSDP/pop) from the provided dataset.
import pandas as pd, numpy as np, re, sys
sys.path.insert(0, ".")
from forecast_2047 import STATE_TO_REGION
x = pd.read_excel("census2011_A1.xlsx", header=None, skiprows=5)
x = x[[0,1,2,3,4,5,10]]; x.columns = ["st","dist","sub","level","name","tru","pop"]
x = x[(x.level=="STATE") & (x.dist.astype(str)=="000")].copy()
x["name"] = x.name.astype(str).str.replace(r"[\s@$#*]+$","",regex=True).str.replace(r"\s*@&$","",regex=True).str.strip().str.title().str.replace(" & "," And ")
p = x.pivot_table(index="name", columns="tru", values="pop", aggfunc="first")
p["urban_share"] = p["Urban"]/p["Total"]
print(p.shape); 
alias = {"Nct Of Delhi":"Delhi","Jammu And Kashmir":"Jammu And Kashmir","Andaman And Nicobar Islands":"Andaman And Nicobar Islands","Dadra And Nagar Haveli":None,"Daman And Diu":None}
p.index = [alias.get(i,i) for i in p.index]; p = p[[i is not None for i in p.index]]
# Telangana was part of Andhra Pradesh in 2011 -> assign AP's value to both (flagged limitation).
if "Telangana" not in p.index and "Andhra Pradesh" in p.index: p.loc["Telangana"]=p.loc["Andhra Pradesh"]
missing = set(STATE_TO_REGION)-set(p.index); print("unmatched dataset states:", missing)
p["region"] = [STATE_TO_REGION.get(i) for i in p.index]
r = p.dropna(subset=["region"]).groupby("region")[["Urban","Total"]].sum()
r["urban_share"]=r.Urban/r.Total
d = pd.read_csv("renewable_energy_dataset.csv", usecols=["State","Year","Population","GSDP (crore INR)"])
d = d[d.Year==2011].set_index("State")
d["ipp"] = d["GSDP (crore INR)"]/d["Population"]
s = p.join(d[["ipp"]], how="inner").dropna(subset=["ipp"])
print(r.round(3)); print("states n=",len(s))
print("corr(urban share, ln income/person) states:", round(np.corrcoef(s.urban_share, np.log(s.ipp))[0,1],2))
print("India urban share:", round(p.loc[[i for i in p.index if i!='Telangana'],'Urban'].sum()/p.loc[[i for i in p.index if i!='Telangana'],'Total'].sum(),4))
s[["urban_share","ipp","region"]].sort_values("urban_share").round(3).to_csv("outputs/urban_share_by_state_2011.csv")
r.round(4).to_csv("outputs/urban_share_by_region_2011.csv")
