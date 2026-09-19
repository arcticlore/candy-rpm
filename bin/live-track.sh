#!/bin/bash
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p state logs
REFRESH="${REFRESH:-20}"
api() { curl -4 -sS --connect-timeout 10 -m 40 \
  -u "$(python3 -c "import configparser,os;c=configparser.ConfigParser();c.read(os.path.expanduser('~/.config/copr'));print(c.get('copr-cli','login',fallback=''))" 2>/dev/null):$(python3 -c "import configparser,os;c=configparser.ConfigParser();c.read(os.path.expanduser('~/.config/copr'));print(c.get('copr-cli','token',fallback=''))" 2>/dev/null)" "$1" 2>/dev/null; }
snapshot() {
    local U="https://copr.fedorainfracloud.org/api_3/build/list?ownername=arcticlore&projectname=candy&limit=300"
    local data; data=$(api "$U") || return 1
    local TF; TF=$(mktemp)
    printf '%s' "$data" > "$TF"
    python3 - "$TF" <<'PY'
import sys,json,time,os
try: d=json.load(open(sys.argv[1]))
except Exception: os.remove(sys.argv[1]); sys.exit(1)
items=d.get('items',[])
agg={}
for b in items:
    n=b.get('source_package',{}).get('name') or '?'
    s=b.get('state','?')
    agg.setdefault(n,{'state':s,'id':b.get('id')})
by_state={}
for b in items:
    s=b.get('state','?'); by_state[s]=by_state.get(s,0)+1
out={'ts':int(time.time()),'total':len(items),'by_state':by_state,
     'pkgs':{n:{'state':v['state'],'id':v['id']} for n,v in sorted(agg.items())}}
json.dump(out,open('state/live-state.json','w'),ensure_ascii=False)
cs=','.join(f"{k}:{v}" for k,v in sorted(by_state.items()))
print(f"[LIVE {time.strftime('%H:%M:%S')}] builds={len(items)} ({cs}) pkgs={len(agg)}")
os.remove(sys.argv[1])
PY
}
web() {
    local PORT="${1:-8787}"

    python3 - "$PORT" <<'PY'
import http.server,socketserver,json,sys,urllib.parse
PORT=int(sys.argv[1])
def load():
    try: return json.load(open('state/live-state.json'))
    except Exception: return {'total':0,'by_state':{},'pkgs':{}}
def cls(x):
    x=x or ''
    return 'ok' if x=='succeeded' else 'failed' if x=='failed' else 'running' if x in ('running','pending') else 'dead'
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p=urllib.parse.urlparse(self.path); d=load()
        if p.path=='/api':
            body=json.dumps(d,ensure_ascii=False).encode('utf-8'); ct='application/json; charset=utf-8'
        else:
            pk=d.get('pkgs',{})
            rows=''.join('<tr><td>'+n+'</td><td class='+cls((v or {}).get('state','?'))+'>'+((v or {}).get('state','?'))+'</td></tr>' for n,v in sorted(pk.items()))
            body=('<!doctype html><html><head><meta charset=utf-8>'
                  '<meta http-equiv=refresh content=5>'
                  '<title>candy live</title>'
                  '<style>body{font:13px/1.5 monospace;background:#12151b;color:#dfe6ee;padding:20px}'
                  'table{border-collapse:collapse;width:100%}td,th{border:1px solid #2a3140;padding:4px 8px;text-align:left}'
                  '.ok{color:#5fe28b}.failed{color:#ff6b6b}.running{color:#ffd166}.dead{color:#888}'
                  '.summary{background:#0d2b1a;border-left:4px solid #5fe28b;padding:8px 12px;margin-bottom:14px}</style>'
                  '</head><body>'
                  f'<div class=summary>builds: <b>{d.get("total",0)}</b> · '
                  ' '.join(f'{k}: {v}' for k,v in sorted(d.get("by_state",{}).items()))+
                  f' · обновлено {d.get("ts","-")}</div>'
                  '<table><tr><th>пакет</th><th>состояние</th></tr>'+rows+'</table>'
                  '<script>setTimeout(()=>location.reload(),5000)</script></body></html>').encode('utf-8')
            ct='text/html; charset=utf-8'
        self.send_response(200); self.send_header('Content-Type',ct)
        self.send_header('Content-Length',str(len(body))); self.end_headers()
        try: self.wfile.write(body)
        except Exception: pass
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
print(f'[WEB] http://127.0.0.1:{PORT}')
http.server.ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
PY
}
case "${1:-}" in
  once) snapshot ;;
  --web) web "${2:-8787}";;
  *)
    trap '' INT
    while :; do clear; echo "=== candy live (arcticlore/candy) — обновление раз в ${REFRESH}с ==="; echo; snapshot || echo "[LIVE] нет связи с COPR"; sleep "$REFRESH"; done
    ;;
esac
