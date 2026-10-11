"""One source-pinned post-route physical optimization pass; no RTL changes."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import run_operand_isolation as trial


def run(attempt):
    parent = P/'results/route_a0'
    old = trial.read(parent/'hardware.json')
    trial.verify(old['source_sha256'])
    trial.verify(old['artifact_sha256'])
    assert old['top'] == trial.TOP and old['clock_period_ns'] == 6
    assert old['part'] == 'xc7a100tcsg324-1'
    checks = trial.functional()
    stamps = trial.frozen() | checks | trial.pins([
        Path(__file__), P/'refine_route_isolation.tcl', P/'run_operand_isolation.py',
        P/'route_operand_isolation.tcl', P/'guard_add_selective_isolated.sv',
        P/'guard_add_selective_isolated_timing.sv', parent/'hardware.json', parent/'design.dcp'])
    trial.verify(stamps)
    wd = trial.directory('route_phys', attempt)
    provenance = hashlib.sha256(json.dumps(stamps, sort_keys=True).encode()).hexdigest()
    trial.write(wd/'source_provenance.json', stamps)
    log = trial.tool([trial.base.VIVADO/'bin/vivado.bat', '-mode', 'batch',
        '-log', 'vivado.log', '-journal', 'vivado.jou', '-source',
        P/'refine_route_isolation.tcl', '-tclargs', trial.TOP, 6, provenance,
        parent/'design.dcp', wd], wd, 'physopt', stamps)
    assert f'OPERAND_ISOLATION_POSTROUTE_REFINED {trial.TOP}' in log.read_text()
    route_report = (wd/'route_status.rpt').read_text()
    # Require the vendor's positive completion statement, not just a saved DCP.
    assert re.search(r'\bDesign is fully routed\b', route_report, re.I), route_report
    core = trial.route_helpers.util(wd/'core_util.rpt', False)
    full = trial.route_helpers.util(wd/'util.rpt')
    accounting = {k:int(v) for k,v in (line.split() for line in
        (wd/'fixture_accounting.txt').read_text().splitlines())}
    assert accounting['fixture_FF'] == full['FF']-core['FF'] == 219
    assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81
    assert core['DSP'] == full['DSP'] == 1
    slack = list(map(float, (wd/'slack.txt').read_text().splitlines()))
    boundary = list(map(float, (wd/'boundary_slack.txt').read_text().splitlines()))
    value = dict(status='pass' if min(slack)>=0 else 'timing_failed', top=trial.TOP,
        core=core, full_fixture=full, slice_accounting=accounting,
        WNS_ns=slack[0], WHS_ns=slack[1], boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
        source_sha256=stamps, functional_check_sha256=checks, part=old['part'],
        clock_period_ns=6, hd_clk_src='BUFGCTRL_X0Y0', route_complete=True,
        parent_hardware_file=str(parent/'hardware.json'),
        parent_hardware_sha256=trial.sha(parent/'hardware.json'),
        parent_checkpoint_file=str(parent/'design.dcp'),
        parent_checkpoint_sha256=trial.sha(parent/'design.dcp'),
        refinement='One post-route phys_opt_design -directive Explore pass; no RTL, retiming or clock changes',
        artifact_sha256=trial.pins(path for path in wd.iterdir() if path.is_file()),
        scope='Same registered OOC fixture; core counts exclude219FF; raw-port timing separate; candidate-only extra implementation pass')
    trial.write(wd/'hardware.json', value)
    print('PHYSOPT COMPLETE', json.dumps({k:value[k] for k in ('status','core','WNS_ns','WHS_ns')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--attempt', type=int, default=0)
    args = parser.parse_args()
    assert args.run, 'Explicit --run required'
    run(args.attempt)
