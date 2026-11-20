/* Live ports of the two Python models (forecast_2047.py, step2_mix_model.py). Same equations, JS random numbers. */
const Lab=(()=>{
const rng=seed=>{let a=seed>>>0;return()=>{a=(a+0x6D2B79F5)|0;let t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296}};
const normal=r=>{let u=0;while(!u)u=r();const v=r();return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v)};
const gamma=(k,r)=>{if(k<1){return gamma(k+1,r)*Math.pow(r(),1/k)}const d=k-1/3,c=1/Math.sqrt(9*d);for(;;){let x,v;do{x=normal(r);v=1+c*x}while(v<=0);v=v*v*v;const u=r();if(Math.log(u)<.5*x*x+d-d*v+d*Math.log(v))return d*v}};
const dirichlet=(a,r)=>{const g=a.map(x=>gamma(x,r)),s=g.reduce((p,q)=>p+q,0);return g.map(x=>x/s)};
const clip=(x,a,b)=>Math.min(b,Math.max(a,x));
const U=(r,a,b)=>a+(b-a)*r();
const quant=(s,q)=>{const p=(s.length-1)*q,i=Math.floor(p),f=p-i;return s[i]+((s[Math.min(i+1,s.length-1)])-s[i])*f};

/* ---------- Step 1 ---------- */
// P: {gdpStart:[m,sd], gdpEnd:[m,sd], gdpShift, beta, betaSd, fade:[lo,hi], uplift:[lo,hi], pop47:[lo,hi]}; band=[lo,hi] quantile fractions
function step1(C,P,n,seed,band){
  const c=C.s1,T=21,r=rng(seed),store=Array.from({length:6},()=>Array.from({length:T},()=>new Float32Array(n)));
  for(let d=0;d<n;d++){
    const P47=U(r,P.pop47[0],P.pop47[1]),gpn=Math.log(P47/c.pop25)/22;
    const g0=clip(P.gdpStart[0]+(P.gdpShift||0)+P.gdpStart[1]*normal(r),c.gdpClip[0],c.gdpClip[1]);
    const g1=clip(P.gdpEnd[0]+(P.gdpShift||0)+P.gdpEnd[1]*normal(r),c.gdpClip[0],c.gdpClip[1]);
    const beta=clip(P.beta+P.betaSd*normal(r),c.betaClip[0],c.betaClip[1]);
    const f=P.fadeFixed!=null?P.fadeFixed:U(r,P.fade[0],P.fade[1]);
    const u=P.upliftFixed!=null?P.upliftFixed:U(r,P.uplift[0],P.uplift[1]);
    for(let i=0;i<5;i++){let cum=0;
      for(let t=1;t<=T;t++){const frac=(t-1)/(T-1),fd=1-t/T;
        const gp=gpn+c.dpop[i]*fd,gdp=g0+(g1-g0)*frac,gy=(gdp-gpn)+c.delta[i]*fd;
        const e=beta*(1-f*frac),ramp=Math.min(1,t/5);
        cum+=e*gy+gp+u*ramp+(P.urb||0)*(P.urbW===false?1:c.urb[i]/c.urbNat)*ramp;const v=c.anchor[i]*Math.exp(cum)/1000;
        store[i][t-1][d]=v;store[5][t-1][d]+=v}}}
  const out=[];
  for(let i=0;i<6;i++){const o={lo:[],p10:[],p50:[],p90:[],hi:[]};
    for(let t=0;t<T;t++){const s=Float64Array.from(store[i][t]).sort();o.lo.push(quant(s,band[0]));o.hi.push(quant(s,band[1]));o.p10.push(quant(s,.1));o.p50.push(quant(s,.5));o.p90.push(quant(s,.9))}
    out.push(o)}
  return out}   // order: North, West, South, East, NorthEast, India

/* ---------- Step 2 ---------- */
const SI={coal:0,gas:1,nuclear:2,hydro:3,solar:4,wind:5,other_re:6};
function ras(X0,rows,cols,caps){
  const nS=rows.length,nR=cols.length;let X=X0.map(r=>r.slice());const fixed=X0.map(r=>r.map(()=>false));
  for(let outer=0;outer<12;outer++){
    const Xf=X0.map((r,i)=>r.map((v,j)=>fixed[i][j]?0:v));
    const rt=rows.map((v,i)=>v-X[i].reduce((a,x,j)=>a+(fixed[i][j]?x:0),0));
    const ct=cols.map((v,j)=>v-X.reduce((a,row,i)=>a+(fixed[i][j]?row[j]:0),0));
    for(let it=0;it<200;it++){let ch=0;
      for(let i=0;i<nS;i++){let rs=0;for(let j=0;j<nR;j++)rs+=Xf[i][j];for(let j=0;j<nR;j++){const nv=rs>0?Xf[i][j]*rt[i]/rs:0;ch=Math.max(ch,Math.abs(nv-Xf[i][j]));Xf[i][j]=nv}}
      for(let j=0;j<nR;j++){let cs=0;for(let i=0;i<nS;i++)cs+=Xf[i][j];for(let i=0;i<nS;i++){const nv=cs>0?Xf[i][j]*ct[j]/cs:0;ch=Math.max(ch,Math.abs(nv-Xf[i][j]));Xf[i][j]=nv}}
      if(ch<1e-7)break}
    for(let i=0;i<nS;i++)for(let j=0;j<nR;j++)if(!fixed[i][j])X[i][j]=Xf[i][j];
    let any=false;for(let i=0;i<nS;i++)for(let j=0;j<nR;j++)if(!fixed[i][j]&&X[i][j]>caps[i][j]+1e-6){X[i][j]=caps[i][j];fixed[i][j]=true;any=true}
    if(!any)break}
  return X}

function policyF(s,k){const f=k/21;return s===0?.5-.5*f:s===1?.5-.25*f:.5+.5*f}
function cfVec(c,price){const m=c.costMid.map((x,i)=>x+price*c.EF[i]/1000),lo=Math.min(...m),hi=Math.max(...m);return m.map(x=>1-(x-lo)/(hi-lo))}
function scores(c,w,k,useRes,CFv){
  w=w.slice();if(!useRes)w[1]=0;const sw=w.reduce((a,b)=>a+b,0);w=w.map(x=>x/sw);
  return c.R.map((_,i)=>c.R[i].map((_,j)=>w[0]*CFv[i]+w[1]*c.R[i][j]+w[2]*c.E[i]+w[3]*c.Sec[i][j]+w[4]*c.I[i][j]+w[5]*policyF(i,k)+w[6]*c.LAND[i][j]))}
const sum=a=>a.reduce((x,y)=>x+y,0);

// T: {2027:[5 GWh],...}; par: national-rule parameters; w: 7 weights. Returns {year: 7x5 GWh}
function step2(C,T,par,w,useRes){
  const c=C.s2,YEARS=[];for(let y=2027;y<=2047;y++)YEARS.push(y);
  const G0=c.G0,G0s=G0.map(sum),h5s=sum(c.h5);let prev=G0.map(r=>r.slice());prev[3]=c.h5.slice();let natPrev=prev.map(sum);
  let vreInc=par.A0;const cfv=cfVec(c,par.carbon||0);
  const capw=c.windPot.map(x=>x*c.windCF*(par.wind_usable??c.windUsable)*8760),capwS=sum(capw);
  const capS=c.solNat*c.solCF*(par.sol_usable??c.solUsable)*8760,capHs=sum(c.capHyd);
  const out={};
  for(const y of YEARS){
    const k=y-2026,rows=T[y],Tn=sum(rows);
    let nuc;
    if(par.nuc2032){nuc=k<=6?G0s[2]+(par.nuc2032-G0s[2])*Math.pow(k/6,1.5):par.nuc2032+(par.nuc2047-par.nuc2032)*(k-6)/15}
    else nuc=G0s[2]+(par.nuc2047-G0s[2])*Math.pow(k/21,par.nuc_exp);
    const hyd=Math.min(h5s*Math.pow(1+par.g_hyd,k),.98*capHs),gas=G0s[1]*Math.pow(1+par.g_gas,k),oth=G0s[6]*Math.pow(1+par.g_oth,k);
    if(k>1)vreInc*=(1+par.lam);
    const vrePrev=natPrev[4]+natPrev[5];let vreRamp=vrePrev+vreInc;
    if(par.floor){const f=y<=2032?c.VRE0+(c.POL2032-c.VRE0)*(y-2026)/6:y<=2036?c.POL2032+(c.POL2036-c.POL2032)*(y-2032)/4:0;vreRamp=Math.max(vreRamp,f)}
    const iota=par.iota0+(par.iota47-par.iota0)*k/21,vreCap=Math.min(iota*Tn,.98*capwS+capS);
    const coalMin=natPrev[0]*(y<=2030?.99:.94),vreRoom=Tn-nuc-hyd-gas-oth-coalMin;
    let vre=Math.max(Math.min(vreRamp,vreCap,vreRoom),0);
    if(par.ei_p!=null&&par.ei_p!==false){const capEi=c.EI0*Math.pow(Math.max(1-(y-2026)/44,0),par.ei_p),coalMax=(capEi*Tn-gas*c.EF[1])/c.EF[0];
      if(Tn-nuc-hyd-gas-oth-vre>coalMax)vre=Math.max(Math.min(Math.max(vre,Tn-nuc-hyd-gas-oth-coalMax),vreCap,vreRoom),0)}
    const wnd=Math.min(vre*(1-par.sol_share),.98*capwS),sol=Math.min(vre-wnd,capS),coal=Tn-nuc-hyd-gas-oth-sol-wnd;
    const cols=[coal,gas,nuc,hyd,sol,wnd,oth];
    const S=scores(c,w,k,useRes,cfv),TEMP=par.TEMP??c.TEMP,A=S.map(r=>r.map(v=>Math.exp(TEMP*v)));
    const X0=prev.map(r=>r.map(()=>0));
    for(let i=0;i<7;i++){const d=cols[i]-sum(prev[i]);
      if(d>=0){const a=A[i].map((v,j)=>i===2?v*(c.R[i][j]>0?1:0):v),s=sum(a);for(let j=0;j<5;j++)X0[i][j]=prev[i][j]+d*a[j]/s}
      else{const a=S[i].map((v,j)=>Math.exp(-TEMP*v)*Math.max(prev[i][j],1e-9)),s=sum(a);for(let j=0;j<5;j++)X0[i][j]=Math.max(prev[i][j]+d*a[j]/s,0)}}
    const caps=X0.map(r=>r.map(()=>1e12));caps[3]=c.capHyd.slice();caps[5]=capw.slice();
    caps[4]=rows.map((rw,j)=>Math.min(iota,c.neSol*(j<4?9:1))*rw);
    const cur=ras(X0,cols,rows,caps);out[y]=cur;prev=cur;natPrev=cur.map(sum)}
  return out}

/* parameter helpers */
function basePar(C,ui){const c=C.s2,p=Object.assign({},c.PAR);
  Object.assign(p,{nuc2047:ui.nuc2047,iota47:ui.iota47,lam:ui.lam,g_hyd:ui.g_hyd,g_gas:ui.g_gas,carbon:ui.carbon,TEMP:ui.TEMP,sol_usable:ui.sol_usable,wind_usable:ui.wind_usable});
  if(ui.floor){p.floor=true;p.nuc2032=157000}
  if(ui.netzero)p.ei_p=1.5;return p}
function drawPar(r,p0){const p=Object.assign({},p0);
  p.lam=U(r,p0.lam-.04,p0.lam+.04);p.iota47=U(r,p0.iota47-.10,p0.iota47+.10);p.sol_share=U(r,.55,.75);
  p.g_hyd=U(r,Math.max(p0.g_hyd-.01,0),p0.g_hyd+.01);p.g_gas=U(r,p0.g_gas-.01,p0.g_gas+.015);p.g_oth=U(r,0,.03);p.nuc_exp=U(r,1.2,2.0);
  p.nuc2047=p0.nuc2047*(p0.nuc2047>=600000?U(r,.9,1):U(r,.78,1.11));return p}
function totalsAtU(S1,u){const T={};for(let t=0;t<21;t++){T[2027+t]=[0,1,2,3,4].map(i=>{const q=S1[i],x=u<=.5?q.p50[t]+(q.p50[t]-q.p10[t])*(u-.5)/.4:q.p50[t]+(q.p90[t]-q.p50[t])*(u-.5)/.4;return Math.max(x,.001)*1000})}return T}
// fold other_re pro rata and return {region:{source:[21 TWh]}} (India included)
function tidy(res,SRC6){const o={};const names=['North','West','South','East','NorthEast','India'];
  names.forEach(n=>{o[n]={};SRC6.forEach(s=>o[n][s]=[])});
  for(let y=2027;y<=2047;y++){const X=res[y];const reg=[];
    for(let j=0;j<5;j++){const tot=X.reduce((a,r)=>a+r[j],0),oth=X[6][j],f=tot/(tot-oth||1);reg.push(SRC6.map((s,i)=>X[i][j]*f/1000))}
    SRC6.forEach((s,i)=>{for(let j=0;j<5;j++)o[names[j]][s].push(reg[j][i]);o.India[s].push(reg.reduce((a,r)=>a+r[i],0))})}
  return o}
function step2Draws(C,S1,ui,w,useRes,n,seed,band,SRC6){
  const r=rng(seed),p0=basePar(C,ui),acc={};const names=['North','West','South','East','NorthEast','India'];
  for(let d=0;d<n;d++){const u=r(),wd=dirichlet(w.map(x=>x*40),r),T=totalsAtU(S1,u),res=step2(C,T,drawPar(r,p0),wd,useRes),t=tidy(res,SRC6);
    names.forEach(nm=>SRC6.forEach(s=>{const k=nm+'|'+s;(acc[k]=acc[k]||[]).push(t[nm][s])}))}
  const out={};
  for(const k in acc){const [nm,s]=k.split('|');out[nm]=out[nm]||{};const lo=[],hi=[],slo=[],shi=[];
    for(let t=0;t<21;t++){const v=acc[k].map(a=>a[t]).sort((a,b)=>a-b);lo.push(quant(v,band[0]));hi.push(quant(v,band[1]))}
    out[nm][s]={lo,hi}}
  return out}
return {step1,step2,basePar,totalsAtU,tidy,step2Draws,rng}})();
if(typeof module!=='undefined')module.exports=Lab;
