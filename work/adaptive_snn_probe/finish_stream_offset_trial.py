"""Serial verification, model replay and RAM-gated routing; no downloads."""
from pathlib import Path
import subprocess,sys
P=Path(__file__).resolve().parent
jobs=[['check_stream_offset.py'],['check_stream_offset_models.py'],['run_stream_offset_route.py',
 'top_stream_offset_const','top_stream_fixed2_const','top_stream_fixed3_const',
 'top_stream_lut3_const','top_stream_absolute_const','top_stream_lut2_const',
 'top_stream_offset_prog','top_stream_fixed2_prog','top_stream_fixed3_prog','top_stream_lut3_prog']]
for args in jobs:
 print('START',args,flush=True)
 z=subprocess.run([sys.executable,*args],cwd=P)
 assert z.returncode==0,(args,z.returncode)
print('STREAM OFFSET VERIFICATION AND ROUTING COMPLETE',flush=True)
