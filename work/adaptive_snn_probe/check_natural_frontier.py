"""Check natural-latency DSP/fixed/adaptive pipelines without changing frozen evidence."""
from pathlib import Path
import sys,time,json,hashlib
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;W=P/'residue_frontier_u13_trial';N=P/'natural_frontier_trial'
sys.path.insert(0,str(W))
import run_u13_physical as run
assert '--run' in sys.argv and not N.exists();N.mkdir()
core=P/'frontier_natural.sv'
tb=(W/'tb_frontier_u13_compare.sv').read_text()
tb=tb.replace('guard_add_frontier_u13 #(.E(E))dut','frontier_natural #(.E(E))dut')
for old,new in [('step-qstep[head%32]!=4','step-qstep[head%32]!=1'),
                ('cycle-qclk[head%32]<4','cycle-qclk[head%32]<1')]:
    assert old in tb;tb=tb.replace(old,new)
(N/'tb_native.sv').write_text(tb)
checker=(W/'verify_frontier_u13.py').read_text()
checker=checker.replace('P = Path(__file__).resolve().parent',f'P = Path({W.as_posix()!r})')
for old,new in [('advance-issued==4','advance-issued==1'),('advance==4','advance==1'),
                ('retire-accept>=4','retire-accept>=1'),('latmin==latmax==4','latmin==latmax==1')]:
    assert old in checker;checker=checker.replace(old,new)
checker=checker.replace('4advancingclocks','1advancingclock')
(N/'verify_native.py').write_text(checker)
launcher=N/'launch_verifier.py'
launcher.write_text(f'''import sys,runpy
sys.dont_write_bytecode=True
sys.path.insert(0,{W.as_posix()!r})
runpy.run_path({(N/'verify_native.py').as_posix()!r},run_name="__main__")
''')
fixture=(W/'guard_add_frontier_u13_timing.sv').read_text()
fixture=fixture.replace('guard_add_frontier_u13_timing','frontier_natural_timing')
fixture=fixture.replace('guard_add_frontier_u13 #(.E(E))core','frontier_natural #(.E(E))core')
fixture=fixture.replace('top_guard_add_frontier_u13_e','top_frontier_natural_e')
(N/'timing.sv').write_text(fixture)
route=(W/'route_u13.tcl').read_text()
route=route.replace('top_guard_add_frontier_u13_e','top_frontier_natural_e')
route=route.replace('read_verilog -sv $here/guard_add_frontier_u13.sv','read_verilog -sv $here/../frontier_natural.sv')
route=route.replace('read_verilog -sv $here/guard_add_frontier_u13_timing.sv','read_verilog -sv $here/timing.sv')
(N/'route.tcl').write_text(route)
stamps=run.pins([Path(__file__),core,N/'tb_native.sv',N/'verify_native.py',launcher,N/'timing.sv',N/'route.tcl',
 W/'tb_frontier_u13_compare.sv',W/'verify_frontier_u13.py',W/'guard_add_frontier_u13_timing.sv',
 W/'route_u13.tcl',W/'prepare_u13_work.py'])
run.write(N/'preparation.json',dict(source_sha256=stamps,scope=
 'All six operation-equivalent cores at one advancing edge. Direct DSP A/B/C to PREG, no DSP input/fabric residue banks. High metadata aligned in one fabric bank. Independent oracle only changes latency and implementation name.'))
native=[]
for kind in ('models','main'):
 for stall in (0,1):
    wd=N/f'native_{kind}_{stall}_a0';wd.mkdir()
    run.tool([sys.executable,'-B',W/'prepare_u13_work.py','--kind',kind,'--directory',wd],wd,'prepare',stamps,.1)
    current=stamps|run.pins([wd/'stream_stim.txt',wd/'workload.json'])
    run.write(wd/'provenance.json',current)
    commands=[
     [run.base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}',
      '-d',f'CAPTURE_TRACE={int(kind=="models" and not stall)}',core,N/'tb_native.sv'],
     [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
     [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_frontier_u13_compare','glbl','-s','sim'],
     [run.base.VIVADO/'bin/xsim.bat','sim','-R'],
     [sys.executable,'-B',launcher,'--directory',wd,'--kind',kind,'--stall',stall,
      '--output',wd/'native_checks.json']]
    for k,command in enumerate(commands):
        while run.base.free()<=1.2:time.sleep(5)
        run.tool(command,wd,f'tool_{k}',current,1.2)
    check=run.read(wd/'native_checks.json')
    assert check['status']=='pass' and {r['engine'] for r in check['rows']}==set(range(6))
    native.append(check|dict(check_file=str(wd/'native_checks.json')))
    print('NATURAL DSP FRONTIER NATIVE PASS',kind,stall,
          [(r['engine'],r['service_clocks']) for r in check['rows']],flush=True)
run.write(N/'native_acceptance.json',dict(status='pass',cohorts=native,source_sha256=stamps))
# Preserve the serialized heavy route/export/power queue. This can overlap only
# its low-memory native/timed simulation work above, never another heavy Vivado.
natural_lut=P/'natural_lut_baseline_trial/route_a0/hardware.json'
while not natural_lut.exists():time.sleep(5)
routes=[]
for engine in (5,2,3,4,0,1):
    while run.base.free()<=2.3:time.sleep(5)
    wd=N/f'route_e{engine}_a0';wd.mkdir()
    current=stamps|run.pins([N/'native_acceptance.json',natural_lut])
    provenance=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()
    command=[run.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
     '-source',N/'route.tcl','-tclargs',f'top_frontier_natural_e{engine}',6,provenance,'fresh',wd]
    try:run.tool(command,wd,'route',current)
    except AssertionError:
        assert 'ERROR: [Synth 20-411]' in (wd/'route.log').read_text(errors='replace')
        assert (wd/'synth/design.dcp').exists() and (wd/'synth/provenance.txt').read_text().strip()==provenance
        command[-2]='resume';command[4]='vivado_resume.log';command[6]='vivado_resume.jou'
        run.tool(command,wd,'route_resume',current)
    c=run.route_helpers.util(wd/'core_util.rpt',False);full=run.route_helpers.util(wd/'util.rpt')
    assert c['DSP']==int(engine!=4) and full['FF']-c['FF']==338
    slack=list(map(float,(wd/'slack.txt').read_text().splitlines()))
    run.verify(current)
    hardware=dict(status='pass' if min(slack)>=0 else 'timing_failed',engine=engine,core=c,
       full_fixture=full,fixture_FF=338,WNS_ns=slack[0],WHS_ns=slack[1],clock_period_ns=6,
       latency_advancing_edges=1,source_sha256=current,
       artifact_sha256=run.pins(p for p in wd.iterdir() if p.is_file()),
       scope='Natural-latency operation-equivalent DSP/fixed/adaptive cores. Resource/STA only; no accepted timed replay or energy.')
    run.write(wd/'hardware.json',hardware);routes.append(hardware)
    print('NATURAL DSP FRONTIER ROUTE COMPLETE',engine,c,slack,flush=True)
run.write(N/'hardware_acceptance.json',dict(status='routes_complete',routes=routes,source_sha256=stamps))
