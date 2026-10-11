"""Verify the isolated repair; wait for the original serial route queue."""
from pathlib import Path
import subprocess,sys,json,time
from check_stream_offset import free
P=Path(__file__).resolve().parent;R=P/'results'
for args in [['check_stream_centered.py'],['check_stream_offset_models.py','--centered']]:
 print('START',args,'free GiB',round(free(),2),flush=True);assert free()>2.2
 z=subprocess.run([sys.executable,*args],cwd=P);assert z.returncode==0,(args,z.returncode)
print('Waiting for original route queue before repair routing',flush=True)
while True:
 if (R/'stream_offset_hardware.json').exists()and len(json.loads((R/'stream_offset_hardware.json').read_text()))==10:break
 time.sleep(20)
args=['run_stream_centered_route.py','top_stream_centered_offset_const','top_stream_centered_offset_prog']
z=subprocess.run([sys.executable,*args],cwd=P);assert z.returncode==0,(args,z.returncode)
print('CENTERED REPAIR VERIFICATION AND ROUTING COMPLETE',flush=True)
