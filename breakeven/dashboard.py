"""Generate the business dashboard (single self-contained HTML file).

    python -m breakeven dashboard            # real data  -> dashboard/index.html
    python -m breakeven dashboard --demo     # synthetic  -> dashboard/demo.html (bannered DEMO)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import insights
from .analytics import DB, ROOT, connect, seed_demo


def build(demo: bool = False) -> Path:
    db = seed_demo() if demo else DB
    if not demo and not db.exists():
        raise SystemExit("No analytics yet. Run `python -m breakeven analytics pull` (or --demo to preview).")
    con = connect(db) if not demo else sqlite3.connect(db)
    source = dict(con.execute("SELECT key, value FROM meta").fetchall()).get("source", "?")
    payload = {
        "source": source,
        "kpis": {"28": insights.kpis(con, 28), "90": insights.kpis(con, 90), "365": insights.kpis(con, 365), "all": insights.kpis(con)},
        "videos": insights.video_table(con),
        "series": insights.timeseries(con),
    }
    payload["patterns"] = insights.patterns(payload["videos"])
    out = ROOT / "dashboard" / ("demo.html" if demo else "index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(TEMPLATE.replace("/*__DATA__*/null", json.dumps(payload)))
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Breakeven Dashboard</title>
<style>
@font-face{font-family:Inter;src:url(../brand/fonts/Inter-Regular.otf)}
@font-face{font-family:Inter;font-weight:600;src:url(../brand/fonts/Inter-SemiBold.otf)}
@font-face{font-family:InterDisplay;font-weight:700;src:url(../brand/fonts/InterDisplay-Bold.otf)}
@font-face{font-family:JBM;src:url(../brand/fonts/JetBrainsMono-Regular.ttf)}
:root{color-scheme:light;--bg:#f3eee4;--surface-1:#fcfcfb;--border:#e2ddd2;--text-primary:#0b0b0b;--text-secondary:#52514e;--muted:#7b7a74;
--grid:#ebe7de;--series-1:#2a78d6;--series-2:#eb6834;--series-3:#1baf7a;--series-4:#eda100;--accent:#ff5c39;--good:#0f7b3d;--warn:#a15c00;--bad:#c62828}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121417;--surface-1:#1a1a19;--border:#2a3038;--text-primary:#f0efec;
--text-secondary:#c3c2b7;--muted:#8c93a0;--grid:#262a30;--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--series-4:#c98500;--good:#3ccb7f;--warn:#e0a030;--bad:#ff6b6b}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121417;--surface-1:#1a1a19;--border:#2a3038;--text-primary:#f0efec;--text-secondary:#c3c2b7;--muted:#8c93a0;
--grid:#262a30;--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--series-4:#c98500;--good:#3ccb7f;--warn:#e0a030;--bad:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text-primary);font:15px/1.45 Inter,system-ui,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:24px 16px 64px}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-bottom:16px}
h1{font:700 26px InterDisplay,Inter,sans-serif;margin:0}h2{font:600 15px Inter;margin:0 0 12px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.06em}
.mono{font-family:JBM,ui-monospace,monospace}.sub{color:var(--text-secondary);font-size:13px}
.demo{background:var(--accent);color:#111;font-weight:600;padding:10px 14px;border-radius:10px;margin-bottom:16px}
.controls{display:flex;gap:8px;flex-wrap:wrap}.controls button{font:inherit;font-size:13px;padding:6px 12px;border-radius:999px;border:1px solid var(--border);background:var(--surface-1);color:var(--text-primary);cursor:pointer}
.controls button[aria-pressed=true]{background:var(--text-primary);color:var(--bg)}
.grid{display:grid;gap:12px}.kpis{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:14px;padding:16px;min-width:0}
.kpi .v{font:700 28px InterDisplay,Inter,sans-serif;font-variant-numeric:tabular-nums}.kpi .l{color:var(--text-secondary);font-size:13px}
.two{grid-template-columns:repeat(auto-fit,minmax(340px,1fr));margin-top:12px}
.meter{height:10px;border-radius:5px;background:var(--grid);overflow:hidden;margin:6px 0 2px}.meter>i{display:block;height:100%;background:var(--series-1);border-radius:5px}
svg{display:block;width:100%;height:auto;overflow:visible}svg text{fill:var(--muted);font:11px JBM,monospace}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;color:var(--text-secondary);margin-bottom:8px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.tip{position:fixed;pointer-events:none;background:var(--text-primary);color:var(--bg);padding:8px 10px;border-radius:8px;font-size:12px;line-height:1.5;display:none;z-index:9;max-width:260px}
table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left;white-space:normal;min-width:220px}th{color:var(--text-secondary);font-weight:600;cursor:pointer;user-select:none;position:sticky;top:0;background:var(--surface-1)}
.tablewrap{overflow-x:auto;max-height:560px}
.ins{list-style:none;padding:0;margin:0}.ins li{padding:10px 0;border-bottom:1px solid var(--border)}.ins b{font-weight:600}
.tag{font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;margin-right:8px;border:1px solid currentColor}
.pattern{color:var(--series-1)}.opportunity{color:var(--good)}.warning{color:var(--warn)}.info{color:var(--muted)}
.linkbtn{background:none;border:none;color:var(--text-secondary);text-decoration:underline;cursor:pointer;font:inherit;font-size:12px;padding:0}
</style></head><body><div class="wrap">
<div id="demo"></div>
<header><div><h1>Breakeven · Business dashboard</h1><div class="sub" id="asof"></div></div>
<div class="controls" role="group" aria-label="Date range"><button data-r="28">28 days</button><button data-r="90">90 days</button><button data-r="365">12 months</button><button data-r="all">All time</button>
<button id="theme" title="Toggle light/dark theme">Theme</button></div></header>
<section class="grid kpis" id="kpis"></section>
<section class="grid two">
 <div class="card"><h2>YouTube Partner Program progress</h2><div id="ypp"></div></div>
 <div class="card"><h2>What the data says</h2><ul class="ins" id="ins"></ul></div>
</section>
<section class="grid two">
 <div class="card"><h2>Daily views <button class="linkbtn" data-table="views">table</button></h2><div id="views"></div></div>
 <div class="card"><h2>Revenue by stream, monthly <button class="linkbtn" data-table="rev">table</button></h2><div class="legend" id="revlegend"></div><div id="rev"></div></div>
</section>
<section class="card" style="margin-top:12px"><h2>Videos · value created</h2><div class="sub" style="margin-bottom:8px">28-day metrics compare videos fairly regardless of age. Click a header to sort.</div><div class="tablewrap"><table id="vt"></table></div></section>
</div><div class="tip" id="tip"></div>
<script>
const D=/*__DATA__*/null;
const $=s=>document.querySelector(s), fmt=(n,d=0)=>n==null?'—':Number(n).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
const money=(n,d=0)=>n==null?'—':(n<0?'-$':'$')+fmt(Math.abs(n),d);
const nice=m=>{const r=m/4,p=Math.pow(10,Math.floor(Math.log10(r||1)));const s=[1,2,2.5,5,10].map(k=>k*p).find(k=>k>=r);return s*4};
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
let range=localStorageGet('range')||'28';
function localStorageGet(k){try{return localStorage.getItem('bk_'+k)}catch(e){return null}}
function localStorageSet(k,v){try{localStorage.setItem('bk_'+k,v)}catch(e){}}
if(D.source==='DEMO')$('#demo').innerHTML='<div class="demo">DEMO DATA: synthetic numbers for testing the dashboard only. Not real results. Run <span class="mono">python -m breakeven analytics pull</span> for real data.</div>';
const tip=$('#tip');function showTip(e,h){tip.innerHTML=h;tip.style.display='block';const x=Math.min(e.clientX+14,innerWidth-270);tip.style.left=x+'px';tip.style.top=(e.clientY+14)+'px'}function hideTip(){tip.style.display='none'}
function kpis(){const k=D.kpis[range]||{};$('#asof').textContent=k.as_of?('Data through '+k.as_of+' · source: '+D.source):'No data';
 const t=[['Views',fmt(k.views)],['Watch hours',fmt(k.watch_hours)],['Net subscribers',fmt(k.subs_net)],['Revenue',money(k.revenue)],['Costs',money(k.costs)],
 ['Profit',money(k.profit)],['RPM (all revenue)',money(k.rpm,2)],['CTR',k.ctr==null?'—':fmt(k.ctr,1)+'%'],['Avg % viewed',k.avd_pct==null?'—':fmt(k.avd_pct,1)+'%'],['Revenue / production hour',money(k.rev_per_prod_hour,2)]];
 $('#kpis').innerHTML=t.map(([l,v])=>`<div class="card kpi"><div class="l">${l}</div><div class="v">${v}</div></div>`).join('');
 const y=(D.kpis.all||{}).ypp||{hours_365:0,hours_target:8000,subs:0,subs_target:1000};
 const m=(l,a,b)=>`<div style="margin-bottom:14px"><div style="display:flex;justify-content:space-between"><span>${l}</span><span class="mono">${fmt(a)} / ${fmt(b)}</span></div><div class="meter" role="progressbar" aria-valuenow="${a}" aria-valuemax="${b}"><i style="width:${Math.min(100,100*a/b)}%"></i></div><div class="sub">${a>=b?'Reached ✓':fmt(100*a/b,0)+'% complete'}</div></div>`;
 $('#ypp').innerHTML=m('Subscribers',y.subs,y.subs_target)+m('Public watch hours (last 365 days)',y.hours_365,y.hours_target)+'<div class="sub">Target reflects the 8,000-hour bar that applies to applications from 1 Feb 2027.</div>';}
function insightsList(){$('#ins').innerHTML=D.patterns.map(p=>`<li><span class="tag ${p.kind}">${p.kind}</span>${p.text}${p.action?'<br><b>Next:</b> '+p.action:''}</li>`).join('')}
function filtered(){const d=D.series.daily;if(range==='all')return d;return d.slice(-Number(range))}
function lineChart(){const d=filtered(),W=560,H=240,L=48,R=10,T=10,B=28;if(!d.length){$('#views').innerHTML='<p class="sub">No data</p>';return}
 const max=nice(Math.max(...d.map(r=>r.views))*1.05)||1,x=i=>L+(W-L-R)*i/Math.max(1,d.length-1),y=v=>T+(H-T-B)*(1-v/max);
 let g='';for(let i=0;i<=4;i++){const v=max*i/4;g+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)"/><text x="${L-6}" y="${y(v)+4}" text-anchor="end">${fmt(v/1000,1)}k</text>`}
 const step=Math.ceil(d.length/6);for(let i=0;i<d.length;i+=step)g+=`<text x="${x(i)}" y="${H-8}" text-anchor="middle">${d[i].date.slice(5)}</text>`;
 const p=d.map((r,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(r.views).toFixed(1)).join('');
 $('#views').innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Daily views line chart">${g}<path d="${p}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round"/><line id="xh" y1="${T}" y2="${H-B}" stroke="var(--muted)" stroke-dasharray="3 3" visibility="hidden"/><circle id="xd" r="5" fill="var(--series-1)" stroke="var(--surface-1)" stroke-width="2" visibility="hidden"/><rect x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}" fill="transparent" id="hit"/></svg>`;
 const svg=$('#views svg'),hit=$('#hit');hit.onmousemove=e=>{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)*W/b.width,i=Math.max(0,Math.min(d.length-1,Math.round((px-L)/(W-L-R)*(d.length-1))));
  const xh=$('#xh'),xd=$('#xd');xh.setAttribute('x1',x(i));xh.setAttribute('x2',x(i));xh.setAttribute('visibility','visible');xd.setAttribute('cx',x(i));xd.setAttribute('cy',y(d[i].views));xd.setAttribute('visibility','visible');
  showTip(e,`<b>${d[i].date}</b><br>Views ${fmt(d[i].views)}<br>Watch hours ${fmt(d[i].hours,1)}<br>Net subs ${fmt(d[i].subs)}`)};hit.onmouseleave=()=>{hideTip();$('#xh').setAttribute('visibility','hidden');$('#xd').setAttribute('visibility','hidden')}}
const STREAMS=[['adsense','AdSense','--series-1'],['affiliate','Affiliate','--series-2'],['sponsor','Sponsors','--series-3'],['product','Products','--series-4']];
function revChart(){const m=D.series.monthly_revenue,W=560,H=240,L=52,R=10,T=10,B=28;$('#revlegend').innerHTML=STREAMS.map(s=>`<span><i style="background:var(${s[2]})"></i>${s[1]}</span>`).join('');
 if(!m.length){$('#rev').innerHTML='<p class="sub">No revenue yet</p>';return}
 const tot=r=>STREAMS.reduce((a,s)=>a+(r[s[0]]||0),0),max=nice(Math.max(...m.map(tot))*1.05)||1,bw=(W-L-R)/m.length,y=v=>T+(H-T-B)*(1-v/max);
 let g='';for(let i=0;i<=4;i++){const v=max*i/4;g+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)"/><text x="${L-6}" y="${y(v)+4}" text-anchor="end">${money(v)}</text>`}
 m.forEach((r,i)=>{let acc=0;const x0=L+i*bw+bw*.18,w=bw*.64;STREAMS.forEach(s=>{const v=r[s[0]]||0;if(v<=0)return;const y1=y(acc+v),y0=y(acc);const h=Math.max(0,y0-y1-2);
  g+=`<rect class="seg" x="${x0}" y="${y1}" width="${w}" height="${h}" rx="${acc===0?0:0}" fill="var(${s[2]})" data-t="<b>${r.month}</b><br>${s[1]}: ${money(v,2)}<br>Month total: ${money(tot(r),2)}"/>`;acc+=v});
  g+=`<text x="${x0+w/2}" y="${H-8}" text-anchor="middle">${r.month.slice(2)}</text>`});
 $('#rev').innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Monthly revenue by stream, stacked bars">${g}</svg>`;
 document.querySelectorAll('#rev .seg').forEach(el=>{el.onmousemove=e=>showTip(e,el.dataset.t);el.onmouseleave=hideTip})}
let sortKey='published',sortDir=-1;const COLS=[['title','Video'],['published','Published'],['series','Series'],['template','Thumb'],['views_28d','Views 28d'],['ctr_28d','CTR 28d %'],['avd_pct_28d','Viewed 28d %'],['subs_per_1k','Subs/1k views'],['watch_hours_total','Watch h'],['revenue_total','Revenue $'],['production_hours','Prod h'],['profit','Profit $'],['rev_per_prod_hour','$/prod h']];
function table(){const v=[...D.videos].sort((a,b)=>{const x=a[sortKey],y=b[sortKey];return (x>y?1:x<y?-1:0)*sortDir});
 $('#vt').innerHTML='<thead><tr>'+COLS.map(c=>`<th data-k="${c[0]}" aria-sort="${c[0]===sortKey?(sortDir>0?'ascending':'descending'):'none'}">${c[1]}${c[0]===sortKey?(sortDir>0?' ▲':' ▼'):''}</th>`).join('')+'</tr></thead><tbody>'+
 v.map(r=>'<tr>'+COLS.map(c=>{let x=r[c[0]];if(typeof x==='number')x=['revenue_total','profit','rev_per_prod_hour'].includes(c[0])?fmt(x,2):fmt(x,c[0].includes('pct')||c[0].includes('ctr')||c[0]==='subs_per_1k'||c[0]==='production_hours'?1:0);return `<td>${x??'—'}</td>`}).join('')+'</tr>').join('')+'</tbody>';
 document.querySelectorAll('#vt th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortDir=k===sortKey?-sortDir:-1;sortKey=k;table()})}
function tableView(which){const w=window.open('','_blank');if(!w)return;const rows=which==='views'?filtered().map(r=>[r.date,r.views,r.hours,r.subs]):D.series.monthly_revenue.map(r=>[r.month,...STREAMS.map(s=>r[s[0]])]);
 const head=which==='views'?['Date','Views','Watch hours','Net subs']:['Month',...STREAMS.map(s=>s[1])];w.document.write('<title>Table</title><table border=1 cellpadding=6 style="border-collapse:collapse;font:13px sans-serif"><tr>'+head.map(h=>'<th>'+h+'</th>').join('')+'</tr>'+rows.map(r=>'<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join('')+'</table>')}
document.querySelectorAll('[data-table]').forEach(b=>b.onclick=()=>tableView(b.dataset.table));
function render(){document.querySelectorAll('[data-r]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.r===range));kpis();lineChart();revChart()}
document.querySelectorAll('[data-r]').forEach(b=>b.onclick=()=>{range=b.dataset.r;localStorageSet('range',range);render()});
$('#theme').onclick=()=>{const cur=document.documentElement.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.dataset.theme=cur==='dark'?'light':'dark';render()};
render();insightsList();table();
</script></body></html>"""
