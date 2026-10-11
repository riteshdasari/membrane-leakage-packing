"""Route the necessary matched baselines and exact monitor simplification."""
from pathlib import Path
import subprocess,sys,shutil
P=Path(__file__).resolve().parent
s=(P/'run_persistent_route.py').read_text().replace('route_persistent_unit.tcl','route_persistent_resume.tcl')
(P/'run_persistent_resume.py').write_text(s)
shutil.copyfile(P/'results'/'top_persist_fixed10_s3_build.log',P/'results'/'top_persist_fixed10_s3_failed_build.log')
jobs=[('run_persistent_resume.py',['top_persist_fixed10_s3']),('run_fast_route.py',['top_fast_adaptive10_s3','top_fast_lut10_s3'])]
for script,tops in jobs:
 r=subprocess.run([sys.executable,str(P/script),*tops],cwd=P)
 assert r.returncode==0,(script,r.returncode)
print('FINAL COMPARISON BUILDS COMPLETE',flush=True)
