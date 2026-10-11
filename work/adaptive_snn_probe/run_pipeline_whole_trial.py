"""Final whole-correction trial: matched 6 ns constant and 8 ns programmable."""
from pathlib import Path
import subprocess, sys, time
from run_stream_pipeline_whole_route import check_functional, hashes
from check_stream_pipeline_whole import free
P = Path(__file__).resolve().parent
const = [f'top_stream_pipeline_whole_{e}_const' for e in
         ['adaptive','adaptive6','fixed2','lut2','lut3','fixed3','hybrid']]
const += [f'top_stream_pipeline_whole_{e}_cw_const' for e in ['adaptive','fixed2','hybrid']]
prog = [f'top_stream_pipeline_whole_{e}_prog' for e in
        ['adaptive','adaptive6','fixed2','lut2','lut3','fixed3','hybrid']]
for tops, target in [(const,'6.0'),(prog,'8.0')]:
    for top in tops:
        while True:
            try:
                check_functional(top,hashes())
                break
            except FileNotFoundError:
                print('Awaiting functional gate',top,flush=True)
                time.sleep(20)
        while free() <= 2.3:
            print('Waiting for 2.3 GiB before route',top,'currently',round(free(),2),flush=True)
            time.sleep(20)
        result = subprocess.run([sys.executable,'run_stream_pipeline_whole_route.py',top,'--target',target],cwd=P)
        assert result.returncode==0, (top,result.returncode)
print('WHOLE PIPELINE HARDWARE TRIAL COMPLETE',flush=True)
