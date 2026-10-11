"""Final matched baseline/candidate trial at a common 8 ns target."""
from pathlib import Path
import subprocess, sys
P = Path(__file__).resolve().parent
tops = [f'top_stream_pipeline_encoded_{e}_const' for e in
        ['adaptive','adaptive6','fixed2','lut2','lut3','fixed3','hybrid']]
tops += [f'top_stream_pipeline_encoded_{e}_cw_const' for e in ['adaptive','fixed2','hybrid']]
tops += [f'top_stream_pipeline_encoded_{e}_prog' for e in
         ['adaptive','adaptive6','fixed2','lut2','lut3','fixed3','hybrid']]
result = subprocess.run([sys.executable,'run_stream_pipeline_encoded_route.py',*tops,'--target','8.0'],cwd=P)
assert result.returncode==0, result.returncode
print('ENCODED PIPELINE HARDWARE TRIAL COMPLETE',flush=True)
