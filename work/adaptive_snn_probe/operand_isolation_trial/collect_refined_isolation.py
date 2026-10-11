"""Collect the completed physical pass using Vivado's numeric route report."""
from pathlib import Path
import hashlib
import json
import math
import re
import sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import run_operand_isolation as trial


def collect():
    parent = P/'results/route_a0'
    wd = P/'results/route_phys_a0'
    assert not (wd/'hardware.json').exists(), 'Preserve prior collection'
    old = trial.read(parent/'hardware.json')
    trial.verify(old['source_sha256']); trial.verify(old['artifact_sha256'])
    stamps = trial.read(wd/'source_provenance.json')
    trial.verify(stamps)
    provenance = hashlib.sha256(json.dumps(stamps, sort_keys=True).encode()).hexdigest()
    assert (wd/'provenance.txt').read_text().splitlines()[0] == provenance
    job = trial.read(wd/'physopt.job.json')
    assert job['returncode'] == 0 and job['source_sha256'] == stamps
    log = (wd/'physopt.log').read_text()
    assert f'OPERAND_ISOLATION_POSTROUTE_REFINED {trial.TOP}' in log
    assert not re.search(r'^ERROR:', log, re.M)
    report = (wd/'route_status.rpt').read_text()
    labels = ('logical nets', 'nets not needing routing', 'routable nets',
              'fully routed nets', 'nets with routing errors')
    counts = {}
    for label in labels:
        found = re.findall(r'# of '+re.escape(label)+r'\.+\s*:\s*(\d+)\s*:', report)
        assert len(found) == 1, (label, found)
        counts[label] = int(found[0])
    assert counts['logical nets'] == counts['nets not needing routing']+counts['routable nets']
    assert counts['routable nets'] == counts['fully routed nets'] > 0
    assert counts['nets with routing errors'] == 0
    core = trial.route_helpers.util(wd/'core_util.rpt', False)
    full = trial.route_helpers.util(wd/'util.rpt')
    accounting = {k:int(v) for k,v in (line.split() for line in
        (wd/'fixture_accounting.txt').read_text().splitlines())}
    assert accounting['fixture_FF'] == full['FF']-core['FF'] == 219
    assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81
    assert core['DSP'] == full['DSP'] == 1
    slack = list(map(float, (wd/'slack.txt').read_text().splitlines()))
    boundary = list(map(float, (wd/'boundary_slack.txt').read_text().splitlines()))
    assert len(slack) == len(boundary) == 2 and all(map(math.isfinite, slack+boundary))
    checks = trial.functional()
    value = dict(status='pass' if min(slack)>=0 else 'timing_failed', top=trial.TOP,
        core=core, full_fixture=full, slice_accounting=accounting,
        WNS_ns=slack[0], WHS_ns=slack[1], boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
        source_sha256=stamps | trial.pins([Path(__file__)]), functional_check_sha256=checks,
        part=old['part'], clock_period_ns=6, hd_clk_src='BUFGCTRL_X0Y0',
        route_complete=True, route_counts=counts,
        parent_hardware_file=str(parent/'hardware.json'),
        parent_hardware_sha256=trial.sha(parent/'hardware.json'),
        parent_checkpoint_file=str(parent/'design.dcp'),
        parent_checkpoint_sha256=trial.sha(parent/'design.dcp'),
        refinement='One post-route phys_opt_design -directive Explore pass; no RTL, retiming or clock changes',
        collection_note='Vivado exited0; initial helper rejected route-report wording. This read-only collector proves completeness from numeric report; physical pass was not repeated.',
        artifact_sha256=trial.pins(path for path in wd.iterdir() if path.is_file()),
        scope='Same registered OOC fixture; core counts exclude219FF; raw-port timing separate; candidate-only extra implementation pass')
    trial.verify(value['source_sha256']); trial.verify(value['artifact_sha256'])
    trial.write(wd/'hardware.json', value)
    print('REFINEMENT COLLECTED', json.dumps({k:value[k] for k in ('status','core','WNS_ns','WHS_ns')}))


if __name__ == '__main__':
    collect()
