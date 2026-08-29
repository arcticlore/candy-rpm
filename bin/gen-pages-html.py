#!/usr/bin/env python3
"""gen-pages-html.py v3 — веб-панель с JS-фильтрами, поиском и сортировкой.
Данные: публичный API COPR (без авторизации). Автообновление каждые 5 минут."""
import html as h, json, sys, urllib.request, datetime, os

OWNER, PROJECT = "arcticlore", "candy"
API = f"https://copr.fedorainfracloud.org/api_3/build/list?ownername={OWNER}&projectname={PROJECT}&limit=1000"

def fetch():
    try: return json.load(urllib.request.urlopen(API, timeout=40)).get("items", [])
    except Exception as e: print("api error:", e, file=sys.stderr); return []

def sc(s):
    return {"succeeded":"#4ade80","failed":"#f87171","running":"#60a5fa",
            "starting":"#fbbf24","pending":"#94a3b8","importing":"#94a3b8",
            "waiting":"#94a3b8","canceled":"#475569"}.get(s,"#64748b")

def dot(s):
    return f"<span class='dot' style='background:{sc(s)}'></span>"

def bar(cur,tot,label,col="#4ade80"):
    tot=max(tot,1); pct=min(int(cur*100/tot),100); n=int(pct*34/100)
    b="▓"*n+"░"*(34-n)
    return (f"<div class='bar'><span class='bl'>{label}</span>"
            f"<span class='bf' style='color:{col}'>{b}</span> {pct}% ({cur}/{tot})</div>")

builds=sorted(fetch(), key=lambda b:b.get("id",0))
latest={}
for b in builds:
    n=(b.get("source_package") or {}).get("name") or "?"
    latest[n]={"state":b.get("state","?"),"id":b.get("id"),"ts":b.get("ended_on") or b.get("submitted_on") or 0}

counts={}
for n,d in latest.items(): counts[d["state"]]=counts.get(d["state"],0)+1
total=len(latest); ok=counts.get("succeeded",0)

states_chips="".join(
    f"<button class='chip' data-filter='{s}' onclick=\"filterState('{s}')\"><span class='dot' style='background:{sc(s)}'></span>{h.escape(s)}: {c}</button>"
    for s,c in sorted(counts.items(),key=lambda kv:-kv[1]))

pkg_rows=""
for n in sorted(latest):
    d=latest[n]
    tstr=datetime.datetime.fromtimestamp(d["ts"]).strftime("%d.%m %H:%M") if isinstance(d["ts"],(int,float)) and d["ts"] else "—"
    pkg_rows+=f"<tr data-state='{d['state']}'><td><b>{h.escape(n)}</b></td><td>{dot(d['state'])}{h.escape(d['state'])}</td><td class='dim'>#{d['id']} · {tstr}</td></tr>\n"

now=datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

html=f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="300">
<title>🍬 candy-rpm panel</title>
<style>
body{{background:#0b1220;color:#dbe4f0;font-family:'JetBrains Mono',Consolas,monospace;margin:24px}}
h1{{font-size:30px;margin:6px 0}} h2{{color:#7dd3fc;margin-top:28px}}
.wrap{{max-width:1100px;margin:auto}}
.banner{{background:linear-gradient(135deg,#ff6ec7,#a78bfa,#38bdf8);border-radius:12px;padding:2px;margin-bottom:18px}}
.inner{{background:#0b1220;border-radius:11px;padding:16px 22px}}
a{{color:#7dd3fc;text-decoration:none}} code{{color:#fbbf24}}
.grid{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 22px}}
.chip{{background:#16202e;border:1px solid #1e3a5f;border-radius:8px;padding:7px 13px;font-size:14px;
       color:#dbe4f0;cursor:pointer;transition:all .15s}}
.chip:hover{{border-color:#7dd3fc;background:#1a2d44}}
.chip.active{{border-color:#4ade80;background:#0d2818}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{padding:6px 12px;text-align:left;border-bottom:1px solid #16202e}}
th{{color:#7dd3fc;font-weight:normal;cursor:pointer;user-select:none}}
th:hover{{color:#fff}}
.bar{{display:flex;align-items:center;gap:10px;margin:8px 0;font-size:14px}}
.bl{{width:230px;color:#93a6bd}} .bf{{letter-spacing:2px}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}}
.dim{{color:#55637a}}
#search{{background:#16202e;border:1px solid #1e3a5f;border-radius:8px;padding:8px 14px;
         color:#dbe4f0;font-family:inherit;font-size:14px;width:300px;margin:10px 0}}
#search:focus{{outline:none;border-color:#7dd3fc}}
.badge{{background:#1e3a5f;border-radius:12px;padding:2px 10px;font-size:12px;margin-left:8px}}
</style></head><body><div class="wrap">
<div class="banner"><div class="inner"><h1>🍬 candy-rpm · панель конвейера</h1>
<span class="dim">автообновление 5 мин · {now} ·
<a href="https://github.com/arcticlore/candy-rpm">github</a></span></div></div>

<h2>📊 Прогресс</h2>
{bar(ok,total,"зелёные пакеты","#4ade80")}
{bar(total-ok,total,"фиксятся","#38bdf8")}

<h2>⚙️ Состояния</h2>
<div class="grid">{states_chips}</div>

<h2>🧩 Пакеты <span class="badge" id="count">{total}</span></h2>
<input type="text" id="search" placeholder="🔍 поиск пакета..." oninput="filterTable()">
<table><tr><th onclick="sortTable(0)">пакет ↕</th><th onclick="sortTable(1)">статус ↕</th><th onclick="sortTable(2)">билд ↕</th></tr>
<tbody id="tbody">{pkg_rows}</tbody></table>

<p class="dim"><code>sudo dnf copr enable arcticlore/candy</code></p>
</div>
<script>
let activeFilter=null;
function filterState(s){{
  activeFilter=activeFilter===s?null:s;
  document.querySelectorAll('.chip').forEach(c=>c.classList.toggle('active',c.dataset.filter===activeFilter));
  filterTable();
}}
function filterTable(){{
  const q=document.getElementById('search').value.toLowerCase();
  let vis=0;
  document.querySelectorAll('#tbody tr').forEach(tr=>{{
    const matchState=!activeFilter||tr.dataset.state===activeFilter;
    const matchSearch=!q||tr.cells[0].textContent.toLowerCase().includes(q);
    const show=matchState&&matchSearch;
    tr.style.display=show?'':'none';
    if(show)vis++;
  }});
  document.getElementById('count').textContent=vis;
}}
let sortDir=[1,1,1];
function sortTable(col){{
  const tb=document.getElementById('tbody');
  const rows=Array.from(tb.rows);
  sortDir[col]*=-1;
  rows.sort((a,b)=>{{
    const av=a.cells[col].textContent, bv=b.cells[col].textContent;
    return av.localeCompare(bv,'ru')*sortDir[col];
  }});
  rows.forEach(r=>tb.appendChild(r));
}}
</script>
</body></html>"""

os.makedirs("docs",exist_ok=True)
open("docs/index.html","w").write(html)
print(f"docs/index.html v3: {total} пакетов, {ok} succeeded")
