import os,shutil,subprocess as s
S=os.path.expanduser("~/gdrive-upload"); D=os.path.dirname(os.path.abspath(__file__))
for f in ["wa_sync.py","dashboard.py","live_final.py","upload_simpeg.py","mulai.py"]:
    shutil.copy(f"{S}/{f}",f"{D}/{f}")
s.run(["git","add","-A"],cwd=D,check=True)
r=s.run(["git","commit","-m","update skrip"],cwd=D)
if r.returncode==0: s.run(["git","push"],cwd=D)
