import os, re, time, random, subprocess
from playwright.sync_api import sync_playwright

B = os.path.dirname(os.path.abspath(__file__))
OUT = f"{B}/wa-pdf"
CHAT = os.environ.get("CHAT", "Huruf FR MAN 3")
MAX = int(os.environ.get("MAX", "30"))
REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive:")
TH = '[data-testid="document-thumb"]'
os.makedirs(OUT, exist_ok=True)

def rc(*a):
    return subprocess.run(["rclone", *a], check=True)

def nama(t):
    m = re.match(r'^Lihat "(.*)"$', t or "", re.S)
    return m.group(1) if m else (t or "")

print("== 1. Tarik dari Drive yang belum ada di lokal")
rc("copy", REMOTE, OUT, "--include", "*.pdf", "--ignore-existing", "-P")

print("== 2. Unduh dari WA Web")
baru, skip, gagal, seen = [], 0, [], set()
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(f"{B}/wa-profile", headless=False, accept_downloads=True,
                                               viewport={"width": 1300, "height": 1000})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    for a in range(6):
        try:
            pg.goto("https://web.whatsapp.com", timeout=60000); break
        except Exception:
            time.sleep(3)
    pg.wait_for_selector("#pane-side", timeout=300000)
    time.sleep(3)
    pg.keyboard.press("Control+Alt+Slash"); time.sleep(1)
    pg.keyboard.type(CHAT); time.sleep(3)
    print("Mencari chat:", CHAT, flush=True)
    hasil = pg.locator(f'span[title*="{CHAT}"]').first
    try:
        hasil.wait_for(timeout=20000)
    except Exception:
        ada = pg.locator("span[title]").evaluate_all("els => els.slice(0, 15).map(e => e.title)")
        raise SystemExit(f"Chat '{CHAT}' tidak ditemukan. Judul terlihat: {ada}")
    hasil.click()
    pg.wait_for_selector("#main", timeout=30000); time.sleep(6)
    main = pg.locator("#main")
    pg.mouse.move(700, 500)

    prev, same = None, 0
    for _ in range(400):
        pg.mouse.wheel(0, -5000); time.sleep(1.0)
        first = main.locator(TH).first.get_attribute("title") if main.locator(TH).count() else None
        same = same + 1 if first == prev else 0
        prev = first
        if same >= 6: break
    print("Riwayat teratas tercapai")

    idle = 0
    while idle < 10 and len(baru) < MAX:
        new = 0
        for i in range(main.locator(TH).count()):
            if len(baru) >= MAX: break
            d = main.locator(TH).nth(i)
            try:
                t = d.get_attribute("title", timeout=2000)
            except Exception:
                continue
            if not t or t in seen: continue
            seen.add(t); new += 1
            fn = nama(t)
            if os.path.exists(os.path.join(OUT, fn)):
                skip += 1; continue
            try:
                d.scroll_into_view_if_needed()
                try:
                    with pg.expect_download(timeout=8000) as dl:
                        d.click()
                except Exception:
                    with pg.expect_download(timeout=30000) as dl:
                        pg.locator('[data-icon*="download"], [aria-label="Unduh"], [title="Unduh"]').first.click()
                f = dl.value
                dst = os.path.join(OUT, f.suggested_filename)
                if os.path.exists(dst):
                    skip += 1
                else:
                    f.save_as(dst); baru.append(f.suggested_filename)
                    print(f"BARU [{len(baru)}] {f.suggested_filename}")
                pg.keyboard.press("Escape")
                time.sleep(random.uniform(3, 7))
            except Exception as e:
                gagal.append(fn); print(f"FAIL {fn}: {str(e).splitlines()[0]}")
                pg.keyboard.press("Escape")
        idle = 0 if new else idle + 1
        pg.mouse.move(700, 500); pg.mouse.wheel(0, 500); time.sleep(1.2)
    ctx.close()

print(f"\nDokumen terlihat: {len(seen)} | Baru: {len(baru)} | Sudah ada: {skip} | Gagal: {len(gagal)}")
for n in gagal: print("  -", n)

print("== 3. Upload ke Google Drive")
rc("copy", OUT, REMOTE, "--include", "*.pdf", "-P")
print("Selesai. Buka dashboard: sertifikat baru berstatus BARU.")
