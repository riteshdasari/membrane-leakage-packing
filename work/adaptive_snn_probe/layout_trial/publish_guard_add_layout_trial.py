"""Validate completed layout experiments and publish a separate UTF-8 report.

Imports and default invocation are read-only. Use --ready after both routes,
four full exact checksets and saved SNN reconstruction have completed.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import sys

import run_guard_add_layout_route as route

P = Path(__file__).resolve().parent
R = P / 'results'
ORIGINAL = P.parent
O = P.parents[2] / 'outputs'
STEM = 'guarded_membrane_layout_trial'
sys.path.insert(0, str(ORIGINAL))
import publish_guard_add_trial as baseline

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return route.sha(path)

def link(path, label):
    return f'[{label}](<{path.resolve().as_posix()}>)'

def vector(row):
    c = row['core']
    return f"{c['LUT']} LUT / {c['FF']} FF / {c['DSP']} DSP"

def passes(row):
    return row['WNS_ns'] >= 0 and row['WHS_ns'] >= 0

def delta(a, b):
    return {k: a['core'][k]-b['core'][k] for k in ('LUT','FF','DSP')}

def validate():
    source = route.hashes()
    evidence = route.functional('top_guard_add_layout_v0', source)
    old = baseline.validate()
    assert source['../guard_add.sv'] == old['source_sha256']['guard_add.sv']
    suites = {n: read(R/n) for n in route.SUITES}
    checked_outputs = 0
    for name, suite in suites.items():
        old_suite = old['suites'][name.replace('layout_', 'guard_add_', 1)]
        ref = next(row for row in old_suite['rows'] if row['engine'] == 0)
        assert suite['frames'] == old_suite['frames']
        assert suite['stimulus_sha256'] == old_suite['stimulus_sha256']
        for row in suite['rows']:
            for field in ('requests','neurons','narrow_requests','copy_requests','clocks',
                          'input_stall_checks','output_stall_checks','latency_checks','output_sha256'):
                assert row[field] == ref[field], (name, row['variant'], field)
            checked_outputs += row['neurons']
    assert checked_outputs == 8684490
    snn = read(R/'layout_snn_checks.json')
    assert len(snn['rows']) == 6
    for row in snn['rows']:
        ref = next(item for item in old['snn']['rows'] if item['engine'] == 0
                   and item['backpressure'] == row['backpressure'])
        assert row['model_rows'] == ref['model_rows']

    screen = read(R/'layout_arithmetic_screen.json')
    assert screen['script_sha256'] == sha(P/'screen_guard_add_layout.py')
    assert screen['core_sha256'] == source['guard_add_layout.sv']
    assert screen['exhaustive_scalar_pairs'] == {'7':16384, '11':4194304}
    assert screen['packed_cases'] == 101014 and screen['mismatches'] == 0
    assert screen['physical_wide_order'] == [0,1,3,2]
    assert screen['physical_narrow_order'] == list(range(6))
    hardware = read(R/'layout_hardware.json')
    assert len(hardware) == 2 and {row['top'] for row in hardware} == set(route.TOPS)
    ordered = {row['variant']:row for row in hardware}
    assert set(ordered) == {0,1}
    for variant, row in ordered.items():
        assert row['variant'] == route.TOPS[row['top']] and row['target_ns'] == 6.0
        assert row['source_sha256'] == source and row['functional_check_sha256'] == evidence
        assert row['hd_clk_src'] == 'BUFGCTRL_X0Y0'
        expected = hashlib.sha256(json.dumps(dict(top=row['top'], variant=variant,
            target_ns=6.0, sources=source, checks=evidence, part='xc7a100tcsg324-1',
            hd_clk_src='BUFGCTRL_X0Y0'), sort_keys=True).encode()).hexdigest()
        assert row['provenance_sha256'] == expected
        dest = R/(row['top']+'_route')
        assert (dest/'provenance.txt').read_text().splitlines()[0] == expected
        assert (R/(row['top']+'_synth')/'provenance.txt').read_text().strip() == expected
        for report in baseline.REPORTS:
            assert (dest/report).is_file(), (variant, report)
        accounting = {k:int(v) for k,v in (line.split() for line in
                      (dest/'fixture_accounting.txt').read_text().splitlines())}
        assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81
        assert accounting['fixture_FF'] == 219
        full, core = route.util(dest/'util.rpt'), route.util(dest/'core_util.rpt',False)
        core['occupied_slices_reported'] = core['occupied_slices']
        core['occupied_slices'] = accounting['core_slices_touched']
        assert row['core'] == core and row['full_fixture'] == full
        assert row['slice_accounting'] == accounting
        assert full['FF']-core['FF'] == 219 and full['LUT'] == core['LUT']
        assert full['DSP'] == core['DSP'] == 1
        assert full['occupied_slices'] == accounting['full_occupied_slices']
        assert row['fixture_overhead'] == {'LUT':0,'FF':219,'DSP':0}
        for report, keys in [('slack.txt',('WNS_ns','WHS_ns')),
                             ('boundary_slack.txt',('boundary_WNS_ns','boundary_WHS_ns'))]:
            values = list(map(float,(dest/report).read_text().splitlines()))
            assert len(values) == 2
            assert all(math.isclose(v,row[k],abs_tol=1e-9) for v,k in zip(values,keys))
    return dict(source=source, checks=evidence, original=old, suites=suites, snn=snn,
                math_screen=screen, hardware=ordered, checked_outputs=checked_outputs)

def findings(data):
    original = data['original']['hardware']
    hw = data['hardware']
    results = {}
    for variant, row in hw.items():
        results[variant] = dict(core=row['core'], registered_timing_pass=passes(row),
            delta_vs_original_adaptive=delta(row,original[0]),
            delta_vs_native_fixed4=delta(row,original[1]),
            delta_vs_fixed_hybrid6=delta(row,original[2]),
            delta_vs_lut6=delta(row,original[3]),
            lut_reduction_vs_original_adaptive=1-row['core']['LUT']/original[0]['core']['LUT'],
            ff_reduction_vs_original_adaptive=1-row['core']['FF']/original[0]['core']['FF'])
    usable = [v for v in hw if passes(hw[v])]
    preferred = min(usable,key=lambda v:(hw[v]['core']['LUT'],hw[v]['core']['FF'])) if usable else None
    models = data['original']['model_rows']
    return dict(variants=results, preferred_timing_passing_variant=preferred,
        selection_rule='Lowest LUT count, then FF count, among registered 6 ns timing-passing variants',
        unchanged_model_clocks=models[0]['supplied_window_clocks'],
        native4_model_clocks=models[1]['supplied_window_clocks'],
        hybrid6_lut6_model_clocks=models[2]['supplied_window_clocks'],
        clock_reduction_vs_native4=1-models[0]['supplied_window_clocks']/models[1]['supplied_window_clocks'],
        clock_increase_vs_hybrid6=models[0]['supplied_window_clocks']/models[2]['supplied_window_clocks']-1,
        overall_win_claim=False)

def report(data, result):
    old = data['original']['hardware']
    lines = ['# Adaptive membrane-addition layout optimization trial','',
        'This trial reduces signed reconstruction and operand-layout overhead while retaining the exact signed 11-bit U plus signed 11-bit I operation, signed 12-bit output, original packing decisions, identity-copy priority, and four advancing clocks from acceptance to retirement.','',
        'Both variants replace sign-parity correction with offset-binary fields. For payload width K, flipping each operand sign bit encodes x + 2^(K-1). The guarded DSP field computes U + I + 2^K, so flipping result bit K recovers the exact signed sum. The guard prevents interlane carry. This is an exact representation of the same integer arithmetic, with no shifts or rounding.','',
        'The narrow physical order remains logical lanes 0,1,2,3,4,5 at 8-bit spacing. The wider order becomes 0,1,3,2 at 12-bit spacing; output wires restore logical order. Logical lanes 0 and 3 therefore share field starts between modes. Two aligned starts are the maximum for these contiguous 8-bit and 12-bit formats, since their common starts in a 48-bit word are 0 and 24.','',
        '- V0 retains raw input registers, removes parity metadata, and uses the aligned, biased fields.',
        '- V1 additionally registers already encoded DSP operands and the exact two possible copies at acceptance. This moves format selection onto the input path while keeping the four-stage interface.',
        '- V2 is the original adaptive core instantiated directly in the functional testbench. Its previously completed route remains the hardware reference.','',
        'Offset-binary encoding and static lane permutation are measured together in V0; their individual LUT savings are not isolated. The V1 versus V0 comparison tests stage placement.','',
        'Matched Vivado 2025.2 routes target xc7a100tcsg324-1 at 6 ns, use one thread, and retain the same core boundary and identical 219 fixture FFs (138 launch + 81 capture). Reported core resources exclude those FFs. The fixture is for timing measurement and is not a production handshake adapter.','',
        'Measured new variants:','']
    for v,row in data['hardware'].items():
        f = result['variants'][v]
        d = f['delta_vs_original_adaptive']
        status = 'passes registered setup and hold' if passes(row) else 'fails registered setup or hold'
        lines.append(f"- V{v}: {vector(row)}; change versus original {d['LUT']:+d} LUT / {d['FF']:+d} FF / {d['DSP']:+d} DSP. "
            f"LUT reduction {100*f['lut_reduction_vs_original_adaptive']:.2f}%, FF reduction {100*f['ff_reduction_vs_original_adaptive']:.2f}%. "
            f"WNS {row['WNS_ns']:+.3f} ns / WHS {row['WHS_ns']:+.3f} ns; {status}. "
            f"Core touches {row['core']['occupied_slices']} slices; full fixture occupies {row['full_fixture']['occupied_slices']} slices. "
            f"Separate raw-port audit WNS {row['boundary_WNS_ns']:+.3f} ns / WHS {row['boundary_WHS_ns']:+.3f} ns.")
    lines += ['', 'Original matched reference kernels:','']
    labels = ['Original adaptive','Native four-lane DSP plus identity copies',
              'Native four-lane DSP plus two LUT additions','Six LUT additions']
    for e,row in old.items():
        lines.append(f"- {labels[e]}: {vector(row)}, WNS {row['WNS_ns']:+.3f} ns / WHS {row['WHS_ns']:+.3f} ns; "
            f"{data['original']['model_rows'][e]['supplied_window_clocks']:,} supplied-window service clocks on the saved trace.")
    lines += ['', f"Every layout variant has the original adaptive schedule: {result['unchanged_model_clocks']:,} supplied-window service clocks "
        f"versus {result['native4_model_clocks']:,} native-four clocks ({100*result['clock_reduction_vs_native4']:.2f}% fewer), "
        f"and {result['hybrid6_lut6_model_clocks']:,} fixed hybrid/LUT clocks ({100*result['clock_increase_vs_hybrid6']:.2f}% more). "
        'The saved trace therefore supplies no new schedule gain from these layout changes; their value is any measured hardware reduction at the retained schedule.','']
    preferred = result['preferred_timing_passing_variant']
    if preferred is None:
        lines += ['Neither new variant passes registered timing at 6 ns. Resource reductions alone do not establish an achievable service-rate advantage.','']
    else:
        row = data['hardware'][preferred]
        dh, dl = delta(row,old[2]), delta(row,old[3])
        lines += [f"V{preferred} is preferred by the declared LUT-then-FF selection rule among variants passing registered timing. Compared with hybrid6 it uses "
            f"{dh['LUT']:+d} LUT / {dh['FF']:+d} FF / {dh['DSP']:+d} DSP and still takes 4.67% more service clocks. "
            f"Compared with LUT6 it uses {dl['LUT']:+d} LUT / {dl['FF']:+d} FF / {dl['DSP']:+d} DSP and the same longer schedule. "
            'These are separate resource tradeoffs; no weighted area, energy, or universal implementation advantage is established.','']
    lines += [f"Functional evidence checks {data['checked_outputs']:,} scalar outputs across two input sets, three variants, and both backpressure settings. "
        'All twelve retired files are byte-identical within each cohort and also match the original adaptive output hash; exact sums, request policy, latency, ordering, poisoned tails, stalled output stability and reset cancellation pass. These are repeated comparisons, not exhaustive combinations of six neuron updates.','',
        'The mathematical screen separately covers all 16,384 signed7 and 4,194,304 signed11 scalar pairs, plus 101,014 packed cases, with zero mismatches. It establishes the encoding algebra; timing and RTL behavior are checked separately.','',
        'Saved SNN reconstruction matches every state, spike, spike count and sampled classification across 144 images from three seeds. Leakage with beta=231/256 and threshold/subtractive reset execute in Python, while addition executes in RTL. This modified reference does not establish preservation of original trained-model accuracy or a complete SNN RTL implementation.','',
        'All registered timing results are OOC fixture results. Raw ports have a separate declared 1 ns setup / 0.1 ns minimum budget; negative raw-port hold slack is not production interface closure. No board Fmax follows from target minus WNS. Slice sets overlap and cannot be treated as additive core/fixture areas.','',
        'Memory supply, gather/scatter, neuron-state memory, host performance, threshold/reset hardware, burst arrival latency, power and energy remain unmeasured. These are local kernels; FireFly hardware is not reproduced. The exact runtime policy has no established first-ever claim. A full-range fixed six-lane residue/high-part reconstruction remains an unmeasured alternative, so superiority over fixed packing generally is not established.','',
        'Evidence: '+', '.join([link(R/'layout_hardware.json','new routes'),
            link(R/'layout_snn_checks.json','saved replay'),link(P/'guard_add_layout.sv','layout core'),
            link(O/(STEM+'.manifest.json'),'source/output/checkpoint manifest')])+'.','']
    return '\n'.join(lines)

def assets():
    files = {P/name for name in route.SOURCES}
    files |= {Path(__file__),P/'screen_guard_add_layout.py',R/'layout_arithmetic_screen.json',
              R/'layout_hardware.json',R/'layout_snn_checks.json'}
    for n in route.SUITES:
        files.add(R/n)
        wd = R/n.removesuffix('_checks.json')
        files.add(wd/'stream_stim.txt')
        files |= {wd/f'stream_out{v}.txt' for v in (0,1,2)}
        files |= {wd/f'tool_{j}.log' for j in range(4)}
    if (R/'compile_label_error.log').exists():
        files.add(R/'compile_label_error.log')
    for root,tops in [(R,route.TOPS),(ORIGINAL/'results',baseline.TOPS)]:
        for top in tops:
            files |= {root/(top+'_route')/n for n in baseline.REPORTS}
            files |= {root/(top+'_synth')/n for n in ('util.rpt','hierarchical_util.rpt','design.dcp','provenance.txt')}
            for suffix in ('','_resume'):
                for ending in ('_build.log','_vivado.log','_vivado.jou'):
                    path = root/(top+suffix+ending)
                    if path.exists(): files.add(path)
    files |= {ORIGINAL/n for n in baseline.q.SOURCES}
    files |= {ORIGINAL/'results'/n for n in baseline.q.MAIN_CHECKS+baseline.q.MODEL_INPUTS}
    files |= {ORIGINAL/'results'/n for n in ('guard_add_hardware.json','guard_add_snn_checks.json','guard_add_workload_screen.json')}
    files |= {ORIGINAL/'screen_guard_add_models.py',ORIGINAL/'publish_guard_add_trial.py'}
    for n in baseline.q.MAIN_CHECKS:
        wd = ORIGINAL/'results'/n.removesuffix('_checks.json')
        files.add(wd/'stream_stim.txt')
        files |= {wd/f'stream_out{e}.txt' for e in range(4)}
        files |= {wd/f'tool_{j}.log' for j in range(4)}
    files |= {O/(baseline.STEM+suffix) for suffix in ('.md','.summary.json','.manifest.json')}
    resolved = sorted({p.resolve() for p in files},key=str)
    assert all(p.is_file() for p in resolved), 'Evidence asset missing'
    return resolved

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready',action='store_true')
    args = parser.parse_args()
    if not args.ready:
        print('Publisher prepared; no report written. Use --ready only after both current routes and exact replay finish.')
        return
    data = validate()
    result = findings(data)
    text = report(data,result)
    entries = [dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in assets()]
    assert route.hashes() == data['source']
    assert route.functional('top_guard_add_layout_v0',data['source']) == data['checks']
    assert baseline.q.hashes() == data['original']['source_sha256']
    assert baseline.q.functional(baseline.TOPS[0],data['original']['source_sha256']) == data['original']['functional_check_sha256']
    now = datetime.now(timezone.utc).isoformat()
    summary = dict(created_utc=now,status='Completed exact layout optimization trial',
        findings=result,source_sha256=data['source'],functional_check_sha256=data['checks'],
        hardware=[data['hardware'][v] for v in (0,1)],
        reference_hardware=[data['original']['hardware'][e] for e in range(4)],
        checked_scalar_outputs=data['checked_outputs'],repeated_engine_and_stall_inputs=True,
        mathematical_screen=data['math_screen'],model_images=144,beta_q8=231,
        trained_model_accuracy_preservation_claim=False,
        scope='Exact signed11 membrane-plus-current -> signed12; unchanged adaptive6/4 policy; offset encoding and lane permutation measured together')
    O.mkdir(exist_ok=True)
    rp,sp,mp = (O/(STEM+suffix) for suffix in ('.md','.summary.json','.manifest.json'))
    rp.write_text(text,encoding='utf-8',newline='')
    sp.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='')
    manifest = dict(created_utc=now,hash_algorithm='SHA-256, streamed 1 MiB chunks',
        source_sha256=data['source'],evidence=entries,
        deliverables=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in (rp,sp)],
        exclusions=['Simulator object directories, WDBs and temporary directories.',
                    'No hardware attribution of individual offset/permutation changes.',
                    'No board Fmax, power, host, memory or burst arrival measurement.'])
    mp.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='')
    print('LAYOUT TRIAL PUBLISHED',rp,sp,mp,flush=True)

if __name__ == '__main__':
    main()
