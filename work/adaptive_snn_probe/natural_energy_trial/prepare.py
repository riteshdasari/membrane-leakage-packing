"""Prepare a new measurement adapter without modifying any executed predecessor."""
from pathlib import Path
import hashlib
import json

P = Path(__file__).resolve().parent
ROOT = P.parent
W = ROOT / 'residue_frontier_u13_trial'
J = ROOT / 'natural_u11_trial'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def put(name, text):
    path = P / name
    assert not path.exists(), path
    path.write_text(text, encoding='utf-8')

tb = (W / 'tb_frontier_u13_route_replay.sv').read_text()
for old, new in (
    ('tb_frontier_u13_route_replay', 'tb_natural_energy_replay'),
    ('[103:0]', '[87:0]'), ('[111:0]', '[95:0]'),
    ('[122:0]', '[106:0]'), ('[122:117]', '[106:101]'),
    ('[116:113]', '[100:97]'), ('[112:1]', '[96:1]'), ('[117]', '[101]'),
):
    assert old in tb, old
    tb = tb.replace(old, new)
put('tb_replay.sv', tb)
put('export.tcl', (W / 'export_u13.tcl').read_text())
power = (W / 'annotation_u13.tcl').read_text()
power = power.replace('tb_frontier_u13_route_replay', 'tb_natural_energy_replay')
power = power.replace('$engine > 5', '$engine > 4').replace('Engine outside 0..5', 'Engine outside 0..4')
put('power.tcl', power)

audit = (W / 'audit_u13_power.py').read_text()
start = audit.index('def functional_checks(')
end = audit.index('\ndef replay(', start)
new_function = '''def functional_checks(stamps, engine):
    """Require both the closed six-cohort U11 trial and exact captured replay."""
    assert engine in range(5) and stamps
    verify(stamps)
    original_file, = [Path(n) for n in stamps if Path(n).name == 'native_acceptance.json']
    original = read(original_file)
    assert original['status'] == 'pass' and len(original['cohorts']) == 6
    assert {(c['kind'],c['backpressure']) for c in original['cohorts']} == {
        (kind,stall) for kind in ('main','shift1','shift3') for stall in (False,True)}
    for key in ('source_sha256','artifact_sha256','prerequisites_sha256'):
        verify(original[key])
    for cohort in original['cohorts']:
        assert cohort['status'] == 'pass' and {r['engine'] for r in cohort['rows']} == set(range(5))
        assert all(r['status'] == 'pass' for r in cohort['rows'])
        verify(read(Path(cohort['check_file']).parent/'provenance.json'))
        verify(cohort['source_sha256']);verify(cohort['candidate_file_sha256'])
        if cohort['kind'] == 'main':assert cohort['exhaustive_scalar_pairs'] == 524288
        else:assert all(r['original_LIF_numeric_retirements_match'] for r in cohort['rows'])
    trace_file, = [Path(n) for n in stamps if Path(n).name == 'trace_checks.json']
    trace = read(trace_file)
    assert trace['status'] == 'pass' and trace['kind'] == 'shift3' and trace['backpressure'] is False
    verify(trace['source_sha256']);verify(trace['candidate_file_sha256'])
    assert len(trace['rows']) == 5 and all(r['status'] == 'pass' for r in trace['rows'])
    old, = [c for c in original['cohorts'] if c['kind'] == 'shift3' and not c['backpressure']]
    for a,b in zip(trace['rows'],old['rows']):
        for key in ('engine','requests','service_clocks','neurons','numeric_retirement_sha256','retirement_sha256'):
            assert a[key] == b[key], (key,a['engine'])
        assert a['neurons'] == SCALARS
        assert sha(a['trace_file']) == a['trace_sha256']
    return original['cohorts']

'''
audit = audit[:start] + new_function + audit[end:]
for old, new in (
    ("ROOT = 'tb_frontier_u13_route_replay/dut'", "ROOT = 'tb_natural_energy_replay/dut'"),
    ('engine in range(6)', 'engine in range(5)'),
    ("native_check['kind'] == 'models'", "native_check['kind'] == 'shift3'"),
    ("accounting['fixture_FF'] == 338 and accounting['launch_FF'] == 215 and accounting['capture_FF'] == 123",
     "accounting['fixture_FF'] == 290 and accounting['launch_FF'] == 183 and accounting['capture_FF'] == 107"),
    ("hardware['core']['FF'] == 338", "hardware['core']['FF'] == 290"),
    ('(0 if engine == 4 else 1)', '(1 if engine < 3 else 0)'),
    ('common 338-FF registered measurement fixture', 'common 290-FF registered measurement fixture'),
):
    assert old in audit, old
    audit = audit.replace(old, new)
put('audit_power.py', audit)

contract = '''This trial measures the frozen one-edge signed11 U plus signed8 I primitive,
on the original shift3 LIF trace, using the five existing matched routed checkpoints.
The original U11 scalar/protocol/LIF acceptance remains authoritative and unchanged.
A new native run enables the existing trace capture only; every retirement byte and
numeric digest must match the previously accepted unstalled shift3 run.

Only complete slow/max SDF replay with transport delays, zero pulse rejection/error,
enabled timing checks, matching all known trace data and all controls can supply SAIF.
The audit requires unchanged native intervals, all physical net aliases annotated,
no unknown time on any physical net, correct enabled clock activity, and the exact
source/checkpoint provenance. Failed attempts remain failures, with no energy claim.

Power is a vendor estimate for the full common 290-FF fixture at 25 C, typical process,
with the same 6 ns clock. It is not isolated core, state-memory, full-neuron, host or
board energy. Raw external I/O hold remains outside the internal route acceptance.
Vendor jobs are serial and memory-gated; no existing source, report or checkpoint is
edited. This adapter changes widths, engine mapping, fixture accounting and source
acceptance to U11; it does not relax functional, timing, interval or activity gates.
'''
put('CONTRACT.md', contract)
inputs = [Path(__file__), W/'tb_frontier_u13_route_replay.sv', W/'export_u13.tcl',
          W/'annotation_u13.tcl', W/'audit_u13_power.py', J/'native_acceptance.json',
          J/'hardware_acceptance.json']
generated = [P/n for n in ('tb_replay.sv','export.tcl','power.tcl','audit_power.py','CONTRACT.md')]
put('source_preparation.json', json.dumps({
    'status':'prepared',
    'source_sha256':{str(p):sha(p) for p in inputs},
    'generated_sha256':{str(p):sha(p) for p in generated},
    'scope':'New width/fixture adapter only; no completed replay or energy claim.'
},indent=2)+'\n')
print('NATURAL U11 ENERGY ADAPTER PREPARED', flush=True)
