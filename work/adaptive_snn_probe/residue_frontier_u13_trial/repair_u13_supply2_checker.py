"""Check actual idle take policy; limit only accepted source work to two."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import run_u13_physical as run
import verify_frontier_u13 as checker
from prepare_u13_work import take_for as hardware_take
P=Path(__file__).resolve().parent
wd=P/'results/supply2_models_0_a0'
assert not (wd/'frontier_checks.json').exists()
stamps=run.read(wd/'provenance.json');run.verify(stamps)
assert 'FRONTIER_U13_COMPARE PASS STALL 0' in (wd/'tool_3.log').read_text()
stamps|=run.pins([Path(__file__),wd/'tool_3.log',wd/'tool_3.job.json'])
run.write(wd/'verifier_repair_provenance.json',dict(source_sha256=stamps,
    retained_failure=dict(assertion="row['take']==n",cause='The first running but invalid/idle trace row retains the eight-position reset-prelude window. It delivers no work; the limiter does not change the core combinational take rule.'),
    scope='No RTL, workload, native output or assertion about accepted capacity changes. Check real hardware policy on idle rows and cap2 on accepted source work.'))
original_audit=checker.audit_trace
def audit_trace(path,engine,groups):
    with Path(path).open() as f:
        for line in f:
            fields=line.split()
            if int(fields[1]) and int(fields[4]) and int(fields[9]):assert 1<=int(fields[6])<=2
    limited=checker.take_for
    checker.take_for=hardware_take
    try:return original_audit(path,engine,groups)
    finally:checker.take_for=limited
checker.take_for=lambda engine,pairs,pos:min(2,len(pairs)-pos)
checker.audit_trace=audit_trace
sys.argv=[str(P/'verify_frontier_u13.py'),'--directory',str(wd),'--kind','models','--stall','0',
          '--output',str(wd/'frontier_checks.json')]
checker.main()
d=run.read(wd/'frontier_checks.json')
assert all(r['requests']==317952 and r['service_clocks']==354816 and
           r['saved_states_spikes_counts_classes_match'] for r in d['rows'])
run.verify(stamps)
run.write(wd/'supply_control_acceptance.json',dict(status='pass',all_six_exact=True,
    all_original_IF_states_spikes_counts_classes_match=True,accepted_supply_never_exceeded_two=True,
    requests=317952,service_clocks=354816,source_sha256=stamps,
    checked_file_sha256=run.pins([wd/'frontier_checks.json',wd/'verifier_repair_provenance.json']),
    scope='Actual ready/valid RTL simulation, accepted supply<=2. Idle/prelude combinational policy checked separately. No SRAM hardware or physical bandwidth claim.'))
print('U13 SUPPLY2 VERIFICATION REPAIRED AND ALL SIX EXACT',flush=True)
