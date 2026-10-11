"""Serial, RAM-gated all-engine main/model checks for both wide encodings."""
from pathlib import Path
import subprocess, sys, time
from check_stream_pipeline_encoded import free
P = Path(__file__).resolve().parent
for args in [['check_stream_pipeline_encoded.py'],['check_stream_pipeline_encoded_models.py'],
             ['check_stream_pipeline_encoded.py','--cw','1'],
             ['check_stream_pipeline_encoded_models.py','--cw','1']]:
    while free() <= 1.5:
        print('Waiting for 1.5 GiB free RAM before',args,'currently',round(free(),2),flush=True)
        time.sleep(20)
    print('START',args,'free GiB',round(free(),2),flush=True)
    result = subprocess.run([sys.executable,*args],cwd=P)
    assert result.returncode == 0, (args,result.returncode)
print('STREAM PIPELINE ENCODED VERIFICATION COMPLETE',flush=True)
