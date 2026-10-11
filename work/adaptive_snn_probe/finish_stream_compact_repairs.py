"""Complete exact checks and serial RAM-gated hardware comparisons."""
from pathlib import Path
import subprocess,sys,json,time
P=Path(__file__).resolve().parent;R=P/'results'
def run(args):
 print('START',args,flush=True)
 z=subprocess.run([sys.executable,*args],cwd=P)
 assert z.returncode==0,(args,z.returncode)
run(['check_stream_unsigned.py'])
run(['check_stream_unsigned_models.py'])
while True:
 rows=json.loads((R/'stream_compact_hardware.json').read_text())if(R/'stream_compact_hardware.json').exists()else[]
 if len(rows)>=3:break
 print('Waiting for the current compact constant-coefficient routing queue',flush=True);time.sleep(20)
run(['run_stream_compact_route.py','top_stream_compact_absolute_prog','top_stream_compact_hybrid_prog'])
run(['run_stream_unsigned_route.py','top_stream_unsigned_absolute_const','top_stream_unsigned_fixed2_const',
 'top_stream_unsigned_hybrid_const','top_stream_unsigned_absolute_prog','top_stream_unsigned_fixed2_prog','top_stream_unsigned_hybrid_prog'])
print('COMPACT REPAIRS VERIFICATION AND ROUTING COMPLETE',flush=True)
