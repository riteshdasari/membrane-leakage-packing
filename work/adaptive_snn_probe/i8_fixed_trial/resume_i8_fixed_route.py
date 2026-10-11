"""Resume one interrupted route without changing the frozen trial source pins.

Only --run launches Vivado. It requires a source/check-bound synthesis
checkpoint and keeps the already measured hybrid row and artifacts intact.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
import run_guard_add_i8_fixed_route as frozen

P, R = frozen.P, frozen.R
TOP = 'top_guard_add_i8_fixed_lut'


def prepare():
    pin = frozen.hashes()
    checks = frozen.functional(TOP, pin)
    provenance = hashlib.sha256(json.dumps(dict(
        top=TOP, engine=frozen.TOPS[TOP], variant=frozen.VARIANTS[TOP],
        target_ns=6.0, sources=pin, checks=checks,
        part='xc7a100tcsg324-1', hd_clk_src='BUFGCTRL_X0Y0'),
        sort_keys=True).encode()).hexdigest()
    pre = R / (TOP + '_synth')
    assert (pre / 'provenance.txt').read_text().strip() == provenance
    assert (pre / 'design.dcp').is_file()
    rows = json.loads((R / 'i8_fixed_hardware.json').read_text())
    assert [row['top'] for row in rows] == ['top_guard_add_i8_fixed_hybrid']
    assert rows[0]['source_sha256'] == pin and rows[0]['functional_check_sha256'] == checks
    assert all(frozen.sha(P / name) == stamp
               for name, stamp in rows[0]['route_artifact_sha256'].items())
    return pin, checks, provenance, pre, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    pin, checks, provenance, pre, rows = prepare()
    checkpoint_pin = frozen.sha(pre / 'design.dcp')
    helper_pin = frozen.sha(Path(__file__))
    summary_pin = frozen.sha(R / 'i8_fixed_hardware.json')
    if not args.run:
        print('Checkpoint and completed hybrid provenance PASS; no tools run.', flush=True)
        return
    memory = frozen.free()
    print(TOP, 'resume free GiB', round(memory, 2), flush=True)
    assert memory > 2.3, 'Insufficient free RAM'
    temporary = R / 'i8_fixed_tmp'
    temporary.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['TEMP'] = env['TMP'] = str(temporary)
    log = R / (TOP + '_resume_build.log')
    command = [str(frozen.VIVADO), '-mode', 'batch',
        '-log', f'results/{TOP}_resume_vivado.log',
        '-journal', f'results/{TOP}_resume_vivado.jou',
        '-source', 'route_guard_add_i8_fixed.tcl',
        '-tclargs', TOP, '6.0', provenance, 'resume']
    started = time.time()
    with log.open('w') as output:
        completed = subprocess.run(subprocess.list2cmdline(command), shell=True,
            cwd=P, env=env, stdout=output, stderr=subprocess.STDOUT)
    assert completed.returncode == 0, log.read_text()[-5000:]
    assert f'GUARD_ADD_I8_FIXED_TIMING_ROUTED {TOP}' in log.read_text()
    assert frozen.sha(Path(__file__)) == helper_pin
    assert frozen.hashes() == pin and frozen.functional(TOP, pin) == checks
    assert frozen.sha(pre / 'design.dcp') == checkpoint_pin
    assert frozen.sha(R / 'i8_fixed_hardware.json') == summary_pin
    assert all(frozen.sha(P / name) == stamp
               for name, stamp in rows[0]['route_artifact_sha256'].items())
    dest = R / (TOP + '_route')
    lines = (dest / 'provenance.txt').read_text().splitlines()
    assert lines[0] == provenance
    assert dict(line.split(maxsplit=1) for line in lines[1:]) == {
        'TOP': TOP, 'TARGET_NS': '6.0', 'VIVADO': '2025.2',
        'HD_CLK_SRC': 'BUFGCTRL_X0Y0'}
    assert (pre / 'provenance.txt').read_text().strip() == provenance
    full = frozen.util(dest / 'util.rpt')
    core = frozen.util(dest / 'core_util.rpt', False)
    accounting = {key: int(value) for key, value in (
        line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines())}
    assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81
    assert accounting['fixture_FF'] == 219
    assert full['FF'] - core['FF'] == 219 and full['LUT'] == core['LUT']
    assert full['DSP'] == core['DSP'] == 0
    assert full['occupied_slices'] == accounting['full_occupied_slices']
    assert accounting['full_occupied_slices'] == accounting['core_slices_touched'] \
        + accounting['fixture_slices_touched'] - accounting['shared_slices']
    assert accounting['core_exclusive_slices'] == accounting['core_slices_touched'] - accounting['shared_slices']
    assert accounting['fixture_exclusive_slices'] == accounting['fixture_slices_touched'] - accounting['shared_slices']
    assert all(value >= 0 for value in accounting.values())
    core['occupied_slices_reported'] = core['occupied_slices']
    core['occupied_slices'] = accounting['core_slices_touched']
    slack = list(map(float, (dest / 'slack.txt').read_text().splitlines()))
    boundary = list(map(float, (dest / 'boundary_slack.txt').read_text().splitlines()))
    assert len(slack) == len(boundary) == 2
    row = dict(top=TOP, engine=frozen.TOPS[TOP], variant=frozen.VARIANTS[TOP],
        target_ns=6.0, core=core, full_fixture=full,
        current_contract='signed8', operation='exact signed11 U + signed8 I -> signed12',
        fixture_overhead=dict(LUT=0, FF=219, DSP=0), slice_accounting=accounting,
        WNS_ns=slack[0], WHS_ns=slack[1], boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
        source_sha256=pin, functional_check_sha256=checks, provenance_sha256=provenance,
        route_artifact_sha256={str(path.relative_to(P)): frozen.sha(path)
            for folder in (pre, dest) for path in sorted(folder.rglob('*')) if path.is_file()},
        hd_clk_src='BUFGCTRL_X0Y0', retried_checkpoint=True,
        resume_helper_sha256=helper_pin, resume_checkpoint_sha256=checkpoint_pin,
        seconds=round(time.time() - started, 1),
        scope='Resumed exact statically-I8 retimed fixed route from source/check-bound checkpoint; '
              'same 219-FF fixture, 6 ns, source pins and arithmetic contract; no power or board claim')
    (R / 'i8_fixed_hardware.json').write_text(json.dumps(rows + [row], indent=2))
    print(json.dumps(dict(top=TOP, core=core, WNS_ns=slack[0], WHS_ns=slack[1], seconds=row['seconds'])), flush=True)


if __name__ == '__main__':
    main()
