"""Serial, source-pinned six-control routes after native acceptance."""
from pathlib import Path
import hashlib,json,math,sys,time,shutil
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sys.path.insert(0,str(ROOT/'common_layout_trial'))
import run_guard_add_selective_route as helper
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
LABELS=['adaptive_precomp','fixed_split2','LUT2','scalar_DSP2','scalar_DSP1','adaptive_post']
DSP=[1,1,0,2,1,1]
def sources():
    prep=read(P/'stage4_source_preparation.json');verify(prep['source_sha256']);verify(read(P/'stage4_route_v3_preparation.json')['source_sha256']);verify(read(P/'stage4_resume_v4_preparation.json')['source_sha256'])
    native=read(P/'stage4_native_acceptance_v4.json');assert native['status']=='pass'
    verify(native['source_sha256']);verify(native['artifact_sha256'])
    for path in native['cohorts']:
        d=read(Path(path));assert d['status']=='pass'
        verify(d['source_sha256']);verify(d['artifact_sha256'])
    return prep['source_sha256']|pins([Path(__file__),P/'stage4_native_acceptance_v4.json',P/'stage4_resume_v4_preparation.json',P/'stage4_route_v3_preparation.json',P/'route_replay_phase3.tcl',ROOT/'common_layout_trial/run_guard_add_selective_route.py',ROOT/'selective_energy_trial/run_selective_energy.py'])
def tool(command,wd,label,stamps):
    while base.free()<=2.45:time.sleep(5)
    return base.job([str(c).replace('\\','/')for c in command],wd,label,stamps,2.3)
def route(e):
    stamps=sources();wd=P/'hardware'/f'route_e{e}_a4';assert not wd.exists();wd.mkdir(parents=True)
    top=f'top_sequential_leak_e{e}'
    original=P/'hardware'/f'route_e{e}_a3'
    if not(original/'synth/design.dcp').exists()or not(original/'synth/provenance.txt').exists():original=P/'hardware'/f'route_e{e}_a0'
    reused=(original/'synth/design.dcp').exists()and(original/'synth/provenance.txt').exists()
    if reused:
        original_sources=read(original/'source_provenance.json');verify(original_sources)
        for path in (P/'leak_core.sv',P/'leak_dsp.sv',P/'timing.sv'):
            assert original_sources[str(path)]==sha(path)
        origin=pins([original/'synth/design.dcp',original/'synth/provenance.txt',original/'source_provenance.json'])
        stamps.update(origin);write(wd/'checkpoint_origin.json',dict(status='completed_synthesis_reused',original_source_sha256=original_sources,original_artifact_sha256=origin,arithmetic_unchanged=True,fixture_constraints_reapplied_before_placement=True))
        stamps.update(pins([wd/'checkpoint_origin.json']))
    provenance=hashlib.sha256(json.dumps(dict(top=top,target_ns=6,part='xc7a100tcsg324-1',sources=stamps),sort_keys=True).encode()).hexdigest()
    write(wd/'source_provenance.json',stamps)
    if reused:
        (wd/'synth').mkdir();shutil.copyfile(original/'synth/design.dcp',wd/'synth/design.dcp')
        (wd/'synth/provenance.txt').write_text(provenance+'\n')
    cmd=[base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'route_replay_phase3.tcl','-tclargs',top,6,provenance,'resume'if reused else'fresh',wd]
    log=tool(cmd,wd,'route',stamps);verify(stamps)
    assert f'FRONTIER_TIMING_ROUTED {top}'in log.read_text()
    full=helper.util(wd/'util.rpt');core=helper.util(wd/'core_util.rpt',False)
    account={k:int(v)for k,v in(line.split()for line in(wd/'fixture_accounting.txt').read_text().splitlines())}
    assert(account['launch_FF'],account['capture_FF'],account['fixture_FF'])==(47,31,78)
    assert full['FF']-core['FF']==78 and full['LUT']==core['LUT']and full['DSP']==core['DSP']==DSP[e]
    assert full['occupied_slices']==account['full_occupied_slices']==account['core_slices_touched']+account['fixture_slices_touched']-account['shared_slices']
    slack=list(map(float,(wd/'slack.txt').read_text().splitlines()));boundary=list(map(float,(wd/'boundary_slack.txt').read_text().splitlines()))
    assert len(slack)==len(boundary)==2 and all(math.isfinite(v)for v in slack+boundary)
    lines=(wd/'provenance.txt').read_text().splitlines();fields=dict(line.split(maxsplit=1)for line in lines[1:])
    assert lines[0]==provenance and fields['TOP']==top and fields['VIVADO']=='2025.2'and fields['HD_CLK_SRC']=='BUFGCTRL_X0Y0'and float(fields['TARGET_NS'])==6
    core['occupied_slices_reported']=core['occupied_slices'];core['occupied_slices']=account['core_slices_touched']
    record=dict(status='pass'if min(slack+boundary)>=0 else'timing_failed',engine=e,label=LABELS[e],top=top,core=core,full_fixture=full,fixture_FF=78,slice_accounting=account,WNS_ns=slack[0],WHS_ns=slack[1],boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],clock_period_ns=6,latency_advancing_edges=2,external_input_phase_ns=3.0,reused_completed_synthesis=reused,part='xc7a100tcsg324-1',source_sha256=stamps,provenance_sha256=provenance,artifact_sha256=pins(p for folder in(wd,wd/'synth')for p in folder.iterdir()if p.is_file()),scope='Matched leakage primitive OOC route and STA; 78 common fixture FF excluded from core area; no board, complete-neuron or energy result')
    write(wd/'hardware.json',record);print('STAGE4 ROUTE',e,core,slack,boundary,flush=True)
    return str(wd/'hardware.json')
def main():
    progress=P/'stage4_route_progress_v4.json';assert not progress.exists()
    state=dict(status='running',rows=[],failures=[],source_sha256=sources())
    for e in range(6):
        state['current_engine']=e;write(progress,state)
        try:state['rows'].append(route(e))
        except Exception as exc:
            state['failures'].append(dict(engine=e,reason=repr(exc)));print('STAGE4 ROUTE RETAINED FAILURE',e,repr(exc),flush=True)
        write(progress,state)
    state['status']='completed_with_retained_failures'if state['failures']or any(read(Path(p))['status']!='pass'for p in state['rows'])else'pass'
    write(progress,state);write(P/'stage4_route_acceptance_v4.json',state|dict(artifact_sha256=pins(map(Path,state['rows']))))
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--engine',type=int,choices=range(6),required=True);a=ap.parse_args();route(a.engine)
