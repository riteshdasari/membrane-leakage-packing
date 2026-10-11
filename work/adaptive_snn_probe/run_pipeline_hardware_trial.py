"""Serial full matched trial, after both original and stronger baseline gates."""
from pathlib import Path
import subprocess, sys
P = Path(__file__).resolve().parent
tops = []
for coef in ['const','prog']:
    for engine in ['adaptive','adaptive6','fixed2','lut2','lut3','fixed3','hybrid']:
        tops.append(f'top_stream_pipeline_{engine}_{coef}')
    for engine in ['adaptive','fixed2','hybrid']:
        tops.append(f'top_stream_pipeline_{engine}_cw_{coef}')
    for engine in ['lut3strong','hybridstrong']:
        tops.append(f'top_stream_pipeline_{engine}_{coef}')
    tops.append(f'top_stream_pipeline_hybridstrong_cw_{coef}')
result = subprocess.run([sys.executable,'run_stream_pipeline_route.py',*tops,'--target','6.0'],cwd=P)
assert result.returncode==0, result.returncode
print('MATCHED PIPELINE HARDWARE TRIAL COMPLETE',flush=True)
