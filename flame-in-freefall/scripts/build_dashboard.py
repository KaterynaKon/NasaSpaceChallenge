#!/usr/bin/env python3
"""
Build a self-contained dashboard: dashboard/index.html with data inlined.
No server, no CDN, works offline and from a file:// URL.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "dashboard_data.json")
OUT_DIR = os.path.join(ROOT, "dashboard")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flame in Freefall — Fire Safety Explorer</title>
<style>
  :root{
    --navy:#425773; --navy2:#425773; --ink:#101720; --muted:#6C7D94;
    --line:#DCE2EA; --line2:#DCE2EB; --bg:#F6F7F9; --card:#FFFFFF; --subtle:#ECEFF3;
    --orange:#FF682D; --orange-dark:#D64717; --orange-soft:#FFF0E9;
    --teal:#425773; --grey:#6C7D94;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased}
  header{background:var(--navy);color:#fff;padding:22px 32px 18px}
  .head-row{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
  h1{font-size:21px;margin:0;letter-spacing:-.2px}
  .tag{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#9FB6C9}
  .sub{color:#B9CBDA;font-size:13px;margin-top:6px;max-width:900px;line-height:1.5}

  .envbar{background:#fff;border-bottom:1px solid var(--line);padding:12px 32px;
    display:flex;gap:8px;flex-wrap:wrap;align-items:center;position:sticky;top:0;z-index:20}
  .envbar .label{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-right:6px}
  .chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 14px;
    font-size:13px;cursor:pointer;color:var(--ink);transition:.15s}
  .chip:hover{border-color:#B9C9D8}
  .chip.on{background:var(--navy);color:#fff;border-color:var(--navy)}
  .chip small{opacity:.65;margin-left:6px;font-size:11px}

  main{display:grid;grid-template-columns:minmax(0,1fr) 430px;gap:22px;padding:22px 32px 60px;align-items:start}
  @media (max-width:1080px){main{grid-template-columns:1fr}}

  .note{background:#fff;border:1px solid var(--line);border-left:3px solid var(--orange);
    padding:10px 14px;font-size:12.5px;color:var(--muted);border-radius:6px;margin-bottom:14px;line-height:1.5}
  .note b{color:var(--ink)}

  .list{display:flex;flex-direction:column;gap:8px}
  .row{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px;
    cursor:pointer;transition:.15s;display:grid;grid-template-columns:34px 1fr auto;gap:12px;align-items:center}
  .row:hover{border-color:#B9C9D8;transform:translateY(-1px)}
  .row.on{border-color:var(--orange);box-shadow:0 0 0 1px var(--orange) inset}
  .rank{font-size:13px;color:var(--grey);font-variant-numeric:tabular-nums}
  .name{font-size:14.5px;font-weight:600;letter-spacing:-.1px}
  .meta{font-size:11.5px;color:var(--muted);margin-top:3px;display:flex;gap:8px;flex-wrap:wrap}
  .score{text-align:right;min-width:96px}
  .score b{font-size:19px;font-weight:650;font-variant-numeric:tabular-nums}
  .score small{display:block;font-size:10px;color:var(--grey);text-transform:uppercase;letter-spacing:.08em}
  .bar{height:3px;background:var(--subtle);border-radius:2px;margin-top:6px;overflow:hidden}
  .bar i{display:block;height:100%;background:var(--orange)}

  .badge{font-size:10px;padding:2px 7px;border-radius:999px;letter-spacing:.04em;text-transform:uppercase}
  .b-meas{background:#E6F4F1;color:var(--teal)}
  .b-est{background:#F1F3F6;color:var(--grey)}
  .b-exp{background:var(--orange-soft);color:#B24A20}

  aside{position:sticky;top:64px;background:#fff;border:1px solid var(--line);border-radius:12px;
    padding:20px;max-height:calc(100vh - 90px);overflow:auto}
  aside h2{font-size:17px;margin:0 0 4px;letter-spacing:-.2px}
  .aside-sub{font-size:12px;color:var(--muted);margin-bottom:14px}
  .kv{display:grid;grid-template-columns:120px 1fr;gap:6px 10px;font-size:12.5px;margin-bottom:14px}
  .kv div:nth-child(odd){color:var(--muted)}
  .kv div:nth-child(even){color:var(--ink)}
  .section-title{font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;color:var(--muted);
    margin:16px 0 8px;border-top:1px solid var(--line);padding-top:12px}
  .part{display:grid;grid-template-columns:1fr 52px;gap:8px;font-size:12.5px;padding:6px 0;border-bottom:1px dashed #EDF1F5}
  .part:last-child{border-bottom:0}
  .part .why{font-size:11px;color:var(--muted);margin-top:2px;line-height:1.4}
  .part .pts{text-align:right;font-variant-numeric:tabular-nums;color:var(--ink)}
  .part .pts span{color:var(--grey);font-size:11px}
  .finding{font-size:12.5px;line-height:1.55;color:#2A3B4C;margin-bottom:8px}
  .links a{display:inline-block;margin:4px 8px 0 0;font-size:12px;color:var(--teal);text-decoration:none;
    border-bottom:1px solid rgba(30,127,123,.25)}
  .empty{color:var(--muted);font-size:13px;padding:40px 0;text-align:center}
  .pill{display:inline-block;font-size:10.5px;color:var(--muted);background:var(--subtle);border-radius:4px;
    padding:2px 6px;margin:2px 4px 0 0}
  .filterbar{background:#fff;border-bottom:1px solid var(--line);padding:9px 32px;
    display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .filterbar .label{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-right:4px}
  .fchip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:5px 11px;
    font-size:12.5px;cursor:pointer;color:var(--ink);transition:.15s}
  .fchip:hover{border-color:#B9C9D8}
  .fchip.on{background:var(--navy2);color:#fff;border-color:var(--navy2)}
  .fchip small{opacity:.55;margin-left:5px;font-size:10.5px}
  .sep{width:1px;height:20px;background:var(--line);margin:0 6px}
  .spacer{flex:1}
  .clear{border:1px solid var(--line);background:#fff;border-radius:999px;padding:5px 11px;
    font-size:12px;color:var(--muted);cursor:pointer}
  .clear:hover{color:var(--ink);border-color:#B9C9D8}
  .emptyrow{background:#fff;border:1px dashed var(--line);border-radius:10px;padding:28px;
    text-align:center;color:var(--muted);font-size:13px}
  footer{padding:0 32px 40px;color:var(--grey);font-size:11.5px;line-height:1.6}
</style>
</head>
<body>
<header>
  <div class="head-row">
    <h1>Flame in Freefall</h1>
    <span class="tag">Fire safety explorer · NASA PSI</span>
  </div>
  <div class="sub">Which microgravity combustion experiment tells you the most about fire risk in a given
    environment? Pick an environment; every rank is a sum of five explicit components you can inspect.</div>
</header>

<div class="envbar" id="envbar"><span class="label">Environment</span></div>
<div class="filterbar" id="filterbar"></div>

<main>
  <section>
    <div class="note" id="note"></div>
    <div class="list" id="list"></div>
  </section>
  <aside id="detail"><div class="empty">Select an investigation to see its score breakdown and sources.</div></aside>
</main>

<footer id="foot"></footer>

<script>
const DATA = __DATA__;
const params = new URLSearchParams(location.search);
let currentEnv = params.get("env") || DATA.environments[0].id;
let currentId = params.get("id") || null;
let currentFuel = params.get("fuel") || "all";
let onlyMeasured = params.get("measured") === "1";
let sortBy = params.get("sort") || "score";

function syncUrl(){
  const p = new URLSearchParams();
  p.set("env", currentEnv);
  if(currentId) p.set("id", currentId);
  if(currentFuel !== "all") p.set("fuel", currentFuel);
  if(onlyMeasured) p.set("measured", "1");
  if(sortBy !== "score") p.set("sort", sortBy);
  history.replaceState(null, "", "?" + p.toString());
}

const el = id => document.getElementById(id);
const fmt = n => n === null || n === undefined ? "—" : (Math.round(n*10)/10).toString();
const range = (a,b,unit) => (a===null||a===undefined) && (b===null||b===undefined) ? "—"
  : (a===null||a===undefined) ? `≤ ${fmt(b)}${unit}` : (b===null||b===undefined) ? `≥ ${fmt(a)}${unit}`
  : (Math.abs(a-b) < 0.05) ? `${fmt(a)}${unit}` : `${fmt(a)}–${fmt(b)}${unit}`;

function renderStats(){
  const m = DATA.meta;
}

function renderEnvBar(){
  const bar = el("envbar");
  DATA.environments.forEach(env => {
    const b = document.createElement("button");
    b.className = "chip" + (env.id === currentEnv ? " on" : "");
    b.innerHTML = `${env.name}<small>${env.o2}% O₂ · ${env.pressure} psia</small>`;
    b.onclick = () => { currentEnv = env.id; renderEnvBar(); renderList(); renderDetail(); syncUrl(); };
    bar.appendChild(b);
  });
}

const FUEL_LABEL = {solid:"Solid", liquid:"Liquid", gaseous:"Gas", mixed:"Mixed", unknown:"Unknown"};

function fuelOf(r){
  const types = (r.physics && r.physics.fuel) || [];
  const known = types.filter(t => t && t !== "unknown");
  if(!known.length) return "unknown";
  return known.includes("mixed") && known.length === 1 ? "mixed" : known[0];
}

function hasMeasured(r){
  const e = r.experimental;
  if(!e) return false;
  return Boolean(e.o2 || e.pressure || e.flow);
}

function filtered(){
  return DATA.investigations.filter(r => {
    if(currentFuel !== "all" && fuelOf(r) !== currentFuel) return false;
    if(onlyMeasured && !hasMeasured(r)) return false;
    return true;
  });
}

function ranked(){
  const rows = filtered();
  rows.sort((a,b) => sortBy === "year"
    ? (parseInt(b.year)||0) - (parseInt(a.year)||0) || b.scores[currentEnv].score - a.scores[currentEnv].score
    : b.scores[currentEnv].score - a.scores[currentEnv].score);
  return rows;
}

function renderFilters(){
  const bar = el("filterbar");
  const total = DATA.investigations.length;
  const counts = {all: total, solid:0, liquid:0, gaseous:0, mixed:0, unknown:0};
  DATA.investigations.forEach(r => { counts[fuelOf(r)] = (counts[fuelOf(r)]||0) + 1; });
  const measuredCount = DATA.investigations.filter(hasMeasured).length;
  const order = ["all","solid","liquid","gaseous","unknown"];
  bar.innerHTML = `<span class="label">Fuel</span>`;
  order.forEach(key => {
    const b = document.createElement("button");
    b.className = "fchip" + (currentFuel === key ? " on" : "");
    const name = key === "all" ? "All" : FUEL_LABEL[key];
    b.innerHTML = `${name}<small>${counts[key]||0}</small>`;
    b.onclick = () => { currentFuel = key; renderFilters(); renderList(); syncUrl(); };
    bar.appendChild(b);
  });
  const sep = document.createElement("span"); sep.className = "sep"; bar.appendChild(sep);
  const clear = document.createElement("button");
  clear.className = "clear"; clear.textContent = "Clear filters";
  clear.onclick = () => { currentFuel = "all"; renderFilters(); renderList(); syncUrl(); };
  bar.appendChild(clear);
}

function renderNote(){
  const env = DATA.environments.find(e => e.id === currentEnv);
  const measured = DATA.investigations.filter(r => r.scores[currentEnv].parts[0].source === "measured").length;
  el("note").innerHTML = `<b>${env.name}:</b> ${env.note} Scores use measured test conditions for
    <b>${measured} of ${DATA.meta.investigations}</b> investigations; the rest are ranked from fuel type,
    flight platform and fire-safety framing only. As more Experimental tables are parsed, ranks shift.`;
}

function renderList(){
  renderNote();
  const list = el("list");
  list.innerHTML = "";
  const rows = ranked();
  if(!rows.length){
    list.innerHTML = `<div class="emptyrow">No investigation matches these filters.
      Try clearing the fuel chips.</div>`;
    return;
  }
  rows.forEach((r,i) => {
    const s = r.scores[currentEnv];
    const o2src = s.parts[0].source;
    const hasNumbers = r.experimental && (r.experimental.o2 || r.experimental.pressure || r.experimental.flow);
    const badge = hasNumbers ? `<span class="badge b-exp">table parsed</span>`
                  : r.experimental ? `<span class="badge b-est">samples only</span>`
                  : o2src === "measured" ? `<span class="badge b-meas">measured</span>`
                  : `<span class="badge b-est">estimated</span>`;
    const row = document.createElement("div");
    row.className = "row" + (r.id === currentId ? " on" : "");
    row.innerHTML = `
      <div class="rank">${i+1}</div>
      <div>
        <div class="name">${r.acronym ? r.acronym + " · " : ""}${r.title}</div>
        <div class="meta">
          <span>${r.id}</span>
          <span>${r.sub_area || "—"}</span>
          <span>${r.platform || "platform n/a"}</span>
          ${badge}
        </div>
      </div>
      <div class="score">
        <b>${s.score}</b><small>/ 100</small>
        <div class="bar"><i style="width:${s.score}%"></i></div>
      </div>`;
    row.onclick = () => { currentId = r.id; renderList(); renderDetail(); syncUrl(); };
    list.appendChild(row);
  });
}

function renderDetail(){
  const aside = el("detail");
  const r = DATA.investigations.find(x => x.id === currentId);
  if(!r){ aside.innerHTML = `<div class="empty">Select an investigation to see its score breakdown and sources.</div>`; return; }
  const s = r.scores[currentEnv];
  const env = DATA.environments.find(e => e.id === currentEnv);
  const p = r.physics || {};
  const exp = r.experimental;

  const parts = s.parts.map(part => `
    <div class="part">
      <div>${part.label}
        <div class="why">${part.why}</div>
      </div>
      <div class="pts">${part.points}<span>/${part.max}</span></div>
    </div>`).join("");

  const materials = (p.materials && p.materials.length) ? p.materials.join(", ") : "—";
  const keywords = (r.keywords || []).slice(0,6).map(k => `<span class="pill">${k}</span>`).join("");

  aside.innerHTML = `
    <h2>${r.acronym ? r.acronym + " — " : ""}${r.title}</h2>
    <div class="aside-sub">${r.id} · ${r.sub_area || "—"}</div>
    <div class="kv">
      <div>Platform</div><div>${r.platform || "—"}</div>
      <div>Hardware</div><div>${r.hardware || "—"}</div>
      <div>Fuel type</div><div>${(p.fuel||[]).join(", ") || "—"}</div>
      <div>Materials</div><div>${materials}</div>
      <div>O₂ measured</div><div>${range(p.o2 && p.o2[0], p.o2 && p.o2[1], "%")}</div>
      <div>Pressure</div><div>${range(p.pressure && p.pressure[0], p.pressure && p.pressure[1], " psia")}</div>
      <div>Airflow</div><div>${range(p.flow && p.flow[0], p.flow && p.flow[1], " cm/s")}</div>
      <div>Test rows</div><div>${exp && exp.rows ? exp.rows : "—"}</div>
      <div>Publications</div><div>${(r.publications && r.publications.total) || 0} (${(r.publications && r.publications.with_doi) || 0} with DOI)</div>
      <div>Data files</div><div>${r.files.count} · ${r.files.size_gb} GB</div>
    </div>
    ${keywords ? `<div>${keywords}</div>` : ""}
    ${r.findings ? `<div class="section-title">What they found</div>
      <div class="finding">${r.findings.summary}</div>
      <div class="links">${(r.findings.links||[]).slice(0,3).map((l,i)=>`<a href="${l}" target="_blank" rel="noopener">Source ${i+1}</a>`).join("")}</div>` : ""}
    <div class="section-title">Score for ${env.name} — ${s.score}/100</div>
    ${parts}
    <div class="section-title">Sources</div>
    <div class="links">
      <a href="${r.source_url}" target="_blank" rel="noopener">PSI record ${r.id}</a>
      ${r.doi ? `<a href="https://doi.org/${r.doi}" target="_blank" rel="noopener">Dataset DOI</a>` : ""}
    </div>`;
}

el("foot").innerHTML = `Data: NASA Physical Sciences Informatics (PSI), Combustion Science, ${DATA.meta.investigations} investigations.
Scores are a transparent weighted sum, not a NASA statement. Every number traces to a test row in the source table.`;

renderStats(); renderEnvBar(); renderFilters();
if(!currentId) currentId = ranked()[0].id;
renderList(); renderDetail();
</script>
</body>
</html>
"""


def main():
    with open(DATA, encoding="utf-8") as fh:
        payload = json.load(fh)

    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", blob)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {path} ({os.path.getsize(path)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
