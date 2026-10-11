"""Actual two-value source control; no RTL or frozen-test changes."""
from pathlib import Path
import sys,time
sys.dont_write_bytecode=True
import run_u13_physical as run
import prepare_u13_work as prepare
import verify_frontier_u13 as checker
P=Path(__file__).resolve().parent
assert '--run' in sys.argv
while not all((P/'results'/f'native_{k}_{s}_a0/frontier_checks.json').exists()
              for k in ('main','models') for s in (0,1)):time.sleep(5)
wd=run.directory('supply2_models_0',0)
tb=wd/'tb_supply2.sv'
original=P/'tb_frontier_u13_compare.sv'
text=original.read_text()
old='av=(length-index>=8)?8:(length-index);'
assert text.count(old)==1
tb.write_text(text.replace(old,'av=(length-index>=2)?2:(length-index);'))
stamps=run.frozen()|run.sources()|run.functional()|run.pins([Path(__file__),
    P/'prepare_u13_work.py',P/'verify_frontier_u13.py',original,tb])
prepare.take_for=lambda engine,pairs,pos:min(2,len(pairs)-pos)
saved_argv=sys.argv[:]
try:
    sys.argv=[str(P/'prepare_u13_work.py'),'--kind','models','--directory',str(wd)]
    prepare.main()
finally:sys.argv=saved_argv
stamps|=run.pins([wd/'stream_stim.txt',wd/'workload.json'])
run.write(wd/'provenance.json',stamps)
commands=[
 [run.base.VIVADO/'bin/xvlog.bat','-sv','-d','STALL=0','-d','CAPTURE_TRACE=1',
  P.parent/'guard_add.sv',P/'guard_add_frontier_u13.sv',tb],
 [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
 [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_frontier_u13_compare','glbl','-s','sim'],
 [run.base.VIVADO/'bin/xsim.bat','sim','-R']]
for n,command in enumerate(commands):
    while run.base.free()<=1.2:time.sleep(5)
    run.tool(command,wd,f'tool_{n}',stamps,1.2)
checker.take_for=lambda engine,pairs,pos:min(2,len(pairs)-pos)
saved_argv=sys.argv[:]
try:
    sys.argv=[str(P/'verify_frontier_u13.py'),'--directory',str(wd),'--kind','models','--stall','0',
              '--output',str(wd/'frontier_checks.json')]
    checker.main()
finally:sys.argv=saved_argv
d=run.read(wd/'frontier_checks.json')
assert len({r['requests'] for r in d['rows']})==1 and len({r['service_clocks'] for r in d['rows']})==1
assert all(r['requests']==317952 and r['service_clocks']==354816 for r in d['rows'])
for row in d['rows']:
    with Path(row['trace_file']).open() as f:
        for line in f:
            fields=line.split()
            if int(fields[1]) and int(fields[4]) and int(fields[9]):assert 1<=int(fields[6])<=2
run.verify(stamps)
run.write(wd/'supply_control_acceptance.json',dict(status='pass',all_six_exact=True,
    all_original_IF_states_spikes_counts_classes_match=True,accepted_supply_never_exceeded_two=True,
    requests=317952,service_clocks=354816,source_sha256=stamps,
    checked_file_sha256=run.pins([wd/'frontier_checks.json']),
    scope='Actual ready/valid RTL simulation at two operands/issue, generous data model. No SRAM hardware or physical source-bandwidth claim.'))
print('U13 SUPPLY2 CONTROL PASS',flush=True)
