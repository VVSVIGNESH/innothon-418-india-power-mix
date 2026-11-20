let OV=null;
const sFc=sc=>OV&&OV.s1===sc?OV.fc:D.fc[sc];
const sMix=(sc,v,r)=>(OV&&OV.s2===sc&&OV.v===v)?OV.mix[r]:D.mix[sc][v][r];
/* ---- Model lab UI (uses Lab, D, S, C, chart(), legend() from the main script) ---- */
let C=null;
const LAB={ready:false,S1:null,res:null,mix:null,draws:null,timer:null,sens:null};
const SRC6=SRC;
const WNAMES=['Cost','Resource potential','Environment','Energy security','Infrastructure','Policy direction','Land availability'];
const SL1=[['gs','GDP growth now, mean',2,10,.1,7.0,'%'],['ge','GDP growth by 2047, mean',2,10,.1,5.5,'%'],['gsd','GDP growth uncertainty (sd)',0,2,.1,1.0,' pp'],
 ['beta','Electricity elasticity β',.5,1.3,.01,.995,''],['bsd','β uncertainty (sd)',0,.3,.01,.15,''],['fade','Elasticity fade by 2047 (max)',0,60,1,20,'%'],
 ['upl','EV / data-centre uplift (max)',0,1,.05,.3,' pp/yr'],['pop','Population 2047 (middle of range)',1.5,1.8,.01,1.64,' bn'],['popw','Population 2047 range width (±)',0,.15,.01,.06,' bn'],['urb','Urbanization uplift (assumption)',0,.5,.01,0,' pp/yr']];
const SL2=[['nuc','Nuclear in 2047',100,900,10,0,' TWh'],['iota','Wind+solar share ceiling 2047 (storage/grid proxy)',30,95,1,65,'%'],['lam','Wind+solar ramp growth per year',0,20,.5,10,'%'],
 ['carbon','Carbon price on coal and gas',0,2000,50,0,' Rs/t'],['ghyd','Hydro growth per year',0,4,.1,2.2,'%'],['ggas','Gas growth per year',-2,3,.1,.5,'%'],
 ['solu','Solar land usable (share of NISE potential)',10,80,1,40,'%'],['windu','Wind potential usable',20,100,1,50,'%'],['temp','Regional sharpness (higher = winner takes more)',1,8,.5,4,'']];
const mainRef=()=>sFc('Main (all uncertainty)').India.p50[20]*1000;
const VPRE={ // overrides of the saved variants (same as step2_mix_model.py)
 'Main (policy-weighted, nuclear ~9%)':{},
 'Current policies (NEP/NGAP targets)':{floor:1},
 'Net-zero aligned':{floor:1,nz:1,amb:1,carbon:1000,iota:80,lam:12,solu:60,windu:80},
 'Viksit Bharat build-out':{floor:1,amb:1,iota:75,lam:12,solu:50,windu:65,carbon:500},
 'Nuclear ambition (100 GW)':{amb:1},
 'Without resource-potential weights':{nores:1}};
function slHTML(id,arr){return arr.map(a=>`<div class="sl"><label for="${id}${a[0]}">${a[1]} <b id="${id}${a[0]}v"></b></label><input type="range" id="${id}${a[0]}" min="${a[2]}" max="${a[3]}" step="${a[4]}" value="${a[5]}"></div>`).join('')}
function wHTML(){return WNAMES.map((n,i)=>`<div class="sl"><label for="lw${i}">Weight · ${n} <b id="lw${i}v"></b></label><input type="range" id="lw${i}" min="0" max="50" step="1" value="${Math.round(C.s2.Wmean[i]*100)}"></div>`).join('')}
const gv=id=>+$(id).value;
function readS1(){const m=gv('l1pop')||1.64,w=gv('l1popw');return {urb:gv('l1urb')/100,urbW:$('lurbw').checked,gdpStart:[gv('l1gs')/100,gv('l1gsd')/100],gdpEnd:[gv('l1ge')/100,gv('l1gsd')/100],beta:gv('l1beta'),betaSd:gv('l1bsd'),fade:[0,gv('l1fade')/100],uplift:[0,gv('l1upl')/100],pop47:[m-w,m+w]}}
function readS2(){return {nuc2047:gv('l2nuc')*1000,iota47:gv('l2iota')/100,lam:gv('l2lam')/100,carbon:gv('l2carbon'),g_hyd:gv('l2ghyd')/100,g_gas:gv('l2ggas')/100,TEMP:gv('l2temp'),sol_usable:gv('l2solu')/100,wind_usable:gv('l2windu')/100,floor:$('lfloor').checked,netzero:$('lnz').checked}}
const readW=()=>WNAMES.map((_,i)=>Math.max(gv('lw'+i),.001))
function showVals(){
  if($('tpop')){$('tpop').value=$('l1pop').value;$('turb').value=$('l1urb').value;$('tpopv').textContent=(+$('l1pop').value).toFixed(2)+' bn';$('turbv').textContent=(+$('l1urb').value).toFixed(2)+' pp/yr'}
  SL1.forEach(a=>{$('l1'+a[0]+'v').textContent=(+$('l1'+a[0]).value).toFixed(a[4]<.1?2:a[4]<1?1:0)+a[6]});
  SL2.forEach(a=>{$('l2'+a[0]+'v').textContent=(+$('l2'+a[0]).value).toFixed(a[4]<1?1:0)+a[6]});
  const w=readW(),s=w.reduce((a,b)=>a+b,0);WNAMES.forEach((_,i)=>$('lw'+i+'v').textContent=Math.round(w[i]/s*100)+'%');
}
function setS1(name){const cc=C.s1;let gs=cc.gdpStart,ge=cc.gdpEnd;if(cc.scen[name]){gs=cc.scen[name][0];ge=cc.scen[name][1]}
  $('l1gs').value=gs[0]*100;$('l1ge').value=ge[0]*100;$('l1gsd').value=gs[1]*100}
function setS2(name){const o=VPRE[name]||{},r=mainRef(),def={nuc:Math.round(.09*r/1000/10)*10,iota:65,lam:10,carbon:0,solu:40,windu:50,ghyd:2.2,ggas:.5,temp:4};
  const v=Object.assign({},def,o);if(o.amb)v.nuc=700;
  ['nuc','iota','lam','carbon','solu','windu','ghyd','ggas','temp'].forEach(k=>$('l2'+k).value=v[k]);
  $('lfloor').checked=!!o.floor;$('lnz').checked=!!o.nz;$('lres').checked=!o.nores;
  C.s2.Wmean.forEach((w,i)=>$('lw'+i).value=Math.round(w*100))}
function savedTotals(){const f=D.fc[S.sc1],n=['North','West','South','East','NorthEast','India'];return n.map(r=>({p10:f[r].p10,p50:f[r].p50,p90:f[r].p90}))}
function bandF(){return $('lband').value.split(',').map(x=>+x/100)}
function labRun(full){
  if(full!==false){LAB.S1=Lab.step1(C,readS1(),+$('ln').value,2047,bandF())}
  const T=Lab.totalsAtU(LAB.S1,.5);
  LAB.res=Lab.step2(C,T,Lab.basePar(C,readS2()),readW(),$('lres').checked);
  LAB.mix=Lab.tidy(LAB.res,SRC6);LAB.ready=true;
  if(S.useLab){LAB.draws=Lab.step2Draws(C,LAB.S1,readS2(),readW(),$('lres').checked,20,99,bandF(),SRC6);ovApply();render()}else{LAB.draws=null;ovRestore();labRender()}}
function ovRestore(){if(!OV)return;D.fc[OV.s1]=OV.fc;D.mix[OV.s2][OV.v]=OV.mix;D.rng[OV.s2][OV.v]=OV.rng;D.pol[OV.s2][OV.v]=OV.pol;OV=null}
function ovApply(){ovRestore();
  OV={s1:S.sc1,s2:S.sc2,v:S.variant,fc:D.fc[S.sc1],mix:D.mix[S.sc2][S.variant],rng:D.rng[S.sc2][S.variant],pol:D.pol[S.sc2][S.variant]};
  const nm=['North','West','South','East','NorthEast','India'],r1=v=>Math.round(v*10)/10,fc={};
  nm.forEach((r,i)=>{const q=LAB.S1[i];fc[r]={p10:q.lo.map(r1),p50:q.p50.map(r1),p90:q.hi.map(r1),g:q.p50.map((v,k)=>k?(v/q.p50[k-1]-1)*100:null)}});
  const rng={};nm.forEach(r=>{rng[r]={};SRC6.forEach(s=>{const d=LAB.draws&&LAB.draws[r]&&LAB.draws[r][s],c=LAB.mix[r][s];
    const tt=k=>SRC6.reduce((a,z)=>a+LAB.mix[r][z][k],0);
    rng[r][s]={lo:d?d.lo:c,hi:d?d.hi:c,slo:(d?d.lo:c).map((v,k)=>v/tt(k)*100),shi:(d?d.hi:c).map((v,k)=>v/tt(k)*100)}})});
  const I=LAB.mix.India,tot=k=>SRC6.reduce((a,s)=>a+I[s][k],0);
  const pol={co2:I.coal.map((v,k)=>(v*.95+I.gas[k]*.45)/tot(k)),lin:OV.pol.lin,front:OV.pol.front,vre:I.solar.map((v,k)=>v+I.wind[k]),coalg:I.coal.map((v,k)=>k?(v/I.coal[k-1]-1)*100:null)};
  D.fc[S.sc1]=fc;D.mix[S.sc2][S.variant]=LAB.mix;D.rng[S.sc2][S.variant]=rng;D.pol[S.sc2][S.variant]=pol}
function labDebounce(){showVals();clearTimeout(LAB.timer);LAB.timer=setTimeout(()=>labRun(true),180)}
function labInit(C0){
  C=C0;$('l1s').innerHTML=slHTML('l1',SL1);$('l2s').innerHTML=slHTML('l2',SL2)+'<div class="lab-h" style="margin-top:8px">Score weights (any scale; shown as % of total)</div>'+wHTML();
  $('l1p').innerHTML='<option>Main (all uncertainty)</option>'+Object.keys(C.s1.scen).map(k=>`<option>${k}</option>`).join('');
  $('l2p').innerHTML=Object.keys(VPRE).map(k=>`<option>${k}</option>`).join('');
  $('l1s').insertAdjacentHTML('beforeend','<label class="chk" style="margin:4px 0"><input type="checkbox" id="lurbw" checked> Weight urbanization by each region’s 2011 urban share</label>');
  setS1('Main (all uncertainty)');setS2(Object.keys(VPRE)[0]);showVals();
  $('l1p').onchange=e=>{setS1(e.target.value);if(D.fc[e.target.value]){S.sc1=e.target.value;sync();render()}labDebounce()};$('l2p').onchange=e=>{setS2(e.target.value);if(D.mix[S.sc2][e.target.value]){S.variant=e.target.value;sync();render()}labDebounce()};
  $('lab').addEventListener('input',e=>{if(e.target.type==='range'||e.target.type==='checkbox')labDebounce()});
  ['tpop','turb'].forEach(id=>$(id).addEventListener('input',e=>{$(id==='tpop'?'l1pop':'l1urb').value=e.target.value;S.useLab=true;$('uselab').checked=true;labDebounce()}));
  $('lurbw').onchange=()=>labDebounce();
  renderStatic();
  $('lband').onchange=$('ln').onchange=()=>labDebounce();
  $('l2run').onclick=()=>{$('l2run').textContent='Running…';setTimeout(()=>{LAB.draws=Lab.step2Draws(C,LAB.S1,readS2(),readW(),$('lres').checked,+$('l2n').value,99,bandF(),SRC6);$('l2run').textContent='Add Step 2 uncertainty';labRender()},30)};
  $('lsens').onclick=labSens;
  labRun(true)}
function labSens(){
  const base=readS1(),n=+$('ln').value,b=bandF();
  const cases=[['baseline (your inputs)',{}],['elasticity does not fade',{fadeFixed:0}],['elasticity fades 40%',{fadeFixed:.4}],['no EV/data-centre uplift',{upliftFixed:0}],['uplift 0.3 pp/yr',{upliftFixed:.003}],['faster urbanization (+0.15 pp/yr, assumption)',{upliftFixed:.0045}],['GDP growth −1 pp',{gdpShift:-.01}],['GDP growth +1 pp',{gdpShift:.01}]];
  const rows=cases.map(([nm,o])=>{const r=Lab.step1(C,Object.assign({},base,o),n,2047,b)[5];return {nm,lo:r.lo[20],p50:r.p50[20],hi:r.hi[20]}});
  const b0=rows[0].p50;const lv=$('lband').selectedOptions[0].textContent.split(' ')[0];
  $('lt5').innerHTML=`<tr><th>Case</th><th>${lv.split('–')[0]}</th><th>Median</th><th>${lv.split('–')[1]||''}</th><th>vs baseline</th></tr>`+rows.map(r=>`<tr><td>${r.nm}</td><td>${f0(r.lo)}</td><td><b>${f0(r.p50)}</b></td><td>${f0(r.hi)}</td><td class="${r.p50>=b0?'dpos':'dneg'}">${r===rows[0]?'–':((r.p50/b0-1)*100).toFixed(1)+'%'}</td></tr>`).join('');
  $('lsub5').textContent=`India FY2046-47 generation, TWh. Each case changes one input on top of your Step 1 settings and is re-run with ${n.toLocaleString()} draws; the band is ${lv}.`;
  $('lsenscard').style.display='';$('lsenscard').scrollIntoView({behavior:'smooth',block:'nearest'})}

function labRender(){
  if(!LAB.ready)return;
  const years=rangeYears(),yi=years.map(ix),yr=S.year,i=ix(yr),pct=S.unit==='pct',reg=S.region,ri=REG.indexOf(reg),ridx=ri===0?5:ri-1;
  const lv=$('lband').selectedOptions[0].textContent.split(' ')[0];
  /* check */
  const sv=sFc('Main (all uncertainty)').India.p50[20],lv0=LAB.S1[5].p50[20];
  $('labcheck').textContent=`Main settings reproduce the saved Python run: India 2047 median ${f0(lv0)} TWh live vs ${f0(sv)} TWh saved. (Check applies when the sliders sit at the Main defaults.)`;
  /* Step 1 live vs saved */
  const L1=LAB.S1[ridx],sv1=sFc(S.sc1)[reg];const col=cv('accent');
  const ser=[{vals:yi.map(k=>L1.p50[k]),lo:yi.map(k=>L1.lo[k]),hi:yi.map(k=>L1.hi[k]),color:col,w:2.6},{vals:yi.map(k=>sv1.p50[k]),color:cv('ink'),w:1.5,dash:'5 3'}];
  chart($('lc1'),{years,series:ser,ymax:Math.max(...ser[0].hi,...ser[1].vals)*1.05,yf:f0,mark:yr,tip:j=>{const k=yi[j];return `<b>${years[j]} · ${reg}</b>Live P50: ${f0(L1.p50[k])} TWh<br>${lv}: ${f0(L1.lo[k])}–${f0(L1.hi[k])}<br>Saved P50 (${S.sc1.split(' (')[0]}): ${f0(sv1.p50[k])}`}});
  legend('llg1',[['Live median with '+lv+' band',col],['Saved median ('+S.sc1.split(' (')[0]+')',cv('ink')]]);
  $('lsub1').textContent=`${reg} · TWh. Your Step 1 inputs vs the saved run.`;
  /* Step 2 live stacked */
  const m=LAB.mix[reg],act=SRC.filter(s=>S.src[s]),tt=k=>SRC.reduce((a,s)=>a+m[s][k],0);
  const st=act.map(s=>({color:srcColor(s),vals:yi.map(k=>pct?m[s][k]/tt(k)*100:m[s][k])}));
  chart($('lc2'),{years,stack:st,bars:S.ctype==='bars',ymax:pct?100:Math.max(...yi.map(tt))*1.04,ticks:pct?[0,25,50,75,100]:null,yf:pct?v=>v+'%':f0,mark:yr,tip:j=>{const k=yi[j];return `<b>${years[j]} · ${reg} (live)</b>`+act.map(s=>`${SNAME[s]}: ${pct?fp(m[s][k]/tt(k)*100):f0(m[s][k])+' TWh'}`).join('<br>')}});
  legend('llg2',act.map(s=>[SNAME[s],srcColor(s)]));$('lsub2').textContent=`${reg} · ${pct?'% of generation':'TWh'} from your Step 2 inputs and live Step 1 totals.`;
  /* source explorer with band */
  const src=S.msrc,base=pct?m[src].map((v,k)=>v/tt(k)*100):m[src];
  const dr=LAB.draws&&LAB.draws[reg]&&LAB.draws[reg][src];
  const sm=sMix(S.sc2,S.variant,reg),sbase=pct?sm[src].map((v,k)=>v/tot(sm,k)*100):sm[src];
  const toV=(arr)=>pct?arr.map((v,k)=>v/tt(k)*100):arr;
  const ser3=[{vals:yi.map(k=>base[k]),lo:dr?yi.map(k=>toV(dr.lo)[k]):null,hi:dr?yi.map(k=>toV(dr.hi)[k]):null,color:srcColor(src),w:2.6,bandOp:.25},{vals:yi.map(k=>sbase[k]),color:cv('ink'),w:1.5,dash:'5 3'}];
  chart($('lc3'),{years,series:ser3,ymax:Math.max(...ser3.flatMap(q=>q.hi||q.vals))*1.05,yf:pct?v=>v+'%':f0,mark:yr,tip:j=>{const k=yi[j];return `<b>${years[j]} · ${reg} · ${SNAME[src]}</b>Live: ${pct?fp(base[k]):f0(base[k])+' TWh'}`+(dr?`<br>${lv}: ${f0(dr.lo[k])}–${f0(dr.hi[k])} TWh`:'')+`<br>Saved: ${pct?fp(sbase[k]):f0(sbase[k])+' TWh'}`}});
  legend('llg3',[[SNAME[src]+' live'+(dr?' with '+lv+' band':''),srcColor(src)],['Saved ('+S.variant.split(' (')[0]+')',cv('ink')]]);
  $('lsub3').textContent=dr?`${SNAME[src]} in ${reg}; band from ${$('l2n').value} draws.`:`${SNAME[src]} in ${reg}. Press "Add Step 2 uncertainty" to draw the band.`;
  /* 2047 table: live vs saved shares by region */
  let h='<tr><th>2047 share</th>'+SRC.map(s=>`<th>${SNAME[s].replace('Natural ','')}</th>`).join('')+'<th>CO₂ t/MWh</th></tr>';
  REG.forEach(r=>{const a=LAB.mix[r],b=sMix(S.sc2,S.variant,r),ta=tt0(a,20),tb=tot(b,20);
    const e=(a.coal[20]*.95+a.gas[20]*.45)/ta;
    h+=`<tr class="${r===reg?'sel':''}"><td>${r} · live</td>`+SRC.map(s=>`<td>${fp(a[s][20]/ta*100)}</td>`).join('')+`<td>${e.toFixed(2)}</td></tr>`;
    h+=`<tr><td style="color:var(--mute)">${r} · saved</td>`+SRC.map(s=>{const d=a[s][20]/ta*100-b[s][20]/tb*100;return `<td class="${d>=0?'dpos':'dneg'}" style="font-weight:400">${fp(b[s][20]/tb*100)} <small>(${d>=0?'+':''}${d.toFixed(1)})</small></td>`}).join('')+`<td></td></tr>`});
  $('lt4').innerHTML=h;
  $('lsub4').textContent=`Share of generation in 2047. Small figures in brackets: live minus saved, in percentage points (${S.variant.split(' (')[0]}, ${S.sc2.split(' (')[0]} growth).`;
}
const tt0=(m,k)=>SRC.reduce((a,s)=>a+m[s][k],0);

/* ---- written reasoning ---- */
const WHY_R={
 India:'The national path comes first: nuclear, hydro and gas follow bounded rules; wind and solar grow as fast as a feasibility ramp and a grid-integration ceiling allow; coal balances whatever generation is still missing. Each source is then shared across regions by a seven-factor score (cost, resource, environment, security, infrastructure, policy direction, land), and a matrix-balancing step makes regional totals match Step 1 and source totals match the national path.',
 North:'North has the second-largest demand and the largest hydro resource on the mainland (about 47 GW exploitable, Himalayan rivers) plus 128 GW of 120 m wind potential (Rajasthan). Its coal resource is small (about 1 bn tonnes), irradiance is mid-range (4.9 kWh/m²/day) and land per person is moderate (0.27 ha). The score therefore pushes coal down and hydro, solar and wind up as policy direction tightens.',
 West:'West is the largest generating region and the most balanced one. It holds 132 bn tonnes of coal (Chhattisgarh, MP, Maharashtra), the best wind potential after the South (256 GW, Gujarat and Maharashtra), strong sun (5.25 kWh/m²/day), plenty of land per person (0.35 ha) and coastal nuclear sites. Coal stays large through 2047 in absolute terms, but solar and wind take most of the growth.',
 South:'South has the highest irradiance (5.28 kWh/m²/day) and the largest wind potential (268 GW, Tamil Nadu, Karnataka, Andhra Pradesh), coastal sites for nuclear, but little coal (27 bn tonnes) and modest hydro (12.6 GW). It becomes the most renewable region: solar and wind take most of the growth and coal falls fastest.',
 East:'East is the coal heartland (238 bn tonnes: Jharkhand, Odisha, West Bengal), so coal scores well on cost and domestic security and stays dominant. It has the lowest irradiance of the mainland (4.69 kWh/m²/day), the least land per person (0.16 ha), no wind-potential data, and 10 GW of hydro, which limits solar and wind and keeps its coal share high.',
 NorthEast:'NorthEast is small (about 40 TWh in 2035) but has the largest hydro potential in India (56 GW). Hydro is capped by the 60% load factor and 60% buildable share, and carries an ecology penalty. Irradiance is lowest (4.44) and hills are cloudy, so solar is capped at 30% of its generation. Nuclear is excluded (seismic zone V). Gas comes from Assam/Tripura, and its share is an artefact of small numbers.'};
const WHY_S={
 coal:'Coal is the balancing source: whatever total generation is not met by the other sources. No closures before 2030 (decline at most 1% a year), then at most 6% a year. Regionally it stays where the resource, domestic security and existing infrastructure are (East, then West), and it loses where the environment and policy scores are low. Emission factor 0.95 t/MWh (IPCC default fuel factor divided by plant efficiency).',
 gas:'Gas follows a simple path: −1% to +2% a year from FY2025-26. It is the most expensive source in our cost table (Rs 6–9/kWh, an assumption because no public figure was found), mostly imported as LNG except in the NorthEast, so it keeps a small peaking role. Emission factor 0.45 t/MWh.',
 nuclear:'Nuclear ramps to about 9% of generation in 2047 in the Main variant (organisers’ statement) or to 700 TWh for 100 GW in the draft National Electricity Policy 2026 variants. The curve exponent is uncertain (1.2–2.0). It is sited only where a site is possible (coastal or river water, seismic zone): zero in the NorthEast. The policy variants start from 22.38 GW (157 TWh) by 2032.',
 hydro:'Hydro starts from a five-year normal-year average, so one wet or dry year is not extrapolated, and grows 1.2–3.2% a year. It is capped at 98% of a buildable ceiling: CEA exploitable potential × 60% load factor × 60% usable (forests, resettlement, viability). North and NorthEast hold most of the potential; the environment score carries a 0.25 ecology penalty.',
 solar:'Solar is the cheapest new energy (Rs 2.48–2.70/kWh in 2025 auctions, plus a 0.7 firming adder). Its resource factor is irradiance, not capacity. It takes 55–75% of the wind-plus-solar energy, capped by a national land ceiling (3,343 GWp × 20% load factor × 40% usable) and by an integration ceiling that rises from 30% to 65% of generation (a storage and grid proxy). NorthEast is limited to 30%.',
 wind:'Wind takes the rest of the wind-plus-solar energy (25–45%). Regional ceilings come from 120 m potential × 30% load factor × 50% usable; only North, West and South have potential data, so East and NorthEast get almost none. Any energy wind cannot take goes to solar.'};
function whyRender(){
  const reg=S.region,i=ix(S.year),m=mixOf(S.sc2,S.variant,reg),s0=SRC.map(s=>m[s][0]/tot(m,0)*100),s1=SRC.map(s=>m[s][20]/tot(m,20)*100),sy=SRC.map(s=>m[s][i]/tot(m,i)*100);
  const best=SRC.map((s,k)=>({s,d:s1[k]-s0[k]})).sort((a,b)=>b.d-a.d);
  $('whyr').innerHTML=`<h3>${reg}</h3><p>${WHY_R[reg]}</p><p><b>Saved result (${S.variant.split(' (')[0]}, ${S.sc2.split(' (')[0]} growth):</b> ${SRC.map((s,k)=>`${SNAME[s]} ${s0[k].toFixed(0)}%→${s1[k].toFixed(0)}%`).join(', ')} (2027→2047). Biggest gain: ${SNAME[best[0].s]} (${best[0].d>=0?'+':''}${best[0].d.toFixed(1)} pts); biggest fall: ${SNAME[best[5].s]} (${best[5].d.toFixed(1)} pts).</p>`;
  const k=SRC.indexOf(S.msrc);
  $('whys').innerHTML=`<h3>${SNAME[S.msrc]}</h3><p>${WHY_S[S.msrc]}</p><p><b>In ${reg}:</b> ${s0[k].toFixed(1)}% in 2027, ${sy[k].toFixed(1)}% in ${S.year}, ${s1[k].toFixed(1)}% in 2047. Change the source with “Source (map, explorer)”.</p>`;
}

/* ---- population and urbanization helpers (dataset 2024 regional population, UN-anchored national path) ---- */
const R5N=['North','West','South','East','NorthEast'];
const urbNatF=()=>C.s1.urbNat;
function urbOf(r){return r==='India'?C.s1.urbNat:C.s1.urb[R5N.indexOf(r)]}
function pop24Of(r){return r==='India'?C.s1.pop24.reduce((a,b)=>a+b,0):C.s1.pop24[R5N.indexOf(r)]}
function popOf(r,i){ // million persons in year index i (0 = 2027)
  const c=C.s1,P47=$('l1pop')?+$('l1pop').value:1.64,g=Math.log(P47/c.pop25)/22,k=i+1,nat=c.pop25*1000*Math.exp(g*(k+1));
  const w=c.pop24.map((p,j)=>{let s=0;for(let q=1;q<=k;q++)s+=c.dpop[j]*(1-q/21);return p*Math.exp(s)}),sw=w.reduce((a,b)=>a+b,0);
  return r==='India'?nat:nat*w[R5N.indexOf(r)]/sw}
