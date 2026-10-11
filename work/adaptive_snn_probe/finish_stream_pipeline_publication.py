"""Finish this authorized local batch once its RAM-gated routes are complete.

This does not schedule recurring work or launch hardware jobs. The full
publisher independently checks route coverage, sources and functional evidence.
"""
from pathlib import Path
import json, subprocess, sys, time
from check_stream_pipeline_whole import free

P = Path(__file__).resolve().parent
hardware = P/'results'/'stream_pipeline_whole_hardware.json'
last_count = None
while True:
    rows = json.loads(hardware.read_text()) if hardware.exists() else []
    count = len({row['top'] for row in rows})
    if count != last_count:
        print('Final matched routes completed',count,'of 17',flush=True)
        last_count = count
    if count == 17:
        break
    assert count < 17, 'Unexpected final route coverage; inspect before publication'
    time.sleep(20)
while free() <= 1.2:
    print('Awaiting 1.2 GiB free RAM for final evidence publication',flush=True)
    time.sleep(20)
result = subprocess.run([sys.executable,'publish_stream_pipeline.py','--ready'],cwd=P)
assert result.returncode == 0, result.returncode
print('FINAL MATCHED PIPELINE EVIDENCE PUBLISHED',flush=True)
