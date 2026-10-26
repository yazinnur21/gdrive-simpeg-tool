import os, json, re, shutil, urllib.parse, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import fitz

B = os.path.dirname(os.path.abspath(__file__))
WA, UP, TH = f"{B}/wa-pdf", f"{B}/wa-pdf-upload", f"{B}/thumb"
DONE, MANUAL = f"{B}/done.txt", f"{B}/manual.txt"
KAT = ("KS", "PM", "LN", "MM")
lock = threading.Lock()
os.makedirs(UP, exist_ok=True); os.makedirs(TH, exist_ok=True)

def L(n):
    p = f"{B}/{n}.json"
    return json.load(open(p)) if os.path.exists(p) else {}
def S(n, d):
    json.dump(d, open(f"{B}/{n}.json", "w"), indent=1, ensure_ascii=False)
def lines(f):
    return set(l for l in open(f).read().splitlines() if l) if os.path.exists(f) else set()
def potong(s, n=110):
    s = re.sub(r'[\\/:*?"<>|]', "-", s).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0]

def data():
    K, T, J, P = L("kategori"), L("tahun"), L("judul"), L("penyelenggara")
    done, man = lines(DONE), lines(MANUAL)
    out = []
    for n in sorted(os.listdir(WA)):
        if not n.lower().endswith(".pdf"): continue
        st = "TERKIRIM" if n in done else ("MANUAL" if n in man else "BELUM")
        out.append({"n": n, "baru": n not in K, "st": st, "k": K.get(n, ""), "t": T.get(n) or "",
                    "j": J.get(n, ""), "p": P.get(n) or "", "kb": round(os.path.getsize(f"{WA}/{n}") / 1024), "mt": os.path.getmtime(f"{WA}/{n}"), "new": time.time() - os.path.getmtime(f"{WA}/{n}") < 259200})
    rank = {"BELUM": 1, "MANUAL": 2, "TERKIRIM": 3}
    out.sort(key=lambda x: (not x["baru"], not x["new"], -x["mt"] if x["new"] else 0, rank[x["st"]], x["n"]))
    return out

def simpan(d):
    n = os.path.basename(d["name"])
    if not os.path.exists(f"{WA}/{n}"): raise ValueError("file tidak ada")
    if d["kategori"] not in KAT: raise ValueError("kategori salah")
    t = int(d["tahun"]); j = d["judul"].strip(); p = d["penyelenggara"].strip()
    if not (1980 <= t <= 2030) or not j or not p: raise ValueError("tahun/judul/penyelenggara tidak valid")
    with lock:
        K, T, J, P, NB = L("kategori"), L("tahun"), L("judul"), L("penyelenggara"), L("namabaru")
        K[n], T[n], J[n], P[n] = d["kategori"], t, j, p
        used = {v for k, v in NB.items() if k != n}
        base = potong(j); nm = base + ".pdf"
        if nm in used: nm = f"{base} ({t}).pdf"
        i = 2
        while nm in used:
            nm = f"{base} ({t}) {i}.pdf"; i += 1
        if n in NB and NB[n] != nm and os.path.exists(f"{UP}/{NB[n]}"): os.remove(f"{UP}/{NB[n]}")
        shutil.copy2(f"{WA}/{n}", f"{UP}/{nm}")
        NB[n] = nm
        for a, b in (("kategori", K), ("tahun", T), ("judul", J), ("penyelenggara", P), ("namabaru", NB)): S(a, b)

def thumb(n):
    t = f"{TH}/{n}.png"
    if not os.path.exists(t):
        fitz.open(f"{WA}/{n}")[0].get_pixmap(dpi=60).save(t)
    return open(t, "rb").read()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ct):
        if isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        p = urllib.parse.unquote(self.path.split("?")[0])
        try:
            if p == "/": self.send(200, HTML, "text/html; charset=utf-8")
            elif p == "/final": self.send(200, open(f"{B}/final.html", "rb").read(), "text/html; charset=utf-8")
            elif p == "/api/data": self.send(200, json.dumps(data()), "application/json")
            elif p.startswith("/thumb/"): self.send(200, thumb(os.path.basename(p[7:])), "image/png")
            elif p.startswith("/pdf/"): self.send(200, open(f"{WA}/{os.path.basename(p[5:])}", "rb").read(), "application/pdf")
            else: self.send(404, "x", "text/plain")
        except Exception as e:
            self.send(500, str(e), "text/plain")
    def do_POST(self):
        try:
            d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            simpan(d); self.send(200, "ok", "text/plain")
        except Exception as e:
            self.send(400, str(e), "text/plain")

HTML = """<!doctype html><meta charset=utf-8><title>Sertifikat</title><style>
body{font-family:sans-serif;margin:0;background:#f4f4f4}
#bar{position:sticky;top:0;background:#0a7;color:#fff;padding:8px;z-index:9}
#bar button,#bar input{padding:6px;margin:2px}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px;padding:12px}
.c{background:#fff;padding:10px;border-radius:6px}.c img{width:100%;border:1px solid #ccc}
.b{display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;font-size:12px}
.TERKIRIM{background:#27a}.BELUM{background:#e80}.MANUAL{background:#c33}.BARU{background:#a0a}.NEW{background:#d00;margin-left:4px}
.c input,.c select{width:100%;box-sizing:border-box;margin:2px 0;padding:4px}
.f{font-size:11px;color:#888;word-break:break-all}
</style>
<div id=bar><input id=q placeholder="filter teks..." oninput=render()>
<span id=btn></span> <b id=stat></b> <small id=ts></small></div>
<div class=g id=g></div>
<script>
let DATA=[],last='',st='',cat='';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function setf(a,b){st=a;cat=b;render()}
async function load(){
  const t=await (await fetch('/api/data')).text();
  if(t===last)return;
  if(document.activeElement&&/INPUT|SELECT/.test(document.activeElement.tagName)&&document.activeElement.id!=='q')return;
  last=t;DATA=JSON.parse(t);render();
  document.getElementById('ts').innerText='update '+new Date().toLocaleTimeString();
}
function render(){
  const q=document.getElementById('q').value.toLowerCase();
  const c=x=>DATA.filter(d=>x(d)).length;
  document.getElementById('stat').innerText=`Total ${DATA.length} | Terkirim ${c(d=>d.st=='TERKIRIM')} | Belum ${c(d=>d.st=='BELUM'&&!d.baru)} | Manual ${c(d=>d.st=='MANUAL')} | Baru ${c(d=>d.baru)} | Terbaru ${c(d=>d.new)}`;
  const B=[['SEMUA','',''],['TERBARU','TERBARU',''],['BARU','BARU',''],['BELUM','BELUM',''],['TERKIRIM','TERKIRIM',''],['MANUAL','MANUAL',''],['KS','','KS'],['PM','','PM'],['LN','','LN'],['MM','','MM']];
  document.getElementById('btn').innerHTML=B.map(b=>`<button onclick="setf('${b[1]}','${b[2]}')">${b[0]}</button>`).join('');
  const rows=DATA.map((d,i)=>[d,i]).filter(([d])=>(!st||(st=='BARU'?d.baru:st=='TERBARU'?d.new:d.st==st))&&(!cat||d.k==cat)&&JSON.stringify(d).toLowerCase().includes(q));
  document.getElementById('g').innerHTML=rows.map(([d,i])=>{
    const lock=d.st=='TERKIRIM'?'disabled':'';
    const opts=['','KS','PM','LN','MM'].map(k=>`<option ${d.k==k?'selected':''}>${k}</option>`).join('');
    return `<div class=c><a href="/pdf/${encodeURIComponent(d.n)}" target=_blank><img loading=lazy src="/thumb/${encodeURIComponent(d.n)}"></a>
    <span class="b ${d.baru?'BARU':d.st}">${d.baru?'BARU':d.st}</span>${d.new?'<span class="b NEW">TERBARU</span>':''} <small>${d.kb} KB</small>
    <select id=k${i} ${lock}>${opts}</select><input id=t${i} placeholder=Tahun value="${esc(d.t)}" ${lock}>
    <input id=j${i} placeholder=Judul value="${esc(d.j)}" ${lock}><input id=p${i} placeholder=Penyelenggara value="${esc(d.p)}" ${lock}>
    ${lock?'':`<button onclick="save(${i})">Simpan</button>`}<div class=f>${esc(d.n)}</div></div>`}).join('');
}
async function save(i){
  const g=id=>document.getElementById(id+i).value;
  const r=await fetch('/api/set',{method:'POST',body:JSON.stringify({name:DATA[i].n,kategori:g('k'),tahun:g('t'),judul:g('j'),penyelenggara:g('p')})});
  if(!r.ok)alert(await r.text());
  last='';document.activeElement.blur();load();
}
load();setInterval(load,5000);
</script>"""

print(f"Dashboard: http://127.0.0.1:{os.environ.get('DASH_PORT', '8765')} (Ctrl+C untuk berhenti)")
ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("DASH_PORT", "8765"))), H).serve_forever()
