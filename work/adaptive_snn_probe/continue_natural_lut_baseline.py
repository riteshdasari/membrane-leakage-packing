"""Continue after a verifier import-path failure; preserve all old evidence."""
from pathlib import Path
import sys,time,hashlib,json
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;W=P/'residue_frontier_u13_trial';N=P/'natural_lut_baseline_trial'
sys.path.insert(0,str(W))
import run_u13_physical as run
assert '--run' in sys.argv
stamps=run.read(N/'preparation.json')['source_sha256'];run.verify(stamps)
launcher=N/'launch_verifier.py';assert not launcher.exists()
launcher.write_text(f'''import sys,runpy
sys.dont_write_bytecode=True
sys.path.insert(0,{W.as_posix()!r})
runpy.run_path({(N/'verify_native.py').as_posix()!r},run_name="__main__")
''')
stamps|=run.pins([Path(__file__),launcher])
native=[]
for kind in ('models','main'):
 for stall in (0,1):
    wd=N/f'native_{kind}_{stall}_a0';existing=wd.exists()
    if existing:
        assert kind=='models' and stall==0 and not (wd/'native_checks.json').exists()
        assert run.read(wd/'tool_4.job.json')['returncode']!=0
        assert "ModuleNotFoundError: No module named 'prepare_u13_work'" in (wd/'tool_4.log').read_text()
        run.verify(run.read(wd/'provenance.json'))
        for k in range(4):assert run.read(wd/f'tool_{k}.job.json')['returncode']==0
    else:
        wd.mkdir()
        run.tool([sys.executable,'-B',W/'prepare_u13_work.py','--kind',kind,'--directory',wd],wd,'prepare',stamps,.1)
    current=stamps|run.pins([wd/'stream_stim.txt',wd/'workload.json'])
    run.write(wd/('resume_provenance.json' if existing else 'provenance.json'),current)
    commands=[
     [run.base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}',
      '-d',f'CAPTURE_TRACE={int(kind=="models" and not stall)}',N/'natural_lut.sv',N/'tb_native.sv'],
     [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
     [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_frontier_u13_compare','glbl','-s','sim'],
     [run.base.VIVADO/'bin/xsim.bat','sim','-R']]
    if not existing:
        for k,command in enumerate(commands):
            while run.base.free()<=1.2:time.sleep(5)
            run.tool(command,wd,f'tool_{k}',current,1.2)
    run.tool([sys.executable,'-B',launcher,'--directory',wd,'--kind',kind,'--stall',stall,
              '--output',wd/'native_checks.json'],wd,'verify_a1',current,.1)
    check=run.read(wd/'native_checks.json');assert check['status']=='pass' and len(check['rows'])==1
    assert check['rows'][0]['engine']==2
    native.append(check|dict(check_file=str(wd/'native_checks.json')))
    print('NATURAL LUT NATIVE PASS',kind,stall,check['rows'][0]['service_clocks'],flush=True)
run.write(N/'native_acceptance.json',dict(status='pass',cohorts=native,source_sha256=stamps,
    retained_verifier_import_failure=True,
    scope='Operation-equivalent one-edge baseline. Independent oracle changed only for declared latency and one instance. Original failed import, sources and completed model0 simulator outputs preserved.'))
completion=W/'results/completion_progress.json'
func_export=P/'residue_frontier_f5_trial/results/diagnostic_routed_functional_a0/export.job.json'
while run.read(completion)['status'] not in ('all_checks_passed','completed_with_retained_failures') or not func_export.exists():time.sleep(5)
assert run.read(func_export)['returncode']==0
while run.base.free()<=2.3:time.sleep(5)
wd=N/'route_a0';assert not wd.exists();wd.mkdir()
current=stamps|run.pins([N/'native_acceptance.json'])
provenance=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()
command=[run.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
         '-source',N/'route.tcl','-tclargs','top_natural_lut',6,provenance,'fresh',wd]
try:run.tool(command,wd,'route',current)
except AssertionError:
    assert 'ERROR: [Synth 20-411]' in (wd/'route.log').read_text(errors='replace')
    assert (wd/'synth/design.dcp').exists() and (wd/'synth/provenance.txt').read_text().strip()==provenance
    command[-2]='resume';command[4]='vivado_resume.log';command[6]='vivado_resume.jou'
    run.tool(command,wd,'route_resume',current)
c=run.route_helpers.util(wd/'core_util.rpt',False);full=run.route_helpers.util(wd/'util.rpt')
assert c['DSP']==0 and full['FF']-c['FF']==338
slack=list(map(float,(wd/'slack.txt').read_text().splitlines()))
run.verify(current)
run.write(wd/'hardware.json',dict(status='pass' if min(slack)>=0 else 'timing_failed',core=c,
    full_fixture=full,fixture_FF=338,WNS_ns=slack[0],WHS_ns=slack[1],clock_period_ns=6,
    latency_advancing_edges=1,source_sha256=current,
    artifact_sha256=run.pins(p for p in wd.iterdir() if p.is_file()),
    scope='Operation-equivalent naturally shallow LUT baseline; matched338FF fixture. Resource/STA only, no accepted timing replay or energy.'))
print('NATURAL LUT ROUTE COMPLETE',c,slack,flush=True)
