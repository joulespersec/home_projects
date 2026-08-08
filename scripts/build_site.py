#!/usr/bin/env python3
"""Generate site/index.html: a self-contained interactive view of year-on-year
finishing-position movement (regression to the mean vs consistency) for six
professional sports leagues. Reads data/processed/viz_data.json and inlines it.
No external assets (CSP-safe): all CSS/JS embedded, system fonts only."""
import json, os

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = json.load(open(os.path.join(ROOT, "data", "processed", "viz_data.json")))
OUT = os.path.join(ROOT, "site", "index.html")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

HTML = r"""<style>
:root{
  color-scheme: light;
  --paper:#f7f7f4; --surface:#ffffff; --surface-2:#fbfbf9;
  --ink:#14171a; --ink-2:#55595e; --muted:#8a8f94;
  --grid:#e8e8e2; --axis:#cdcec8; --diag:#b7b8b1;
  --good:#0f9d3a; --good-band:rgba(15,157,58,.09);
  --crit:#d03b3b; --crit-band:rgba(208,59,59,.10);
  --border:rgba(20,23,26,.11); --shadow:rgba(20,23,26,.07);
  --s-nfl:#2a78d6; --s-nba:#eb6834; --s-mlb:#1baf7a;
  --s-epl:#4a3aa7; --s-afl:#eda100; --s-nrl:#e34948;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  color-scheme: dark;
  --paper:#0c0c0c; --surface:#191919; --surface-2:#161615;
  --ink:#f5f5f2; --ink-2:#c3c2b7; --muted:#8f8e88;
  --grid:#2b2b29; --axis:#3a3a37; --diag:#4a4a46;
  --good:#26b34e; --good-band:rgba(38,179,78,.15);
  --crit:#e66767; --crit-band:rgba(230,103,103,.15);
  --border:rgba(255,255,255,.12); --shadow:rgba(0,0,0,.4);
  --s-nfl:#3987e5; --s-nba:#d95926; --s-mlb:#199e70;
  --s-epl:#9085e9; --s-afl:#c98500; --s-nrl:#e66767;
}}
:root[data-theme="dark"]{
  color-scheme: dark;
  --paper:#0c0c0c; --surface:#191919; --surface-2:#161615;
  --ink:#f5f5f2; --ink-2:#c3c2b7; --muted:#8f8e88;
  --grid:#2b2b29; --axis:#3a3a37; --diag:#4a4a46;
  --good:#26b34e; --good-band:rgba(38,179,78,.15);
  --crit:#e66767; --crit-band:rgba(230,103,103,.15);
  --border:rgba(255,255,255,.12); --shadow:rgba(0,0,0,.4);
  --s-nfl:#3987e5; --s-nba:#d95926; --s-mlb:#199e70;
  --s-epl:#9085e9; --s-afl:#c98500; --s-nrl:#e66767;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  line-height:1.55;-webkit-font-smoothing:antialiased;}
.wrap{max-width:1180px;margin:0 auto;padding:clamp(20px,4vw,52px) clamp(16px,4vw,40px) 80px;}
.tnum{font-variant-numeric:tabular-nums}

/* ---- header ---- */
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);font-weight:600;margin:0 0 14px;}
h1{font-size:clamp(30px,5.2vw,52px);line-height:1.02;letter-spacing:-.022em;
  font-weight:800;margin:0 0 18px;text-wrap:balance;max-width:20ch;}
h1 em{font-style:normal;color:var(--ink-2);font-weight:800;}
.stand{font-size:clamp(16px,2vw,19px);color:var(--ink-2);max-width:64ch;margin:0 0 6px;}
.byline{font-size:13px;color:var(--muted);margin-top:16px;}
.byline b{color:var(--ink-2);font-weight:600}

/* ---- persistence strip ---- */
.thesis{margin:40px 0 8px;padding:24px clamp(16px,3vw,28px);background:var(--surface);
  border:1px solid var(--border);border-radius:14px;box-shadow:0 1px 3px var(--shadow);}
.thesis h2{font-size:15px;margin:0 0 4px;letter-spacing:-.01em}
.thesis .sub{font-size:13.5px;color:var(--ink-2);margin:0 0 20px;max-width:70ch}
.prow{display:grid;grid-template-columns:118px 1fr 132px;align-items:center;gap:14px;
  padding:9px 0;border-top:1px solid var(--grid);}
.prow:first-of-type{border-top:none}
.pname{font-weight:700;font-size:14px;display:flex;align-items:center;gap:9px}
.dot{width:11px;height:11px;border-radius:3px;flex:none}
.meter{position:relative;height:12px;background:var(--grid);border-radius:6px;overflow:hidden}
.meter>span{position:absolute;inset:0 auto 0 0;border-radius:6px}
.pval{font-size:13px;color:var(--ink-2);text-align:right}
.pval b{color:var(--ink);font-weight:700;font-size:15px}
.scalec{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);
  margin-top:12px;letter-spacing:.02em}

/* ---- controls ---- */
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:34px 0 22px}
.controls .spacer{flex:1}
.btn{font:inherit;font-size:13px;font-weight:600;color:var(--ink-2);cursor:pointer;
  background:var(--surface);border:1px solid var(--border);border-radius:9px;
  padding:8px 13px;display:inline-flex;align-items:center;gap:8px;}
.btn:hover{color:var(--ink);border-color:var(--axis)}
.btn[aria-pressed="true"]{color:var(--ink);border-color:currentColor;
  box-shadow:inset 0 0 0 1px var(--border)}
.btn .sw{width:26px;height:15px;border-radius:8px;background:var(--grid);position:relative;transition:.15s}
.btn .sw::after{content:"";position:absolute;top:2px;left:2px;width:11px;height:11px;border-radius:50%;
  background:var(--surface);box-shadow:0 1px 2px var(--shadow);transition:.15s}
.btn[aria-pressed="true"] .sw{background:var(--ink-2)}
.btn[aria-pressed="true"] .sw::after{left:13px}
.btn:focus-visible{outline:2px solid var(--s-nfl);outline-offset:2px}

/* ---- how to read ---- */
.legend{display:flex;flex-wrap:wrap;gap:16px 22px;font-size:12.5px;color:var(--ink-2);
  align-items:center;margin-bottom:8px}
.legend .li{display:flex;align-items:center;gap:8px}

/* ---- grid of panels ---- */
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:20px;margin-top:14px}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:14px;
  padding:16px 16px 10px;box-shadow:0 1px 3px var(--shadow);position:relative;min-width:0}
.phead{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:2px}
.ptitle{font-size:16px;font-weight:750;letter-spacing:-.01em;display:flex;align-items:center;gap:9px}
.pmeta{font-size:11.5px;color:var(--muted);text-align:right;line-height:1.4}
.psub{font-size:12px;color:var(--ink-2);margin:0 0 4px}
.psub b{color:var(--ink);font-weight:650}
svg.chart{width:100%;height:auto;display:block;overflow:visible}
svg.chart text{font-family:inherit}
.pts{opacity:0}
.show-pts .pts{opacity:.5}
.mtrend{opacity:0}
.show-trend .mtrend{opacity:1}

/* tooltip */
.tt{position:fixed;z-index:40;pointer-events:none;opacity:0;transition:opacity .1s;
  background:var(--ink);color:var(--paper);font-size:12px;line-height:1.5;
  padding:9px 11px;border-radius:9px;box-shadow:0 6px 20px var(--shadow);max-width:230px}
.tt b{font-weight:700}
.tt .row{display:flex;justify-content:space-between;gap:16px}
.tt .k{color:color-mix(in srgb,var(--paper) 60%,var(--ink))}
.tt hr{border:none;border-top:1px solid color-mix(in srgb,var(--paper) 25%,transparent);margin:6px 0}

/* ---- notes + table ---- */
.notes{margin-top:44px;display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:22px}
.note h3{font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin:0 0 8px}
.note p,.note li{font-size:13.5px;color:var(--ink-2);margin:0 0 8px}
.note ul{margin:0;padding-left:18px}
.note a{color:var(--s-nfl);text-decoration:none;border-bottom:1px solid var(--border)}
.note a:hover{border-color:currentColor}
.tablewrap{margin-top:30px;overflow-x:auto;display:none}
.tablewrap.show{display:block}
table{border-collapse:collapse;width:100%;font-size:12.5px;min-width:640px}
th,td{padding:6px 10px;text-align:right;border-bottom:1px solid var(--grid);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
thead th{color:var(--muted);font-weight:600;position:sticky;top:0;background:var(--surface);
  border-bottom:1px solid var(--axis)}
tbody tr:hover{background:var(--surface-2)}
.foot{margin-top:56px;padding-top:22px;border-top:1px solid var(--grid);font-size:12.5px;color:var(--muted)}
</style>

<div class="wrap">
  <header>
    <p class="eyebrow">Regression to the mean &middot; six leagues &middot; regular season only</p>
    <h1>Where do you finish <em>next</em> year?</h1>
    <p class="stand">Every professional league sells the same story: this season's table is a verdict.
      But finishing position is a noisy signal. This view tracks every club's regular-season finish and
      where the <b>same club</b> lands the following year &mdash; so you can see how strongly the ladder
      pulls everyone back toward the middle, and which leagues resist it.</p>
    <p class="byline">Post-season excluded. Each panel is a league's <b>modern, stable-size era</b>;
      positions are read within the frame teams actually compete in (conference, division, or a single table).</p>
  </header>

  <section class="thesis" id="thesis">
    <h2>Consistency vs. regression, ranked</h2>
    <p class="sub">Correlation (<i>r</i>) between a club's finishing position and its position the next
      year, on a shared 0&ndash;1 scale. High&nbsp;=&nbsp;the order persists (consistency). Low&nbsp;=&nbsp;
      last year barely predicts next year (strong regression to the mean).</p>
    <div id="prows"></div>
    <div class="scalec"><span>0.0 &mdash; pure regression to the mean</span><span>total consistency &mdash; 1.0</span></div>
  </section>

  <div class="controls">
    <button class="btn" id="tgPts" aria-pressed="false"><span class="sw"></span>Show every team-season</button>
    <button class="btn" id="tgTrend" aria-pressed="true"><span class="sw"></span>Median trend</button>
    <button class="btn" id="tgTable" aria-pressed="false">Data table</button>
    <span class="spacer"></span>
    <button class="btn" id="tgTheme">◐ Theme</button>
  </div>

  <div class="legend" aria-hidden="true">
    <span class="li"><svg width="30" height="20"><rect x="9" y="3" width="12" height="10" rx="2" fill="var(--s-nfl)" fill-opacity=".4" stroke="var(--s-nfl)" stroke-width="1.5"/><line x1="15" y1="0" x2="15" y2="3" stroke="var(--axis)" stroke-width="1.5"/><line x1="15" y1="13" x2="15" y2="19" stroke="var(--axis)" stroke-width="1.5"/></svg>middle 50% &amp; full range</span>
    <span class="li"><svg width="24" height="14"><line x1="3" y1="7" x2="21" y2="7" stroke="var(--ink)" stroke-width="2"/></svg>median</span>
    <span class="li"><svg width="18" height="14"><path d="M9 2 L15 7 L9 12 L3 7 Z" fill="var(--ink)"/></svg>mean</span>
    <span class="li"><svg width="30" height="14"><line x1="2" y1="12" x2="28" y2="2" stroke="var(--diag)" stroke-width="2" stroke-dasharray="3 3"/></svg>finished where it started</span>
    <span class="li"><svg width="16" height="14"><rect width="16" height="14" fill="var(--good-band)"/><line x1="0" y1="13" x2="16" y2="13" stroke="var(--good)" stroke-width="2" stroke-dasharray="3 2"/></svg>finals / playoffs zone</span>
    <span class="li"><svg width="16" height="14"><rect width="16" height="14" fill="var(--crit-band)"/></svg>relegation (EPL)</span>
  </div>

  <div class="grid" id="grid"></div>

  <div class="tablewrap" id="tablewrap"></div>

  <div class="notes">
    <div class="note">
      <h3>How to read a panel</h3>
      <p>Horizontal axis: where a club finished. Vertical axis: where it finished the <b>next</b> season,
        with <b>1st at the top</b>. Each column is a box plot of every club that started at that position.</p>
      <p>If finishing order carried over perfectly, every box would sit on the dashed diagonal. Instead the
        boxes bend toward mid-table: top finishers slide down, strugglers climb. That bend <b>is</b>
        regression to the mean.</p>
    </div>
    <div class="note">
      <h3>Method</h3>
      <ul>
        <li>Regular season only; play-offs and finals excluded.</li>
        <li>Position is ranked within the competitive frame: <b>conference</b> (NFL, NBA), <b>division</b>
          (MLB), or a <b>single table</b> (EPL, AFL, NRL).</li>
        <li>Each league is limited to a recent era with a stable team count so a given position means the
          same thing every year (shown per panel).</li>
        <li>A club must appear in both seasons to count. In the EPL the bottom three are relegated, so
          positions 18&ndash;20 have essentially no "next year" in the top flight &mdash; the shaded band.</li>
        <li>EPL / AFL / NRL tables are recomputed from match results (points, then goal-difference /
          percentage); administrative points deductions are not applied.</li>
      </ul>
    </div>
    <div class="note">
      <h3>Data sources</h3>
      <ul>
        <li>NFL &mdash; <a href="https://github.com/nflverse/nfldata">nflverse/nfldata</a></li>
        <li>NBA &mdash; <a href="https://github.com/fivethirtyeight/data/tree/master/nba-elo">FiveThirtyEight nba-elo</a></li>
        <li>MLB &mdash; <a href="https://github.com/chadwickbureau/baseballdatabank">Chadwick Baseball Databank</a></li>
        <li>EPL &mdash; <a href="https://github.com/footballcsv/england">footballcsv</a> + <a href="https://github.com/openfootball/england">openfootball</a></li>
        <li>AFL &mdash; <a href="https://github.com/HashenAbey/afl-data-update">afl-data-update</a></li>
        <li>NRL &mdash; <a href="https://github.com/uselessnrlstats/uselessnrlstats">uselessnrlstats</a></li>
      </ul>
    </div>
  </div>

  <p class="foot">Built from public regular-season records. Finals/playoff cut-off lines are the standard
    qualification count for each league's era; NFL playoffs expanded from 6 to 7 per conference in 2020, and
    MLB's second and third-place clubs frequently reach the post-season via wild cards.</p>
</div>

<div class="tt" id="tt" role="tooltip"></div>

<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const ORDER = ['NFL','NBA','MLB','EPL','AFL','NRL'];
const CLR = {NFL:'var(--s-nfl)',NBA:'var(--s-nba)',MLB:'var(--s-mlb)',
             EPL:'var(--s-epl)',AFL:'var(--s-afl)',NRL:'var(--s-nrl)'};
const SVGNS='http://www.w3.org/2000/svg';
const el=(n,a={})=>{const e=document.createElementNS(SVGNS,n);for(const k in a)e.setAttribute(k,a[k]);return e;};

/* ---------- persistence strip ---------- */
(function(){
  const host=document.getElementById('prows');
  const rows=ORDER.map(k=>({k,...DATA.leagues[k].persistence,name:DATA.leagues[k].name}))
                  .sort((a,b)=>b.r-a.r);
  for(const r of rows){
    const div=document.createElement('div');div.className='prow';
    div.innerHTML=`<div class="pname"><span class="dot" style="background:${CLR[r.k]}"></span>${r.k}</div>
      <div class="meter"><span style="width:${(r.r*100).toFixed(1)}%;background:${CLR[r.k]}"></span></div>
      <div class="pval tnum"><b>${r.r.toFixed(2)}</b> &nbsp;<span>r&sup2;=${r.r2.toFixed(2)}</span></div>`;
    host.appendChild(div);
  }
})();

/* ---------- panels ---------- */
const TT=document.getElementById('tt');
function showTT(html,x,y){TT.innerHTML=html;TT.style.opacity=1;
  const r=TT.getBoundingClientRect();let nx=x+14,ny=y+14;
  if(nx+r.width>innerWidth-8)nx=x-r.width-14;
  if(ny+r.height>innerHeight-8)ny=y-r.height-14;
  TT.style.left=nx+'px';TT.style.top=ny+'px';}
function hideTT(){TT.style.opacity=0;}

function panel(key){
  const d=DATA.leagues[key];
  const maxPos=Math.max(d.size,...d.positions.map(p=>p.pos));
  const N=maxPos;
  const W=520,H=380,ml=40,mr=16,mt=26,mb=38;
  const pw=W-ml-mr,ph=H-mt-mb;
  const X=p=>ml+(p-0.5)/N*pw;
  const Y=v=>mt+(v-0.5)/N*ph;
  const band=pw/N;
  const bw=Math.min(band*0.62,26);

  const svg=el('svg',{class:'chart',viewBox:`0 0 ${W} ${H}`,
    preserveAspectRatio:'xMidYMid meet',role:'img',
    'aria-label':`${d.name}: next-season finishing position by this-season finish`});

  // finals band (top) + relegation band (bottom)
  if(d.finals_cut){
    svg.appendChild(el('rect',{x:ml,y:Y(0.5),width:pw,height:Y(d.finals_cut+0.5)-Y(0.5),
      fill:'var(--good-band)'}));
    svg.appendChild(el('line',{x1:ml,x2:ml+pw,y1:Y(d.finals_cut+0.5),y2:Y(d.finals_cut+0.5),
      stroke:'var(--good)','stroke-width':1.5,'stroke-dasharray':'4 3','stroke-opacity':.8}));
    const fl=el('text',{x:ml+pw-2,y:Y(0.5)+11,'text-anchor':'end',
      'font-size':10.5,fill:'var(--good)','font-weight':600});
    fl.textContent=d.finals_label;svg.appendChild(fl);
  }
  if(d.relegation_cut){
    svg.appendChild(el('rect',{x:ml,y:Y(d.relegation_cut-0.5),width:pw,
      height:Y(N+0.5)-Y(d.relegation_cut-0.5),fill:'var(--crit-band)'}));
    const rl=el('text',{x:ml+pw-2,y:Y(N+0.5)-4,'text-anchor':'end',
      'font-size':10.5,fill:'var(--crit)','font-weight':600});
    rl.textContent=d.relegation_label;svg.appendChild(rl);
  }

  // gridlines + y ticks
  const yticks=[1];for(let v=5;v<=N;v+=5)yticks.push(v);
  if(N-yticks[yticks.length-1]>=2)yticks.push(N);  // avoid crowding the last ×5 tick
  for(const v of yticks){
    svg.appendChild(el('line',{x1:ml,x2:ml+pw,y1:Y(v),y2:Y(v),stroke:'var(--grid)','stroke-width':1}));
    const t=el('text',{x:ml-7,y:Y(v)+3.5,'text-anchor':'end','font-size':10,fill:'var(--muted)',
      'font-variant-numeric':'tabular-nums'});t.textContent=v;svg.appendChild(t);
  }
  // x axis baseline + ticks
  svg.appendChild(el('line',{x1:ml,x2:ml+pw,y1:mt+ph,y2:mt+ph,stroke:'var(--axis)','stroke-width':1}));
  const step=N>16?2:1;
  for(let p=1;p<=N;p++){
    if(p%step!==0 && p!==1 && p!==N)continue;
    const t=el('text',{x:X(p),y:mt+ph+14,'text-anchor':'middle','font-size':10,fill:'var(--muted)',
      'font-variant-numeric':'tabular-nums'});t.textContent=p;svg.appendChild(t);
  }

  // diagonal "finished where it started"
  svg.appendChild(el('line',{x1:X(1),y1:Y(1),x2:X(N),y2:Y(N),stroke:'var(--diag)','stroke-width':2,
    'stroke-dasharray':'4 4'}));

  // raw points (behind boxes), median trend
  const ptsG=el('g',{class:'pts'});
  const trendPts=[];
  const boxesG=el('g',{});
  for(const p of d.positions){
    const cx=X(p.pos);
    // jittered points
    let seed=p.pos*97.13;
    for(const v of p.values){
      seed=(seed*9301+49297)%233280;const j=(seed/233280-0.5)*band*0.5;
      ptsG.appendChild(el('circle',{cx:cx+j,cy:Y(v),r:1.7,fill:CLR[key]}));
    }
    // whisker
    boxesG.appendChild(el('line',{x1:cx,x2:cx,y1:Y(p.min),y2:Y(p.max),
      stroke:CLR[key],'stroke-width':1.4,'stroke-opacity':.85}));
    boxesG.appendChild(el('line',{x1:cx-4,x2:cx+4,y1:Y(p.min),y2:Y(p.min),stroke:CLR[key],'stroke-width':1.4}));
    boxesG.appendChild(el('line',{x1:cx-4,x2:cx+4,y1:Y(p.max),y2:Y(p.max),stroke:CLR[key],'stroke-width':1.4}));
    // box q1..q3
    boxesG.appendChild(el('rect',{x:cx-bw/2,y:Y(p.q1),width:bw,height:Math.max(Y(p.q3)-Y(p.q1),1.5),
      rx:2.5,fill:CLR[key],'fill-opacity':.42,stroke:CLR[key],'stroke-width':1.5}));
    // median
    boxesG.appendChild(el('line',{x1:cx-bw/2,x2:cx+bw/2,y1:Y(p.median),y2:Y(p.median),
      stroke:'var(--ink)','stroke-width':2}));
    // mean diamond
    const m=Y(p.mean);
    boxesG.appendChild(el('path',{d:`M${cx} ${m-4} L${cx+4} ${m} L${cx} ${m+4} L${cx-4} ${m} Z`,
      fill:'var(--ink)',stroke:'var(--surface)','stroke-width':1}));
    trendPts.push([cx,Y(p.median)]);
    // hover hit area
    const hit=el('rect',{x:cx-band/2,y:mt,width:band,height:ph,fill:'transparent'});
    const mv=(p.mean_move>0?'+':'')+p.mean_move;
    hit.addEventListener('mousemove',e=>showTT(
      `<b>${key} &middot; finished ${p.pos}${suf(p.pos)}</b><hr>`+
      `<div class="row"><span class="k">Next year median</span><b>${p.median}${suf(Math.round(p.median))}</b></div>`+
      `<div class="row"><span class="k">Middle 50%</span><b>${p.q1}&ndash;${p.q3}</b></div>`+
      `<div class="row"><span class="k">Full range</span><b>${p.min}&ndash;${p.max}</b></div>`+
      `<div class="row"><span class="k">Mean move</span><b>${mv} places</b></div>`+
      `<div class="row"><span class="k">Seasons</span><b>${p.n}</b></div>`,e.clientX,e.clientY));
    hit.addEventListener('mouseleave',hideTT);
    boxesG.appendChild(hit);
  }
  // trend polyline through medians
  const tr=el('polyline',{class:'mtrend',fill:'none',stroke:CLR[key],'stroke-width':2,
    'stroke-opacity':.55,'stroke-dasharray':'1 5','stroke-linecap':'round',
    points:trendPts.map(p=>p.join(',')).join(' ')});

  svg.appendChild(ptsG);svg.appendChild(tr);svg.appendChild(boxesG);

  // axis titles
  const ax=el('text',{x:ml+pw/2,y:H-2,'text-anchor':'middle','font-size':10.5,fill:'var(--ink-2)'});
  ax.textContent='Finishing position  ▶';svg.appendChild(ax);

  // wrapper
  const wrap=document.createElement('div');wrap.className='panel';
  const fr={conference:'per conference',division:'per division',league:'single table'}[d.grouped_by];
  wrap.innerHTML=`<div class="phead">
      <div class="ptitle"><span class="dot" style="background:${CLR[key]}"></span>${d.name}</div>
      <div class="pmeta tnum">${d.window[0]}&ndash;${d.window[1]} &middot; ${d.n_transitions} moves<br>${d.size} teams ${fr}</div>
    </div>
    <p class="psub">r = <b>${d.persistence.r.toFixed(2)}</b> &middot; ${verdict(d.persistence.r)}</p>`;
  wrap.appendChild(svg);
  // y-axis caption
  const cap=document.createElement('div');
  cap.style.cssText='font-size:10.5px;color:var(--muted);margin:-2px 0 4px 2px';
  cap.innerHTML='▲ next-season finish (1st at top)';
  wrap.insertBefore(cap,svg);
  return wrap;
}
function suf(n){n=Math.round(n);const s=['th','st','nd','rd'],v=n%100;return (s[(v-20)%10]||s[v]||s[0]);}
function verdict(r){return r>=0.6?'order tends to persist':r>=0.45?'moderate carry-over':
  r>=0.38?'strong pull to the middle':'very strong regression to the mean';}

const grid=document.getElementById('grid');
ORDER.forEach(k=>grid.appendChild(panel(k)));

/* ---------- data table ---------- */
(function(){
  const w=document.getElementById('tablewrap');
  let h='<table><thead><tr><th>League</th><th>Finish</th><th>Seasons</th><th>Next: min</th>'+
    '<th>Q1</th><th>Median</th><th>Q3</th><th>max</th><th>Mean</th><th>Mean move</th></tr></thead><tbody>';
  for(const k of ORDER){for(const p of DATA.leagues[k].positions){
    const mv=(p.mean_move>0?'+':'')+p.mean_move;
    h+=`<tr><td>${k}</td><td class="tnum">${p.pos}</td><td class="tnum">${p.n}</td>`+
       `<td class="tnum">${p.min}</td><td class="tnum">${p.q1}</td><td class="tnum">${p.median}</td>`+
       `<td class="tnum">${p.q3}</td><td class="tnum">${p.max}</td><td class="tnum">${p.mean}</td>`+
       `<td class="tnum">${mv}</td></tr>`;
  }}
  w.innerHTML=h+'</tbody></table>';
})();

/* ---------- controls ---------- */
const root=document.documentElement, grEl=document.getElementById('grid');
function toggle(btn,cls,host){const on=btn.getAttribute('aria-pressed')!=='true';
  btn.setAttribute('aria-pressed',on);host.classList.toggle(cls,on);}
document.getElementById('tgPts').onclick=e=>toggle(e.currentTarget,'show-pts',grEl);
const trendBtn=document.getElementById('tgTrend');grEl.classList.add('show-trend');
trendBtn.onclick=e=>toggle(e.currentTarget,'show-trend',grEl);
document.getElementById('tgTable').onclick=e=>{const on=e.currentTarget.getAttribute('aria-pressed')!=='true';
  e.currentTarget.setAttribute('aria-pressed',on);document.getElementById('tablewrap').classList.toggle('show',on);};
document.getElementById('tgTheme').onclick=()=>{
  const cur=root.getAttribute('data-theme');
  const sysDark=matchMedia('(prefers-color-scheme:dark)').matches;
  const now=cur?cur:(sysDark?'dark':'light');
  root.setAttribute('data-theme',now==='dark'?'light':'dark');};
</script>
"""

with open(OUT, "w") as f:
    f.write(HTML.replace("__DATA__", json.dumps(DATA, separators=(",", ":"))))
print("wrote", OUT, os.path.getsize(OUT), "bytes")
