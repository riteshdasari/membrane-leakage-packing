"""Serial RAM-gated routing of exact-checked, registered timing fixtures.

The fixture adds 83 preserved FFs and is NOT a production handshake adapter.
Main WNS/WHS cover the registered input arithmetic plus all internal/control
paths. Port timing is a separate OOC budget audit. Occupied slice sets overlap;
core_slices_touched is meaningful but cannot be subtracted from full slices.
No board Fmax, board latency, power, memory bandwidth, or full neuron update
claim follows from these reports.
"""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import time

P = Path(__file__).resolve().parent
R = P / 'results'
V = Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
SOURCES = ['continuous_leak.sv', 'continuous_timing.sv',
           'route_continuous.tcl', 'run_continuous_route.py']
ENGINES = dict(adaptive=7, hybrid=5)


class Mem(ctypes.Structure):
    _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                ('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong),
                ('rest', ctypes.c_ulonglong * 5)]


def hashes():
    return {name: hashlib.sha256((P / name).read_bytes()).hexdigest()
            for name in SOURCES}


def check_functional(top, stamps):
    match = re.fullmatch(r'top_continuous_(adaptive|hybrid)_(const|prog)', top)
    if not match or match[1] not in ENGINES:
        raise ValueError(f'Unknown timing fixture top: {top}')
    engine = ENGINES[match[1]]
    # A programmable route requires the programmable backpressure check too.
    stem = 'continuous_main'
    core_source = 'continuous_leak.sv'
    checks = [stem + '_25_0_checks.json', 'continuous_models_checks.json', 'continuous_stress_checks.json']
    if match[2] == 'prog':
        checks.append(stem + '_-1_1_checks.json')
    evidence = {}
    for name in checks:
        data = json.loads((R / name).read_text())
        assert data['source_hashes'][core_source] == stamps[core_source], name
        assert data['frames'] > 0 and data['acceptance_to_handshake_advances'] == 4, name
        assert data['tested_engines'] == [5,7] and data['matched_whole_stimulus'] is True, name
        assert hashlib.sha256((R/name.removesuffix('_checks.json')/'stream_stim.txt').read_bytes()).hexdigest() == data['stimulus_sha256'], name
        row = next(row for row in data['rows'] if row['engine'] == engine)
        assert row['mismatches'] == 0 and row['neurons'] > 0, (name, row)
        if name in ('continuous_models_checks.json','continuous_stress_checks.json'):
            assert row['clocks'] == row['requests']+4, name
        if name == 'continuous_models_checks.json':
            assert row['state_mismatches'] == row['spike_mismatches'] == 0, name
        # Pin the testbench too: the evidence must still describe current files.
        for checked_source, stamp in data['source_hashes'].items():
            assert hashlib.sha256((P / checked_source).read_bytes()).hexdigest() == stamp, checked_source
        evidence[name] = hashlib.sha256((R / name).read_bytes()).hexdigest()
    return evidence


def parse_util(path, occupied_required=True):
    text = path.read_text()
    def get(label):
        found = re.search(r'\|\s*' + re.escape(label) + r'\*?\s*\|\s*([\d.]+)', text)
        assert found, (path, label)
        return int(float(found[1]))
    occupied = re.search(r'\|\s*Slice\s*\|\s*([\d.]+)', text)
    if occupied_required:
        assert occupied, (path, 'Slice')
    return dict(LUT=get('Slice LUTs'), FF=get('Slice Registers'), DSP=get('DSPs'),
                RAMB18=get('RAMB18'), RAMB36=get('RAMB36/FIFO*'),
                occupied_slices=int(float(occupied[1])) if occupied else None)


def parse_row(top, target, stamps, checks, provenance, seconds, retried):
    dest = R / f'{top}_route'
    assert (dest / 'provenance.txt').read_text().splitlines()[0] == provenance
    full, core = parse_util(dest / 'util.rpt'), parse_util(dest / 'core_util.rpt', False)
    accounting = {key: int(value) for key, value in
                  (line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines())}
    assert accounting['fixture_FF'] == 83, accounting
    assert full['FF'] - core['FF'] == 83, (full, core, accounting)
    assert full['LUT'] == core['LUT'] and full['DSP'] == core['DSP'], (full, core)
    assert full['occupied_slices'] == accounting['full_occupied_slices'], (full, accounting)
    # Selected-cell utilization reports may omit physical slice distribution;
    # the independently recorded site set supplies the core occupancy directly.
    core['occupied_slices_reported'] = core['occupied_slices']
    core['occupied_slices'] = accounting['core_slices_touched']
    main = list(map(float, (dest / 'slack.txt').read_text().splitlines()))
    boundary = list(map(float, (dest / 'boundary_slack.txt').read_text().splitlines()))
    assert len(main) == len(boundary) == 2
    return dict(top=top, target_ns=target, full_fixture=full, core=core,
                fixture_overhead=dict(LUT=full['LUT']-core['LUT'], FF=83,
                                      DSP=full['DSP']-core['DSP']),
                slice_accounting=accounting,
                WNS_ns=main[0], WHS_ns=main[1],
                clock_to_clock_period_estimate_ns=target-main[0],
                boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
                boundary_period_estimate_ns=target-boundary[0],
                seconds=round(seconds, 1), source_sha256=stamps,
                functional_check_sha256=checks, provenance_sha256=provenance,
                retried_checkpoint=retried, hd_clk_src='BUFGCTRL_X0Y0',
                scope='registered OOC timing fixture; not a production interface or board measurement')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('tops', nargs='+')
    ap.add_argument('--target', type=float, default=None, help='Optional: must equal 6ns constant or 8ns programmed target.')
    ap.add_argument('--min-free-gib', type=float, default=2.3)
    args = ap.parse_args()
    assert (args.target is None or args.target > 0) and args.min_free_gib >= 2.3
    R.mkdir(exist_ok=True)
    stamps = hashes()
    summary = R / 'continuous_hardware.json'
    rows = json.loads(summary.read_text()) if summary.exists() else []
    for top in args.tops:
        target = 8.0 if top.endswith('_prog') else 6.0
        assert args.target is None or args.target == target, ('Incorrect coefficient-cohort target',top,args.target)
        assert hashes() == stamps, 'A build source changed during queue'
        checks = check_functional(top, stamps)
        pin = dict(top=top, target_ns=target, sources=stamps, checks=checks,
                   part='xc7a100tcsg324-1', hd_clk_src='BUFGCTRL_X0Y0')
        provenance = hashlib.sha256(json.dumps(pin, sort_keys=True).encode()).hexdigest()
        if any(row['top'] == top and row.get('provenance_sha256') == provenance for row in rows):
            print('Already complete', top, flush=True)
            continue
        memory = Mem()
        memory.length = ctypes.sizeof(memory)
        assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
        print(top, 'free GiB', round(memory.free/2**30, 2), flush=True)
        assert memory.free > args.min_free_gib * 2**30, 'Insufficient free RAM for routing'
        tmp = R / 'continuous_tmp'
        tmp.mkdir(exist_ok=True)
        env = os.environ.copy()
        env['TEMP'] = str(tmp)
        env['TMP'] = str(tmp)
        # Stale DCPs cannot satisfy a fresh attempt's resume condition. The Tcl
        # writes this pin only after this attempt writes its checked checkpoint.
        pre_pin = R / f'{top}_synth' / 'provenance.txt'
        if pre_pin.exists():
            pre_pin.unlink()
        started = time.time()
        retried = False
        for attempt in range(2):
            assert hashes() == stamps, 'A build source changed before Vivado'
            suffix = '_resume' if attempt else ''
            log = R / f'{top}{suffix}_build.log'
            command = [str(V), '-mode', 'batch', '-log', f'results/{top}{suffix}_vivado.log',
                       '-journal', f'results/{top}{suffix}_vivado.jou',
                       '-source', 'route_continuous.tcl', '-tclargs', top,
                       str(target), provenance, 'resume' if attempt else 'fresh']
            with log.open('w') as output:
                result = subprocess.run(subprocess.list2cmdline(command), shell=True,
                                        cwd=P, env=env, stdout=output, stderr=subprocess.STDOUT)
            if result.returncode == 0:
                break
            failure = log.read_text()
            dcp = R / f'{top}_synth' / 'design.dcp'
            valid_resume = (dcp.exists() and pre_pin.exists() and
                            pre_pin.read_text().strip() == provenance)
            if attempt == 0 and 'ERROR: [Synth 20-411]' in failure and valid_resume:
                retried = True
                continue
            raise RuntimeError(failure[-5000:])
        assert hashes() == stamps, 'A build source changed while Vivado ran'
        assert check_functional(top, stamps) == checks, 'Functional evidence changed during routing'
        row = parse_row(top, target, stamps, checks, provenance, time.time()-started, retried)
        rows = [old for old in rows if old['top'] != top]
        rows.append(row)
        summary.write_text(json.dumps(rows, indent=2))
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()






