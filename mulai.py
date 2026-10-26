import os,sys,subprocess,shutil,time,urllib.request,webbrowser
B=os.path.dirname(os.path.abspath(__file__))
CDP=os.environ.get("CDP_PORT","9222")
C=[shutil.which("brave"),shutil.which("brave-browser")]+[os.path.join(os.environ.get(k,""),r"BraveSoftware\Brave-Browser\Application\brave.exe") for k in ("ProgramFiles","ProgramFiles(x86)","LocalAppData")]
BR=next((c for c in C if c and os.path.exists(c)),None)
if not BR: sys.exit("Brave tidak ditemukan")
def up():
    try: urllib.request.urlopen(f"http://127.0.0.1:{CDP}/json/version",timeout=2); return True
    except Exception: return False
if not up():
    subprocess.Popen([BR,f"--remote-debugging-port={CDP}",f"--user-data-dir={os.path.join(B,'brave-debug')}","https://simpeg5.kemenag.go.id/pengalaman"])
    for _ in range(30):
        if up(): break
        time.sleep(1)
subprocess.Popen([sys.executable,"-X","utf8",os.path.join(B,"live_final.py")],cwd=B,env={**os.environ,"PYTHONUTF8":"1"})
time.sleep(2)
webbrowser.open("http://127.0.0.1:"+os.environ.get("DASH_PORT","8765"))
