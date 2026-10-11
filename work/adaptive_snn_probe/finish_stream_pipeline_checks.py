"""Serial, RAM-gated smoke/main/model verification. No synthesis or routing."""
from pathlib import Path
import subprocess, sys, time
from check_stream_pipeline import free
P = Path(__file__).resolve().parent
for args in [['check_stream_pipeline.py','--small'],['check_stream_pipeline.py'],['check_stream_pipeline_models.py'],
             ['check_stream_pipeline.py','--small','--cw','1'],['check_stream_pipeline.py','--cw','1'],
             ['check_stream_pipeline_models.py','--cw','1']]:
    while free() <= 1.5:
        print('Waiting for 1.5 GiB free RAM before',args,'currently',round(free(),2),flush=True)
        time.sleep(20)
    print('START',args,'free GiB',round(free(),2),flush=True)
    result = subprocess.run([sys.executable,*args],cwd=P)
    assert result.returncode == 0, (args,result.returncode)
print('STREAM PIPELINE VERIFICATION COMPLETE',flush=True)
