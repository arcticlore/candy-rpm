#!/usr/bin/env python3
"""Генерирует docs/index.html — веб-дашборд из публичного API COPR.
Работает без авторизации: данные читаются из открытого эндпоинта."""
import json, urllib.request, datetime, os

OWNER, PROJECT = "arcticlore", "candy"
API = f"https://copr.fedorainfracloud.org/api_3/build/list?ownername={OWNER}&projectname={PROJECT}&limit=800"

def fetch():
    try:
        return json.load(urllib.request.urlopen(API, timeout=30)).get("items", [])
    except Exception as e:
        print("api error:", e, file=sys.stderr); return []

def state_color(s):
    return {"succeeded":"#4ade80","failed":"#f87171","running":"#60a5fa",
            "starting":"#fbbf24","pending":"#94a3b8","importing":"#94a3b8"}.get(s,"#64748b")

def esc(s): return s.replace("&","&amp;").replace("<","&lt;")

builds = fetch()
latest = {}
for b in sorted(builds, key=lambda x: x.get("id",0)):
    name = b.get("source_package",{}).get("name") or "?"
    st   = b.get("state","?")
    latest[name] = (st, b.get("id"), b.get("ended_on") or b.get("submitted_on"))

counts = {}
for n,(s,i,t) in latest.items(): counts[s] = counts.get(s,0)+1
total = len(latest)
ok = counts.get("succeeded",0)

rows=[]
for n in sorted(latest):
    s,bid,t = latest[n]
    tstr = datetime.datetime.fromtimestamp(t).strftime("%d.%m %H:%M") if isinstance(t,(int,float)) and t else ""
    rows.append(f"<tr><td>{esc(n)}</td><td><span class='dot' style='background:{state_color(s)}'></span>{s}"
                f"</td><td class='dim'>#{bid} · {tstr}</td></tr>")
rows_html="\n".join(rows)

bars="".join(f"<div class='chip'><span style='background:{state_color(s)}'></span>{s}: {c}</div>"
             for s,c in sorted(counts.items(), key=lambda kv:-kv[1]))

now=datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
html=f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="300">
<title>candy-rpm dashboard</title>
<style>
 body{{background:#0f172a;color:#e2e8f0;font-family:'JetBrains Mono',monospace;margin:24px}}
 h1{{background:linear-gradient(90deg,#ff6ec7,#a78bfa,#38bdf8);-webkit-background-clip:text;color:transparent}}
 .grid{{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}}
 .chip{{background:#1e293b;border-radius:8px;padding:6px 12px}} .chip span{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}}
 table{{border-collapse:collapse;width:100%}} td{{padding:5px 10px;border-bottom:1px solid #1e293b}}
 .dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px}}
 .dim{{color:#64748b}} a{{color:#38bdf8;text-decoration:none}}
</style></head><body>
<h1>🍬 candy-rpm</h1>
<p>Обновляется автоматически каждые 5 минут · сгенерировано {now} ·
<a href="https://github.com/arcticlore/candy-rpm">исходники</a></p>
<div class="grid">{bars}</div>
<h2>Пакеты ({total})</h2>
<table>{rows_html}</table>
<p class="dim">Подключение: dnf copr enable arcticlore/candy</p>
</body></html>"""

os.makedirs("docs", exist_ok=True)
open("docs/index.html","w").write(html)
print(f"docs/index.html: {total} пакетов")
