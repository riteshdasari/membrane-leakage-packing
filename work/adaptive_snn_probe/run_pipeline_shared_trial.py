"""Target only changed adaptive and positive-constant DSP mappings."""
from pathlib import Path
import subprocess, sys
P = Path(__file__).resolve().parent
tops = [f'top_stream_pipeline_shared_{e}_const' for e in
        ['adaptive','adaptive6','fixed2','fixed3','hybrid']]
tops += [f'top_stream_pipeline_shared_{e}_cw_const' for e in ['adaptive','fixed2','hybrid']]
tops += [f'top_stream_pipeline_shared_{e}_prog' for e in ['adaptive','adaptive6']]
result = subprocess.run([sys.executable,'run_stream_pipeline_shared_route.py',*tops,'--target','6.0'],cwd=P)
assert result.returncode==0, result.returncode
print('SHARED PIPELINE HARDWARE TRIAL COMPLETE',flush=True)
