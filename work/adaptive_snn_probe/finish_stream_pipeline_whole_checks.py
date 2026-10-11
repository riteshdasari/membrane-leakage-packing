"""Serial, RAM-gated checks; reuse only source/stimulus-matched completed runs."""
from pathlib import Path
import hashlib, json, runpy, sys, time
import check_stream_pipeline_whole as checker
P = Path(__file__).resolve().parent
original_simulate = checker.simulate

def resume_simulate(tag, frames, dc, stall, variant='pipeline', cw=0):
    saved = P/'results'/(tag+'_checks.json')
    if saved.exists():
        data = json.loads(saved.read_text())
        probe = P/'results'/'stream_pipeline_whole_resume_probe'
        probe.mkdir(exist_ok=True)
        checker.write_stim(probe, frames)
        stimulus = hashlib.sha256((probe/'stream_stim.txt').read_bytes()).hexdigest()
        if (data['source_hashes']==checker.hashes() and data['stimulus_sha256']==stimulus
            and data['constant_delta']==dc and data['backpressure']==bool(stall)
            and data['centered_wide']==bool(cw) and len(data['rows'])==7
            and all(row['mismatches']==0 for row in data['rows'])):
            print('Reuse checked source/stimulus',tag,flush=True)
            return data
    while checker.free() <= 1.5:
        print('Waiting for 1.5 GiB before',tag,'currently',round(checker.free(),2),flush=True)
        time.sleep(20)
    return original_simulate(tag,frames,dc,stall,variant,cw)

checker.simulate = resume_simulate
for args in [['check_stream_pipeline_whole.py'],['check_stream_pipeline_whole_models.py'],
             ['check_stream_pipeline_whole.py','--cw','1'],
             ['check_stream_pipeline_whole_models.py','--cw','1']]:
    while checker.free() <= 1.5:
        print('Waiting for 1.5 GiB free RAM before',args,'currently',round(checker.free(),2),flush=True)
        time.sleep(20)
    print('START',args,'free GiB',round(checker.free(),2),flush=True)
    sys.argv = args
    if args[0]=='check_stream_pipeline_whole.py':
        # runpy gives __main__ separate globals, so inject the guarded function
        # by explicitly using the already imported checker for both main runs.
        cw = int(args[-1]) if '--cw' in args else 0
        prefix = 'stream_pipeline_whole_centered' if cw else 'stream_pipeline_whole'
        frames = checker.test_frames(False)
        for dc,stall in [(25,0),(-1,1)]:
            resume_simulate(f'{prefix}_main_{dc}_{stall}',frames,dc,stall,cw=cw)
    else:
        runpy.run_path(str(P/args[0]),run_name='__main__')
print('STREAM PIPELINE WHOLE VERIFICATION COMPLETE',flush=True)
