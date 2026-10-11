"""Continue this one authorized study serially, avoiding simultaneous route jobs."""
from pathlib import Path
import json,time,subprocess,sys
P=Path(__file__).resolve().parent;R=P/'results';start=time.time()
print('Waiting for the nine first-implementation routes before starting compact routes',flush=True)
while True:
 f=R/'adaptive_delta_hardware.json'
 rows=json.loads(f.read_text())if f.exists()else[]
 if len(rows)==9:break
 if time.time()-start>1800:raise RuntimeError('First route queue did not finish; no compact routes started')
 time.sleep(10)
subprocess.run([sys.executable,str(P/'run_adaptive_delta_compact_route.py'),
 'top_delta_compact_adapt_const','top_delta_compact_fixed_const',
 'top_delta_compact_adapt_prog','top_delta_compact_fixed_prog'],check=True)
subprocess.run([sys.executable,str(P/'audit_delta_boundary.py')],check=True)
print('All selected route and declared-boundary checks complete',flush=True)
