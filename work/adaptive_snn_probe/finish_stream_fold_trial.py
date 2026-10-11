"""Verify the new algebra in RTL before serial routing after the prior queue."""
from pathlib import Path
import subprocess,sys,json,time
P=Path(__file__).resolve().parent;R=P/'results'
def run(args):
 print('START',args,flush=True)
 z=subprocess.run([sys.executable,*args],cwd=P);assert z.returncode==0,(args,z.returncode)
run(['check_stream_fold.py'])
run(['check_stream_fold_models.py'])
while True:
 rows=json.loads((R/'stream_unsigned_hardware.json').read_text())if(R/'stream_unsigned_hardware.json').exists()else[]
 if len(rows)>=6:break
 print('Waiting for preceding serial hardware queue',flush=True);time.sleep(20)
run(['run_stream_fold_route.py','top_stream_fold_offset_const','top_stream_fold_absolute_const','top_stream_fold_fixed3_const',
 'top_stream_fold_offset_prog','top_stream_fold_absolute_prog'])
print('FRACTION FOLD VERIFICATION AND ROUTING COMPLETE',flush=True)
