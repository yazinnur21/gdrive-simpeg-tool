import os, re, time, random, json
from playwright.sync_api import sync_playwright

B = os.path.dirname(os.path.abspath(__file__))
L = lambda n: json.load(open(f"{B}/{n}.json"))
K, T, J, P, NB = L("kategori"), L("tahun"), L("judul"), L("penyelenggara"), L("namabaru")
VAL = {"KS": "PK", "PM": "KP", "MM": "MS", "LN": "LN"}
DONE, MANUAL = f"{B}/done.txt", f"{B}/manual.txt"
done = set(l for l in open(DONE).read().splitlines() if l) if os.path.exists(DONE) else set()
BAD = re.compile(r"jabatan|unit kerja|menerangkan|\bpi\b|\bser\b|kena umum|bahwa|\bor$|\bdut\b|persekolahan|instansi|administrasi|^-$|di penerbit|buku tersebut", re.I)
order = {"KS": 0, "PM": 1, "LN": 2, "MM": 3}
semua = sorted(K, key=lambda n: (order[K[n]], n))
DARI, SAMPAI = int(os.environ.get("DARI", "1")), int(os.environ.get("SAMPAI", str(len(semua))))
files = [n for i, n in enumerate(semua, 1) if DARI <= i <= SAMPAI and n not in done]
print(f"Rentang {DARI}-{SAMPAI} | antre: {len(files)}")
pause = lambda a, b: time.sleep(random.uniform(a, b))
LIMIT = int(os.environ.get("LIMIT", "9999"))

def ketik(pg, sel, teks):
    loc = pg.locator(sel)
    loc.click(timeout=20000)
    loc.press_sequentially(teks, delay=random.randint(45, 90))
    pause(.3, .8)

with sync_playwright() as p:
    br = p.chromium.connect_over_cdp(f"http://127.0.0.1:{os.environ.get('CDP_PORT', '9222')}")
    pg = next((pg for c in br.contexts for pg in c.pages if "simpeg5.kemenag.go.id/pengalaman" in pg.url), None)
    if not pg: raise SystemExit("Tab Pengalaman tidak ditemukan.")
    pg.bring_to_front()
    head = pg.get_by_text("Tambah Riwayat Pengalaman").first
    if head.is_visible():
        pg.get_by_role("button", name="Cancel").click(); pause(1, 2)
    n = 0
    for name in files:
        if n >= LIMIT: break
        y, pny = T.get(name), (P.get(name) or "")
        if not y or not pny or BAD.search(pny):
            open(MANUAL, "a").write(name + "\n"); print(f"LEWATI (data kurang): {name}"); continue
        n += 1
        judul = J.get(name) or re.sub(r"\.pdf$", "", name)[:200]
        path = f"{B}/wa-pdf-upload/{NB[name]}"
        try:
            pg.get_by_role("button", name=re.compile("Tambah pengalaman")).first.click(timeout=20000)
            head.wait_for(state="visible", timeout=30000); pause(1.5, 3)
            pg.evaluate("v => { const $s = window.jQuery('#kt_select2_pengalaman'); $s.val(v).trigger('change'); $s.trigger('select2:select'); }", VAL[K[name]]); pause(.8, 1.5)
            pg.locator("#kt_tahun").wait_for(state="visible", timeout=15000)
            got = pg.locator("#kt_select2_pengalaman").input_value()
            assert got == VAL[K[name]], f"jenis tidak terpilih: {got}"
            ketik(pg, "#kt_tahun", str(y))
            ketik(pg, 'input[name="A10"]', judul[:200])
            ketik(pg, 'input[name="A4"]', pny[:150])
            pg.locator("#dokumen").set_input_files(path); pause(2, 4)
            assert os.path.basename(path) in pg.locator("#dokumen").evaluate("e => e.files[0] ? e.files[0].name : ''"), "dokumen tidak terlampir"
            pg.get_by_role("button", name="Simpan").first.click(timeout=20000); pause(1, 2)
            pg.get_by_role("button", name="Ya, Simpan!").click(timeout=20000)
            head.wait_for(state="hidden", timeout=90000)
            open(DONE, "a").write(name + "\n")
            print(f"[{n}/{LIMIT}] OK {K[name]} | {y} | {judul}")
            pause(6, 12)
        except Exception as e:
            print(f"FAIL {name}: {str(e).splitlines()[0]}")
            pg.screenshot(path=f"{B}/simpeg-fail.png"); break
print("Selesai.")
