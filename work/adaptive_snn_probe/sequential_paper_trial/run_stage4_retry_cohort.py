"""Serial mapped-checkpoint retries only for the saved Synth20-411 tool failures."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
import run_stage4_route_checkpoint_retry as retry
original_sources=retry.sources
retry.sources=lambda:original_sources()|retry.pins([Path(__file__)])
def main():
    d=retry.read(P/'stage4_route_acceptance_v4.json');assert d['status']=='completed_with_retained_failures'
    retry.verify(d['source_sha256']);retry.verify(d['artifact_sha256'])
    engines=[]
    for row in d['failures']:
        assert 'Synth 20-411'in row['reason']
        engines.append(row['engine'])
    progress=P/'stage4_checkpoint_retry_progress.json';assert not progress.exists()
    state=dict(status='running',engines=engines,rows=[],failures=[])
    for e in engines:
        state['current_engine']=e;retry.write(progress,state)
        try:state['rows'].append(retry.route(e))
        except Exception as exc:state['failures'].append(dict(engine=e,reason=repr(exc)))
        retry.write(progress,state)
    state['status']='pass'if not state['failures']else'completed_with_retained_failures';retry.write(progress,state)
if __name__=='__main__':main()
