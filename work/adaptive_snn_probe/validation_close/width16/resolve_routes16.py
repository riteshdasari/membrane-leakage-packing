"""Retained, source-identical checkpoint retries and an explicit route selection manifest."""
from pathlib import Path
import argparse, math, subprocess, sys, time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent.parent/'selective_energy_trial'))
import run_selective_energy as b

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--original',default='a0');ap.add_argument('--attempt',required=True);args=ap.parse_args()
    for name in (args.original,args.attempt):assert name.replace('_','').isalnum()
    original=P/f'route_acceptance_{args.original}.json';d=b.read(original)
    assert d['status']in('pass','completed_with_retained_failures') and d['period_ns']==12 and d['B']==16
    b.verify(d['source_sha256']);b.verify(d['artifact_sha256'])
    progress=P/f'route_resolution_{args.attempt}.json';assert not progress.exists()
    stamps=b.pins([Path(__file__),original,P/'run_routes16_checkpoint_retry.py',P.parent.parent/'selective_energy_trial/run_selective_energy.py'])
    state=dict(status='running',B=16,period_ns=12,original_acceptance=str(original),selected_routes={},retries=[],source_sha256=stamps)
    for engine in range(7):
        initial=P/'hardware'/f'route12_e{engine}_{args.original}'
        selected=initial
        if not (initial/'hardware.json').exists() or b.read(initial/'hardware.json')['status']!='pass':
            state['current_engine']=engine;b.write(progress,state)
            log=P/f'route_retry_e{engine}_{args.attempt}.log';assert not log.exists()
            start=time.time()
            with log.open('w',encoding='utf-8')as stream:
                rc=subprocess.run([sys.executable,'-B',str(P/'run_routes16_checkpoint_retry.py'),'--engine',str(engine),'--original-attempt',str(initial),'--attempt',args.attempt],cwd=P,stdout=stream,stderr=subprocess.STDOUT).returncode
            state['retries'].append(dict(engine=engine,returncode=rc,seconds=time.time()-start,log=str(log),log_sha256=b.sha(log)))
            b.write(progress,state)
            assert rc==0,('retained checkpoint retry failed',engine,str(log))
            selected=P/'hardware'/f'route12_e{engine}_{args.attempt}'
        hw=b.read(selected/'hardware.json')
        assert hw['status']=='pass'and hw['engine']==engine and hw['B']==16 and hw['clock_period_ns']==12
        assert hw['part']=='xc7a100tcsg324-1'and hw['top']==f'top_sequential_leak16_e{engine}'and hw['latency_advancing_edges']==2
        a=hw['slice_accounting'];assert (a['launch_FF'],a['capture_FF'],a['fixture_FF'])==(55,39,94)
        assert hw['full_fixture']['FF']-hw['core']['FF']==94 and hw['full_fixture']['LUT']==hw['core']['LUT']
        assert hw['core']['DSP']==hw['full_fixture']['DSP']==[1,1,0,2,1,1,0][engine]
        assert all(math.isfinite(hw[k])and hw[k]>=0 for k in ('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))
        b.verify(hw['source_sha256']);b.verify(hw['artifact_sha256']);b.verify(stamps)
        state['selected_routes'][str(engine)]=str(selected)
        b.write(progress,state)
        print('SELECTED ROUTE',engine,selected,hw['core'],flush=True)
    state['status']='pass';state['artifact_sha256']=b.pins(Path(path)/'hardware.json'for path in state['selected_routes'].values())
    state['selection_policy']='Reuse successful original attempts; retry failed attempts using source-identical completed synthesis. No selection by area or power.'
    b.write(progress,state);b.write(P/f'route_resolved_acceptance_{args.attempt}.json',state)
if __name__=='__main__':main()
