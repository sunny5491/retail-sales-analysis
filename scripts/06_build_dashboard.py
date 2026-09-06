"""
Step 5: Build a self-contained interactive KPI dashboard (HTML + Plotly + vanilla JS).

Why HTML instead of Power BI/Tableau?  It opens anywhere (GitHub Pages, any
browser) and shows the same skills: KPI tiles, cross-filtering, drill-down.
The row-level data is embedded as JSON so filters recompute everything client-side.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data" / "cleaned" / "retail_sales_clean.csv")
OUT = ROOT / "dashboard" / "retail_dashboard.html"

cols = ["year_month", "year", "region", "state", "segment", "category", "sub_category",
        "product_name", "discount", "sales", "profit", "quantity", "ship_mode", "ship_days"]
data_json = json.dumps(df[cols].round(2).to_dict(orient="records"), separators=(",", ":"))

html = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retail Sales Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.3/plotly.min.js"></script>
<style>
  :root{--bg:#f6f6f4;--surface:#ffffff;--text:#0b0b0b;--muted:#52514e;--line:#e6e5e1;
        --blue:#2a78d6;--orange:#eb6834;--aqua:#1baf7a;--yellow:#eda100;--red:#e34948;--gray:#9a9892}
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  header{padding:20px 28px 8px} h1{margin:0;font-size:22px} header p{margin:4px 0 0;color:var(--muted)}
  .filters{display:flex;gap:12px;flex-wrap:wrap;padding:12px 28px;align-items:center}
  .filters label{font-size:12px;color:var(--muted);display:flex;flex-direction:column;gap:4px}
  select{padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--surface);font-size:13px;min-width:150px}
  button{padding:7px 12px;border:1px solid var(--line);border-radius:6px;background:var(--surface);cursor:pointer;margin-top:18px}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;padding:8px 28px}
  .kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
  .kpi .l{font-size:12px;color:var(--muted)} .kpi .v{font-size:24px;font-weight:600;margin-top:2px;font-variant-numeric:tabular-nums}
  .kpi .s{font-size:12px;color:var(--muted)} .neg{color:var(--red)}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:12px;padding:8px 28px 28px}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-width:0}
  .card h3{margin:0 0 4px;font-size:14px} .card .sub{font-size:12px;color:var(--muted);margin-bottom:6px}
  .card.wide{grid-column:1/-1}
  table{width:100%;border-collapse:collapse;font-size:13px} th,td{padding:6px 8px;text-align:right;border-bottom:1px solid var(--line)}
  th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left} th{color:var(--muted);font-weight:500}
  .plot{width:100%;height:300px}
</style></head><body>
<header><h1>Retail Sales Dashboard</h1><p>2024-2025 · 6,000 orders · filters recompute every tile and chart</p></header>

<div class="filters">
  <label>Year<select id="fYear"><option value="">All</option><option>2024</option><option>2025</option></select></label>
  <label>Region<select id="fRegion"><option value="">All</option></select></label>
  <label>Category<select id="fCategory"><option value="">All</option></select></label>
  <label>Segment<select id="fSegment"><option value="">All</option></select></label>
  <button id="reset">Reset filters</button>
</div>

<div class="kpis">
  <div class="kpi"><div class="l">Total sales</div><div class="v" id="kSales"></div><div class="s" id="kSalesSub"></div></div>
  <div class="kpi"><div class="l">Total profit</div><div class="v" id="kProfit"></div><div class="s" id="kProfitSub"></div></div>
  <div class="kpi"><div class="l">Profit margin</div><div class="v" id="kMargin"></div><div class="s">profit / sales</div></div>
  <div class="kpi"><div class="l">Orders</div><div class="v" id="kOrders"></div><div class="s" id="kOrdersSub"></div></div>
  <div class="kpi"><div class="l">Avg order value</div><div class="v" id="kAOV"></div><div class="s">sales / orders</div></div>
  <div class="kpi"><div class="l">Loss-making orders</div><div class="v" id="kLoss"></div><div class="s">orders with profit &lt; 0</div></div>
</div>

<div class="grid">
  <div class="card wide"><h3>Monthly sales and profit</h3><div class="sub">hover for exact values</div><div id="cTrend" class="plot"></div></div>
  <div class="card"><h3>Sales by sub-category</h3><div class="sub">colored by category · red = loss-making</div><div id="cSub" class="plot" style="height:340px"></div></div>
  <div class="card"><h3>Profit margin by discount level</h3><div class="sub">margins turn negative above 20%</div><div id="cDisc" class="plot" style="height:340px"></div></div>
  <div class="card"><h3>Sales by region</h3><div class="sub">label = profit margin</div><div id="cRegion" class="plot"></div></div>
  <div class="card"><h3>Sales by segment</h3><div id="cSeg" class="plot"></div></div>
  <div class="card wide"><h3>Top 10 products</h3><div class="sub">ranked by sales within current filters</div><table id="tTop"><thead><tr><th>#</th><th>Product</th><th>Category</th><th>Units</th><th>Sales</th><th>Profit</th><th>Margin</th></tr></thead><tbody></tbody></table></div>
</div>

<script>
const DATA = __DATA__;
const C = {blue:"#2a78d6",orange:"#eb6834",aqua:"#1baf7a",yellow:"#eda100",red:"#e34948",gray:"#9a9892"};
const CAT = {"Technology":C.blue,"Furniture":C.orange,"Office Supplies":C.aqua};
const $ = id => document.getElementById(id);
const fmtM = v => "$" + (Math.abs(v) >= 1e6 ? (v/1e6).toFixed(2)+"M" : Math.abs(v) >= 1e3 ? (v/1e3).toFixed(0)+"K" : v.toFixed(0));
const fmtN = v => v.toLocaleString();
const pct = v => (v*100).toFixed(1) + "%";
const sum = (arr, k) => arr.reduce((a, r) => a + r[k], 0);
const groupBy = (arr, k) => { const m = {}; for (const r of arr) (m[r[k]] ||= []).push(r); return m; };
const base = {margin:{l:56,r:16,t:8,b:40},paper_bgcolor:"#fff",plot_bgcolor:"#fff",font:{size:12,color:"#52514e"},
              xaxis:{gridcolor:"#e6e5e1",zeroline:false},yaxis:{gridcolor:"#e6e5e1",zeroline:false},hovermode:"closest",showlegend:false};
const cfg = {displayModeBar:false,responsive:true};

// populate filter options from data
for (const [id,key] of [["fRegion","region"],["fCategory","category"],["fSegment","segment"]]) {
  [...new Set(DATA.map(r => r[key]))].sort().forEach(v => { const o = document.createElement("option"); o.textContent = v; $(id).appendChild(o); });
  $(id).addEventListener("change", render);
}
$("fYear").addEventListener("change", render);
$("reset").addEventListener("click", () => { for (const id of ["fYear","fRegion","fCategory","fSegment"]) $(id).value = ""; render(); });

function filtered() {
  const y = $("fYear").value, r = $("fRegion").value, c = $("fCategory").value, s = $("fSegment").value;
  return DATA.filter(d => (!y || d.year == y) && (!r || d.region === r) && (!c || d.category === c) && (!s || d.segment === s));
}

function render() {
  const rows = filtered();
  const sales = sum(rows,"sales"), profit = sum(rows,"profit"), n = rows.length;
  // ---- KPI tiles ----
  $("kSales").textContent = fmtM(sales);
  $("kProfit").textContent = fmtM(profit); $("kProfit").className = "v" + (profit < 0 ? " neg" : "");
  $("kMargin").textContent = n ? pct(profit/sales) : "-";
  $("kOrders").textContent = fmtN(n);
  $("kAOV").textContent = n ? "$" + (sales/n).toFixed(0) : "-";
  $("kLoss").textContent = n ? pct(rows.filter(r => r.profit < 0).length / n) : "-";
  const y24 = rows.filter(r => r.year == 2024), y25 = rows.filter(r => r.year == 2025);
  const yoy = (k) => y24.length && y25.length ? `2025 vs 2024: ${(sum(y25,k)/sum(y24,k)-1 >= 0 ? "+" : "")}${pct(sum(y25,k)/sum(y24,k)-1)}` : "";
  $("kSalesSub").textContent = yoy("sales"); $("kProfitSub").textContent = yoy("profit");
  $("kOrdersSub").textContent = y24.length && y25.length ? `2025 vs 2024: ${(y25.length/y24.length-1>=0?"+":"")}${pct(y25.length/y24.length-1)}` : "";

  // ---- monthly trend (two charts sharing x, no dual axis) ----
  const bym = groupBy(rows,"year_month"); const months = Object.keys(bym).sort();
  Plotly.react("cTrend", [
    {x:months, y:months.map(m => sum(bym[m],"sales")), name:"Sales", type:"scatter", mode:"lines+markers", line:{color:C.blue,width:2}, marker:{size:6}, hovertemplate:"%{x}<br>Sales $%{y:,.0f}<extra></extra>"},
    {x:months, y:months.map(m => sum(bym[m],"profit")), name:"Profit", type:"scatter", mode:"lines+markers", line:{color:C.aqua,width:2}, marker:{size:6}, yaxis:"y2", xaxis:"x2", hovertemplate:"%{x}<br>Profit $%{y:,.0f}<extra></extra>"}],
    {...base, showlegend:true, legend:{orientation:"h",y:1.12,x:0}, grid:{rows:2,columns:1,pattern:"independent",roworder:"top to bottom"},
     xaxis:{gridcolor:"#e6e5e1",showticklabels:false}, xaxis2:{gridcolor:"#e6e5e1"}, yaxis:{gridcolor:"#e6e5e1",tickprefix:"$",tickformat:"~s",rangemode:"tozero"},
     yaxis2:{gridcolor:"#e6e5e1",tickprefix:"$",tickformat:"~s",rangemode:"tozero"}, margin:{l:56,r:16,t:30,b:40}}, cfg);

  // ---- sub-category bars ----
  const bys = groupBy(rows,"sub_category");
  const subs = Object.keys(bys).map(k => ({k, cat:bys[k][0].category, s:sum(bys[k],"sales"), p:sum(bys[k],"profit")})).sort((a,b)=>a.s-b.s);
  Plotly.react("cSub", [{type:"bar", orientation:"h", x:subs.map(d=>d.s), y:subs.map(d=>d.k), marker:{color:subs.map(d => d.p < 0 ? C.red : CAT[d.cat])},
    customdata:subs.map(d=>[d.p, d.cat]), hovertemplate:"%{y} (%{customdata[1]})<br>Sales $%{x:,.0f}<br>Profit $%{customdata[0]:,.0f}<extra></extra>"}],
    {...base, margin:{l:90,r:16,t:8,b:40}, xaxis:{gridcolor:"#e6e5e1",tickprefix:"$",tickformat:"~s"}, yaxis:{gridcolor:"rgba(0,0,0,0)"}, bargap:0.35}, cfg);

  // ---- discount vs margin ----
  const byd = groupBy(rows,"discount"); const ds = Object.keys(byd).map(Number).sort((a,b)=>a-b);
  const margins = ds.map(d => sum(byd[d],"profit")/sum(byd[d],"sales")*100);
  Plotly.react("cDisc", [{type:"bar", x:ds.map(d => (d*100).toFixed(0)+"%"), y:margins, marker:{color:margins.map(m => m<0?C.red:C.blue)},
    text:margins.map(m => m.toFixed(1)+"%"), textposition:"outside", cliponaxis:false, textfont:{color:"#52514e"}, customdata:ds.map(d=>byd[d].length),
    hovertemplate:"Discount %{x}<br>Margin %{y:.1f}%<br>%{customdata:,} orders<extra></extra>"}],
    {...base, xaxis:{type:"category",title:{text:"discount level"},gridcolor:"rgba(0,0,0,0)"}, yaxis:{gridcolor:"#e6e5e1",ticksuffix:"%",zeroline:true,zerolinecolor:"#52514e"}, bargap:0.4}, cfg);

  // ---- region ----
  const byr = groupBy(rows,"region"); const regs = Object.keys(byr).map(k=>({k,s:sum(byr[k],"sales"),p:sum(byr[k],"profit")})).sort((a,b)=>b.s-a.s);
  Plotly.react("cRegion", [{type:"bar", x:regs.map(d=>d.k), y:regs.map(d=>d.s), marker:{color:C.blue}, text:regs.map(d=>d.s?pct(d.p/d.s):""), textposition:"outside", cliponaxis:false, textfont:{color:"#52514e"},
    hovertemplate:"%{x}<br>Sales $%{y:,.0f}<extra></extra>"}], {...base, margin:{l:56,r:16,t:24,b:40}, yaxis:{gridcolor:"#e6e5e1",tickprefix:"$",tickformat:"~s"}, xaxis:{gridcolor:"rgba(0,0,0,0)"}, bargap:0.45}, cfg);

  // ---- segment ----
  const byg = groupBy(rows,"segment"); const segs = Object.keys(byg).map(k=>({k,s:sum(byg[k],"sales"),n:byg[k].length})).sort((a,b)=>b.s-a.s);
  Plotly.react("cSeg", [{type:"bar", x:segs.map(d=>d.k), y:segs.map(d=>d.s), marker:{color:C.blue}, customdata:segs.map(d=>d.n),
    hovertemplate:"%{x}<br>Sales $%{y:,.0f}<br>%{customdata:,} orders<extra></extra>"}], {...base, yaxis:{gridcolor:"#e6e5e1",tickprefix:"$",tickformat:"~s"}, xaxis:{gridcolor:"rgba(0,0,0,0)"}, bargap:0.5}, cfg);

  // ---- top products table ----
  const byp = groupBy(rows,"product_name");
  const top = Object.keys(byp).map(k=>({k,cat:byp[k][0].category,q:sum(byp[k],"quantity"),s:sum(byp[k],"sales"),p:sum(byp[k],"profit")})).sort((a,b)=>b.s-a.s).slice(0,10);
  $("tTop").querySelector("tbody").innerHTML = top.map((d,i)=>`<tr><td>${i+1}</td><td>${d.k}</td><td>${d.cat}</td><td>${fmtN(d.q)}</td><td>$${d.s.toLocaleString(undefined,{maximumFractionDigits:0})}</td><td class="${d.p<0?"neg":""}">$${d.p.toLocaleString(undefined,{maximumFractionDigits:0})}</td><td class="${d.p<0?"neg":""}">${pct(d.p/d.s)}</td></tr>`).join("");
}
render();
</script></body></html>"""

OUT.write_text(html.replace("__DATA__", data_json))
print(f"Dashboard -> {OUT}  ({OUT.stat().st_size/1024:,.0f} KB)")
