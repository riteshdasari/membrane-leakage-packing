"""Serial native then route-only U11 comparison; pinned predecessors are immutable."""
from pathlib import Path
import argparse,hashlib,json,math,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sys.path.insert(0,str(ROOT/'common_layout_trial'))
import run_guard_add_selective_route as route_helpers
from workload import groups_for,predictions,MAP
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
def prerequisites(route=False):
    paths=[ROOT/'natural_lif_feedback_trial/acceptance.json',ROOT/'natural_supply2_trial/acceptance.json']
    for path in paths:
        d=read(path);assert d['status']=='pass',(path,d.get('status'))
        for key in ('source_sha256','artifact_sha256','candidate_file_sha256'):
            if key in d:verify(d[key])
    if route:
        progress=ROOT/'residue_frontier_u13_trial/results/ram_retry_progress.json'
        assert read(progress)['status']in('all_checks_passed','completed_with_retained_failures')
        paths.append(progress)
    return pins(paths)
def sources():
    h=read(P/'source_preparation.json');verify(h['source_sha256']);verify(h['generated_sha256'])
    paths=[P/n for n in ('CONTRACT.md','core.sv','timing.sv','tb_native.sv','route.tcl','prepare_sources.py','source_preparation.json','workload.py','verify_native.py','run_trial.py','check_algebra.py','algebra_certificate.json')]
    paths.extend([ROOT/'residue_frontier_trial/prepare_frontier_work.py',ROOT/'trained_reference_native_trial/prepare_restored_work.py',ROOT/'trained_reference_native_trial/verify_restored_native.py',base.P/'run_selective_energy.py',ROOT/'common_layout_trial/run_guard_add_selective_route.py',ROOT/'trained_reference_admission_study/manifest.json',ROOT/'trained_reference_admission_study/restored_reference_summary.json'])
    verify(read(ROOT/'trained_reference_admission_study/manifest.json')['files'])
    for shift in(1,3):
        paths.extend(ROOT/f'trained_reference_admission_study/leak_shift{shift}'/n for n in('stream_stim.txt','reference_ledger.json'))
        for stall in(0,1):paths.append(ROOT/'trained_reference_native_trial/results'/f'native_shift{shift}_stall{stall}_a1/native_checks.json')
    paths.extend(ROOT/'results'/f'model_seed{s}.npz'for s in range(3))
    return pins(paths)
def job(command,wd,label,stamps,gate):
    while base.free()<=gate:time.sleep(5)
    return base.job([str(x).replace('\\','/')for x in command],wd,label,stamps,gate)
def native(kind,stall,attempt):
    stamps=sources()|prerequisites();wd=P/'results'/f'native_{kind}_stall{stall}_a{attempt}'
    assert not wd.exists();wd.mkdir(parents=True);groups=groups_for(kind)
    with(wd/'stream_stim.txt').open('w',newline='\n')as stream:
        stream.write(str(len(groups))+'\n')
        for gap,pairs in groups:
            stream.write(f'{len(pairs)} {gap}\n')
            for u,i in pairs:stream.write(f'{u&2047:03x} {i&2047:03x}\n')
    workload=dict(status='pass',kind=kind,groups=len(groups),neurons=sum(len(v)for _,v in groups),
        predictions=predictions(groups),exhaustive_scalar_pairs=524288 if kind=='main'else 0,
        stimulus_sha256=sha(wd/'stream_stim.txt'),source_sha256=stamps)
    if kind!='main':
        ledger=ROOT/f'trained_reference_admission_study/leak_shift{kind[-1]}/reference_ledger.json'
        (wd/'reference_ledger.json').write_bytes(ledger.read_bytes());workload['ledger_sha256']=sha(ledger)
        stamps.update(pins([wd/'reference_ledger.json']))
    write(wd/'workload.json',workload);stamps.update(pins([wd/'stream_stim.txt',wd/'workload.json']));write(wd/'provenance.json',stamps)
    commands=[
        [base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}','-d','CAPTURE_TRACE=0',P/'core.sv',P/'tb_native.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_natural_u11','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-R'],
        [sys.executable,'-B',P/'verify_native.py','--directory',wd,'--kind',kind,'--stall',stall]]
    for n,command in enumerate(commands):job(command,wd,f'tool_{n}',stamps,1.2)
    verify(stamps);d=read(wd/'native_checks.json');print('NATURAL U11 NATIVE PASS',kind,stall,flush=True);return d|dict(check_file=str(wd/'native_checks.json'))
def native_acceptance():
    rows=[]
    for kind in('main','shift1','shift3'):
        for stall in(0,1):
            passed=[p for p in(P/'results').glob(f'native_{kind}_stall{stall}_a*/native_checks.json')if read(p)['status']=='pass']
            assert len(passed)==1,(kind,stall,passed);p=passed[0];d=read(p)
            assert d['kind']==kind and d['backpressure']==bool(stall)and {r['engine']for r in d['rows']}==set(range(5))
            verify(read(p.parent/'provenance.json'));verify(d['source_sha256']);verify(d['candidate_file_sha256'])
            rows.append(d|dict(check_file=str(p)))
    value=dict(status='pass',cohorts=rows,source_sha256=sources(),artifact_sha256=pins(Path(r['check_file'])for r in rows),
        prerequisites_sha256=prerequisites(),scope='One-edge U11 native exactness,protocol,and original shift1/shift3 actualfeedback only')
    target=P/'native_acceptance.json';assert not target.exists();write(target,value);return value
def functional():
    d=read(P/'native_acceptance.json');assert d['status']=='pass';verify(d['source_sha256']);verify(d['artifact_sha256']);verify(d['prerequisites_sha256'])
    for r in d['cohorts']:verify(r['candidate_file_sha256'])
    return pins([P/'native_acceptance.json'])
def route(engine,attempt):
    stamps=sources()|prerequisites(True)|functional();top=f'top_natural_u11_e{engine}'
    wd=P/'results'/f'route_e{engine}_a{attempt}';assert not wd.exists();wd.mkdir(parents=True)
    provenance=hashlib.sha256(json.dumps(dict(top=top,target_ns=6,part='xc7a100tcsg324-1',sources=stamps),sort_keys=True).encode()).hexdigest()
    write(wd/'source_provenance.json',stamps)
    command=[base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'route.tcl','-tclargs',top,6,provenance,'fresh',wd]
    retried=False
    try:log=job(command,wd,'route',stamps,2.3)
    except (RuntimeError,AssertionError):
        pre=wd/'synth';log=wd/'route.log'
        assert 'ERROR: [Synth 20-411]'in log.read_text()and(pre/'design.dcp').exists()and(pre/'provenance.txt').read_text().strip()==provenance
        retried=True;command[-2]='resume';log=job(command,wd,'route_resume',stamps,2.3)
    assert f'FRONTIER_TIMING_ROUTED {top}'in log.read_text();verify(stamps)
    full=route_helpers.util(wd/'util.rpt');core=route_helpers.util(wd/'core_util.rpt',False)
    account={k:int(v)for k,v in(line.split()for line in(wd/'fixture_accounting.txt').read_text().splitlines())}
    assert account['launch_FF']==183 and account['capture_FF']==107 and account['fixture_FF']==290
    assert full['FF']-core['FF']==290 and full['LUT']==core['LUT']and full['DSP']==core['DSP']==(1 if engine<3 else 0)
    assert full['occupied_slices']==account['full_occupied_slices']==account['core_slices_touched']+account['fixture_slices_touched']-account['shared_slices']
    slack=list(map(float,(wd/'slack.txt').read_text().splitlines()));boundary=list(map(float,(wd/'boundary_slack.txt').read_text().splitlines()))
    assert len(slack)==len(boundary)==2 and all(math.isfinite(v)for v in slack+boundary)
    fields=dict(line.split(maxsplit=1)for line in(wd/'provenance.txt').read_text().splitlines()[1:])
    assert (wd/'provenance.txt').read_text().splitlines()[0]==provenance
    assert fields['TOP']==top and fields['VIVADO']=='2025.2'and fields['HD_CLK_SRC']=='BUFGCTRL_X0Y0'and float(fields['TARGET_NS'])==6
    core['occupied_slices_reported']=core['occupied_slices'];core['occupied_slices']=account['core_slices_touched']
    value=dict(status='pass'if min(slack)>=0 else'timing_failed',engine=engine,label=MAP[engine],top=top,core=core,
        full_fixture=full,fixture_FF=290,slice_accounting=account,WNS_ns=slack[0],WHS_ns=slack[1],
        boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],clock_period_ns=6,latency_advancing_edges=1,
        part='xc7a100tcsg324-1',hd_clk_src='BUFGCTRL_X0Y0',source_sha256=stamps,provenance_sha256=provenance,
        retried_checkpoint=retried,artifact_sha256=pins(p for folder in(wd,wd/'synth')for p in folder.iterdir()if p.is_file()),
        scope='Route resource/STA only, same U11 operation and290FFfixture; no new SDF/energy or complete neuron-update result')
    write(wd/'hardware.json',value);print('NATURAL U11 ROUTE',engine,core,slack,flush=True);return value|dict(hardware_file=str(wd/'hardware.json'))
def hardware_acceptance():
    rows=[]
    for e in range(5):
        candidates=list((P/'results').glob(f'route_e{e}_a*/hardware.json'));assert len(candidates)==1
        p=candidates[0];d=read(p);verify(d['source_sha256']);verify(d['artifact_sha256']);assert d['engine']==e
        rows.append(d|dict(hardware_file=str(p)))
    value=dict(status='pass'if all(r['status']=='pass'for r in rows)else'completed_with_retained_failures',rows=rows,
        source_sha256=sources(),artifact_sha256=pins(Path(r['hardware_file'])for r in rows),prerequisites_sha256=prerequisites(True),
        scope='Five matched one-edge U11 core resource/STA rows only; no new one-edge routed energy claim')
    assert not(P/'hardware_acceptance.json').exists();write(P/'hardware_acceptance.json',value);return value
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--stage',choices=('native','route','native-acceptance','hardware-acceptance'),required=True)
    ap.add_argument('--kind',choices=('main','shift1','shift3'));ap.add_argument('--stall',type=int,choices=(0,1));ap.add_argument('--engine',type=int,choices=range(5));ap.add_argument('--attempt',type=int,default=0)
    a=ap.parse_args();assert a.run and a.attempt>=0
    if a.stage=='native':assert a.kind is not None and a.stall is not None;native(a.kind,a.stall,a.attempt)
    elif a.stage=='route':assert a.engine is not None;route(a.engine,a.attempt)
    elif a.stage=='native-acceptance':native_acceptance()
    else:hardware_acceptance()
if __name__=='__main__':main()
