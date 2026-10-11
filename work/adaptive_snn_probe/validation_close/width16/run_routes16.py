"""Matched fixed16 routes, serial and source pinned; retained failed attempts."""
from pathlib import Path
import argparse,hashlib,json,math,re,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sys.path.insert(0,str(ROOT/'common_layout_trial'))
import run_guard_add_selective_route as helper
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
LABELS=['adaptive_precomp','fixed_split2','LUT2','scalar_DSP2','scalar_DSP1','adaptive_post','shift2_beta128']
DSP=[1,1,0,2,1,1,0]

def sources():
    prep=read(P/'preparation_v2.json')
    verify(prep['source_sha256']);verify(prep['artifact_sha256'])
    native=read(P/'hardware/native_general_s0_a0/acceptance.json')
    assert native['status']=='pass' and native['B']==16
    verify(native['source_sha256']);verify(native['artifact_sha256'])
    return prep['source_sha256']|prep['artifact_sha256']|pins([Path(__file__),P/'preparation_v2.json',P/'hardware/native_general_s0_a0/acceptance.json',ROOT/'selective_energy_trial/run_selective_energy.py',ROOT/'common_layout_trial/run_guard_add_selective_route.py'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--engines',default='0,1,2,3,4,5,6');ap.add_argument('--period',type=int,choices=[6,9,12],default=12);ap.add_argument('--attempt',required=True);args=ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
    engines=list(map(int,args.engines.split(',')));assert len(engines)==len(set(engines))and all(0<=e<=6 for e in engines)
    stamps=sources();progress=P/f'route_progress_{args.attempt}.json';assert not progress.exists()
    state=dict(status='running',B=16,period_ns=args.period,rows=[],failures=[],source_sha256=stamps)
    for e in engines:
        state['current_engine']=e;write(progress,state)
        wd=P/'hardware'/f'route{args.period}_e{e}_{args.attempt}';assert not wd.exists();wd.mkdir(parents=True)
        top=f'top_sequential_leak16_e{e}'
        prov=hashlib.sha256(json.dumps(dict(top=top,period_ns=args.period,part='xc7a100tcsg324-1',sources=stamps),sort_keys=True).encode()).hexdigest()
        write(wd/'source_provenance.json',stamps)
        try:
            verify(stamps)
            while base.free()<=2.45:time.sleep(5)
            cmd=[base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'route16.tcl','-tclargs',top,args.period,prov,'fresh',wd]
            log=base.job([str(x).replace('\\','/')for x in cmd],wd,'route',stamps,2.3)
            assert f'FRONTIER_TIMING_ROUTED {top}'in log.read_text()
            full=helper.util(wd/'util.rpt');core=helper.util(wd/'core_util.rpt',False)
            account={k:int(v)for k,v in(line.split()for line in(wd/'fixture_accounting.txt').read_text().splitlines())}
            assert(account['launch_FF'],account['capture_FF'],account['fixture_FF'])==(55,39,94)
            assert full['FF']-core['FF']==94 and full['LUT']==core['LUT']and full['DSP']==core['DSP']==DSP[e]
            assert full['occupied_slices']==account['full_occupied_slices']==account['core_slices_touched']+account['fixture_slices_touched']-account['shared_slices']
            slack=list(map(float,(wd/'slack.txt').read_text().splitlines()));boundary=list(map(float,(wd/'boundary_slack.txt').read_text().splitlines()))
            assert len(slack)==len(boundary)==2 and all(math.isfinite(v)for v in slack+boundary)
            fields=(wd/'provenance.txt').read_text().splitlines();assert fields[0]==prov
            verify(stamps)
            record=dict(status='pass'if min(slack+boundary)>=0 else'timing_failed',B=16,engine=e,label=LABELS[e],top=top,core=core,full_fixture=full,fixture_FF=94,slice_accounting=account,WNS_ns=slack[0],WHS_ns=slack[1],boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],clock_period_ns=args.period,latency_advancing_edges=2,part='xc7a100tcsg324-1',source_sha256=stamps,provenance_sha256=prov,artifact_sha256=pins(p for folder in(wd,wd/'synth')for p in folder.iterdir()if p.is_file()),scope='Matched fixed16 leakage primitive OOC route/STA; fixture94FF excluded from core area; E6 beta128 only. No board or complete-neuron energy result.')
            write(wd/'hardware.json',record);state['rows'].append(str(wd/'hardware.json'))
            print('ROUTE16',e,core,slack,boundary,flush=True)
        except Exception as exc:
            state['failures'].append(dict(engine=e,reason=repr(exc)));print('RETAINED FAILURE',e,repr(exc),flush=True)
        write(progress,state)
    state['status']='completed_with_retained_failures'if state['failures']or any(read(Path(p))['status']!='pass'for p in state['rows'])else'pass'
    write(progress,state);write(P/f'route_acceptance_{args.attempt}.json',state|dict(artifact_sha256=pins(map(Path,state['rows']))))
if __name__=='__main__':main()
