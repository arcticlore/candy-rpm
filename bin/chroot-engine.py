#!/usr/bin/env python3
"""chroot-engine v3 — замок на формулу: ЧРУТ + ФЕДОРА + ПАКЕТ.

Опрашивает живые результаты COPR по каждому чруту последнего билда пакета:

  каталог билда содержит .rpm            → SUCCEEDED (подтверждён)
  есть builder-live.log.gz, .rpm нет     → FAILED
  каталога нет                           → PENDING

Правила:
  • подтверждённый успех на текущей версии -> чрут закрыт, не трогается
  • FAILED                                 -> в план пересборки
  • PENDING дольше STUCK_HOURS             -> тоже в план (завис)

Выход: logs/chroot-plan.json  {"plan":{pkg:[chroots]}, "done":[pkg]}
"""
import json, os, sys, time, subprocess, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://download.copr.fedorainfracloud.org/results/arcticlore/candy"
LOCKF = os.path.join(ROOT, "state", "chroot-lock.json")
STUCK_HOURS = float(os.environ.get("STUCK_HOURS", "6"))
PROJECT = os.environ.get("CANDY_PROJ", "arcticlore/candy")

def jload(p, d):
    try: return json.load(open(p))
    except Exception: return d

lock = jload(LOCKF, {})
meta = jload(os.path.join(ROOT,"pkgs.json"), {})
state = jload(os.path.join(ROOT,"state/state.json"), {})
CHROOTS = meta.get("project",{}).get("chroots",[])

def save_lock():
    t = LOCKF+".tmp"; json.dump(lock, open(t,"w"), ensure_ascii=False, indent=1); os.replace(t, LOCKF)

def http_text(url):
    try:
        return urllib.request.urlopen(url, timeout=10).read().decode(errors="ignore")
    except Exception:
        return ""

def copr_failed_latest():
    """имя -> id последнего failed билда (для сигнатур), плюс все последние."""
    try:
        out = subprocess.run(["copr-cli","list-builds",PROJECT],
                             capture_output=True,text=True,timeout=30).stdout
    except subprocess.TimeoutExpired:
        return {},{}
    latest={}; failed={}
    for line in out.splitlines():
        p=line.split()
        if len(p)<3: continue
        bid,name,state=p[0],p[1],p[-1]
        if name not in latest: latest[name]=(int(bid),state)
        if state=="failed": failed[name]=int(bid)
    return latest,failed

latest, failed_map = copr_failed_latest()

plan = {}
done = []
now = time.time()

def check_chroot(args):
    """Проверяет один чрут для одного пакета. Возвращает (pkg, chroot, need_rebuild)."""
    n, c, bid, bstate, ver = args
    key = f"{n}|{c}"
    idx = f"{BASE}/{c}/{bid}-{n}/"
    listing = http_text(idx)
    if not listing:
        return (n, c, False)  # билдер не дошёл
    has_rpm = ".rpm" in listing.split("builder-live.log.gz")[0]
    if has_rpm:
        return (n, c, False)  # RPM есть → OK
    return (n, c, True)  # лог есть, rpm нет → failed

for x in meta["packages"]:
    n = x["name"]
    if x.get("enabled") is False: continue
    b = latest.get(n)
    if not b: continue
    bid, bstate = int(b[0]), b[1]

    # полностью зелёный последний билд -> замок по всем чрутам, не трогаем
    if bstate == "succeeded":
        ver = (state.get(n) or {}).get("ver","?")
        e = lock.setdefault(f"{n}|*", {"ver":ver,"ok":list(CHROOTS)})
        done.append(n)
        continue

    ver = (state.get(n) or {}).get("ver","?")
    
    # Параллельная проверка чрутов
    tasks = [(n, c, bid, bstate, ver) for c in CHROOTS]
    need = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(check_chroot, t): t for t in tasks}
        for future in as_completed(futures):
            pkg, chroot, needs_rebuild = future.result()
            if needs_rebuild:
                need.append(chroot)

    if need:
        plan[n] = need

# применяем правила к плану с учётом зависших pending
final={}
for n,chs in plan.items():
    keep=[]
    for c in chs:
        key=f"{n}|{c}"
        rec=lock.get(key) or {}
        if rec.get("fail_ver"):
            ts=rec.get("ts",0)
            if now-ts < STUCK_HOURS*3600:
                continue          # недавно падал и уже пересылался — ждём
        keep.append(c)
    if keep: final[n]=keep

json.dump({"plan":final,"done":done},
          open(os.path.join(ROOT,"logs/chroot-plan.json"),"w"),ensure_ascii=False,indent=1)
save_lock()
print(json.dumps(final,ensure_ascii=False))
