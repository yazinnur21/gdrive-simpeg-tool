import os, json, html, time, subprocess, sys, signal

B = os.path.dirname(os.path.abspath(__file__))
NAMA = {"KS": "Konferensi/Seminar/Lokakarya/Simposium", "PM": "Pengabdian kepada Masyarakat",
        "LN": "Luar Negeri", "MM": "Pengalaman Membimbing Mahasiswa"}
ORDER = ["KS", "PM", "LN", "MM"]
BDG = "<b style='background:#d00;color:#fff;padding:1px 6px;border-radius:8px'>TERBARU</b>"

def L(n):
    p = f"{B}/{n}.json"
    return json.load(open(p)) if os.path.exists(p) else {}
def rd(f):
    return set(l for l in open(f).read().splitlines() if l) if os.path.exists(f) else set()

def build():
    K, T, J, P = L("kategori"), L("tahun"), L("judul"), L("penyelenggara")
    done, man = rd(f"{B}/done.txt"), rd(f"{B}/manual.txt")
    wa = {f for f in os.listdir(f"{B}/wa-pdf") if f.lower().endswith(".pdf")}
    names = sorted((n for n in K if n in wa), key=lambda n: (ORDER.index(K[n]), n))
    baru = sorted(wa - set(K))
    nw = {f for f in wa if time.time() - os.path.getmtime(f"{B}/wa-pdf/{f}") < 259200}
    rows = []
    for i, n in enumerate(names, 1):
        st = "TERKIRIM" if n in done else ("MANUAL" if n in man else "BELUM")
        c = {"TERKIRIM": "#cfc", "MANUAL": "#fdd", "BELUM": "#fff"}[st]
        rows.append(f"<tr style='background:{c}'><td>{i}</td><td>{K[n]}</td><td>{NAMA[K[n]]}</td><td>{T.get(n) or ''}</td>"
                    f"<td>{html.escape(J.get(n, ''))}</td><td>{html.escape(P.get(n) or '')}</td><td>{st} {BDG if n in nw else ''}</td><td>{html.escape(n)}</td></tr>")
    for n in baru:
        rows.append(f"<tr style='background:#ecf'><td>+</td><td colspan=6>BARU (belum diisi datanya, isi di dashboard)</td><td>{html.escape(n)}</td></tr>")
    sent = len(done & set(K))
    h = ("<meta charset=utf-8><meta http-equiv=refresh content=10><style>body{font-family:sans-serif;margin:16px}"
         "table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #ccc;padding:4px 6px;text-align:left}"
         "th{background:#0a7;color:#fff;position:sticky;top:0}</style>"
         f"<b>Terkirim {sent} / {len(K)} | Sisa {len(K) - sent} | Baru {len(baru)} | Terbaru {len(nw & set(K))}</b> | diperbarui {time.strftime('%H:%M:%S')}<br><br>"
         "<div style=background:#f3faf7;border:1px solid #0a7;padding:10px 14px;margin-bottom:14px;line-height:1.5><b>Alur (mode server)</b><ol style=margin:6px 0><li><b>Seret</b> zip/gambar/PDF ke folder <code>~/gdrive-upload/masuk</code> di laptop. Otomatis terkirim ke server, diproses +-30 detik.</li><li>Klik ikon <b>Sertifikat Go</b>, login SIMPEG, buka tab menu (Pengalaman). Halaman ini dan dashboard terbuka otomatis.</li><li>Di <a href=/>dashboard</a> klik <b>TERBARU</b>, cek data, klik <b>Simpan</b>.</li><li>Klik ikon <b>Upload SIMPEG</b>, isi jumlah file. Kolom <b>No</b> di tabel ini dipakai untuk rentang <code>DARI</code>/<code>SAMPAI</code>.</li><li>Cek tabel <b>Tunggu</b> di SIMPEG.</li></ol></div><table><thead><tr><th>No</th><th>Kode</th><th>Jenis SIMPEG</th><th>Tahun</th><th>Judul</th><th>Penyelenggara</th><th>Status</th><th>File</th></tr></thead><tbody>"
         + "".join(rows) + "</tbody></table>")
    tmp = f"{B}/.final.html.tmp"
    open(tmp, "w").write(h)
    os.replace(tmp, f"{B}/final.html")

dash = subprocess.Popen([sys.executable, f"{B}/dashboard.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
signal.signal(signal.SIGTERM, lambda *a: (dash.terminate(), sys.exit(0)))
print("Dashboard live : http://127.0.0.1:" + os.environ.get("DASH_PORT", "8765"))
print("final.html     : file://" + B + "/final.html (dibangun ulang tiap 10 detik)")
print("Ctrl+C untuk berhenti")
try:
    while True:
        try:
            build()
        except Exception as e:
            print("build gagal:", e)
        time.sleep(10)
except KeyboardInterrupt:
    pass
finally:
    dash.terminate()
