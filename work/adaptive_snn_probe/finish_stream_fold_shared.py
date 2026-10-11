from pathlib import Path
import subprocess,sys,json,time
P=Path(__file__).resolve().parent;R=P/'results'
def run(args):
 print('START',args,flush=True);z=subprocess.run([sys.executable,*args],cwd=P);assert z.returncode==0,(args,z.returncode)
run(['check_stream_fold_shared.py']);run(['check_stream_fold_shared_models.py'])
while True:
 rows=json.loads((R/'stream_fold_hardware.json').read_text())if(R/'stream_fold_hardware.json').exists()else[]
 if len(rows)>=5:break
 print('Waiting for preceding serial hardware queue',flush=True);time.sleep(20)
run(['run_stream_fold_shared_route.py','top_stream_fold_shared_offset_prog','top_stream_fold_shared_absolute_prog'])
print('SHARED COEFFICIENT TABLE TRIAL COMPLETE',flush=True)
