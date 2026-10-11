"""Write a lightweight, validated checkpoint; never simulate or route hardware."""
from pathlib import Path
from datetime import datetime, timezone
import ctypes
import hashlib
import json
import re

P = Path(__file__).resolve().parent
R = P / 'results'
O = P.parents[1] / 'outputs'
STEM = 'pipelined_adaptive_leakage_checkpoint'
FAMILIES = {
    'original': ('stream_pipeline', ['stream_pipeline_leak.sv', 'tb_stream_pipeline_leak.sv'], set(range(7))),
    'strong': ('stream_pipeline_strong', ['stream_pipeline_strong_leak.sv', 'tb_stream_pipeline_strong_leak.sv', 'check_stream_pipeline.py'], {3, 5}),
    'shared': ('stream_pipeline_shared', ['stream_pipeline_shared_leak.sv', 'tb_stream_pipeline_shared_leak.sv', 'check_stream_pipeline.py'], set(range(7))),
    'encoded': ('stream_pipeline_encoded', ['stream_pipeline_encoded_leak.sv', 'tb_stream_pipeline_encoded_leak.sv', 'check_stream_pipeline.py', 'check_stream_pipeline_encoded.py'], set(range(7))),
    'whole': ('stream_pipeline_whole', ['stream_pipeline_whole_leak.sv', 'tb_stream_pipeline_whole_leak.sv', 'check_stream_pipeline.py', 'check_stream_pipeline_whole.py'], set(range(7))),
}
BUILD = ['stream_pipeline_leak.sv', 'stream_pipeline_timing.sv',
         'stream_pipeline_strong_leak.sv', 'stream_pipeline_strong_timing.sv',
         'route_stream_pipeline.tcl', 'run_stream_pipeline_route.py']
PARTS = ['main_25_0', 'main_-1_1', 'models', 'stress']


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(path.read_text())


def link(label, path):
    return f'[{label}](<{path.resolve().as_posix()}>)'


def free_gib():
    class Mem(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    ('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong),
                    ('rest', ctypes.c_ulonglong * 5)]
    value = Mem()
    value.length = ctypes.sizeof(value)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value))
    return value.free / 2**30


def collect():
    checks, pins, stimulus_pins = {}, {}, {}
    for family, (stem, sources, engines) in FAMILIES.items():
        current_sources = {name: sha(P / name) for name in sources}
        pins.update(current_sources)
        for cw in (False, True):
            prefix = stem + ('_centered' if cw else '')
            for part in PARTS:
                key = prefix + '_' + part
                file = R / (key + '_checks.json')
                data = read(file)
                assert data['source_hashes'] == current_sources, ('Source pin mismatch', key)
                assert data['centered_wide'] == cw, key
                assert data['acceptance_to_handshake_advances'] == 4, key
                assert data['constant_delta'] == (-1 if part == 'main_-1_1' else 25), key
                assert data['backpressure'] == (part == 'main_-1_1'), key
                assert len(data['rows']) == len(engines)
                assert {row['engine'] for row in data['rows']} == engines, key
                stimulus = R / key / 'stream_stim.txt'
                stimulus_hash = sha(stimulus)
                if 'stimulus_sha256' in data:
                    assert data['stimulus_sha256'] == stimulus_hash, key
                if family != 'original':
                    assert data['matched_original_stimulus'] is True, key
                original_key = 'stream_pipeline' + ('_centered' if cw else '') + '_' + part
                original_hash = sha(R / original_key / 'stream_stim.txt')
                assert stimulus_hash == original_hash, ('Stimulus differs from original', key)
                # CW changes the arithmetic representation, not the input trace.
                assert original_hash == sha(R / ('stream_pipeline_' + part) / 'stream_stim.txt'), key
                stimulus_pins[str(stimulus.relative_to(P))] = stimulus_hash
                for row in data['rows']:
                    assert row['neurons'] == data['real_neurons'] > 0, key
                    assert row['requests'] > 0 and row['mismatches'] == 0, key
                    for field in ('state_mismatches', 'spike_mismatches'):
                        if field in row:
                            assert row[field] == 0, (key, field)
                    if part == 'models':
                        assert row['state_mismatches'] == row['spike_mismatches'] == 0, key
                        assert all(m['spike_counts_matched'] for m in row['model_rows']), key
                    if part in ('models', 'stress'):
                        assert row['clocks'] == row['requests'] + 4, key
                    if part == 'main_-1_1':
                        assert row['input_stall_checks'] > 0 and row['output_stall_checks'] > 0, key
                    assert (R / key / f"stream_out{row['engine']}.txt").is_file(), key
                checks[key] = dict(family=family, centered_wide=cw,
                                   json_path=str(file), json_sha256=sha(file),
                                   source_hashes=current_sources,
                                   stimulus_path=str(stimulus), stimulus_sha256=stimulus_hash,
                                   retired_output_paths={str(row['engine']): str(R / key / f"stream_out{row['engine']}.txt")
                                                         for row in data['rows']},
                                   rows=data['rows'])
    runs = sum(len(check['rows']) for check in checks.values())
    assert len(checks) == 40 and runs == 240

    ledger_path = R / 'adaptive_delta_model_input.json'
    ledger = read(ledger_path)
    images = sum(m['sampled_images'] for m in ledger['metadata'])
    neurons = sum(item['neurons'] for item in ledger['ledger'])
    assert images == 144 and neurons == 635904
    pins[str(ledger_path.relative_to(P))] = sha(ledger_path)
    for key, check in checks.items():
        if not key.endswith('_models'):
            continue
        for row in check['rows']:
            assert row['neurons'] == neurons
            assert sum(m['images'] for m in row['model_rows']) == images
            assert len(row['model_rows']) == len(ledger['metadata'])
            for model, reference in zip(row['model_rows'], ledger['metadata']):
                assert model['seed'] == reference['seed']
                assert model['images'] == reference['sampled_images']
                assert model['accuracy'] == reference['sampled_reference_accuracy']
            if check['family'] in ('encoded', 'whole'):
                original_key = ('stream_pipeline_centered' if check['centered_wide'] else 'stream_pipeline') + '_models'
                original = next(x for x in checks[original_key]['rows'] if x['engine'] == row['engine'])
                assert row['requests'] == original['requests'] and row['clocks'] == original['clocks']

    hardware_path = R / 'stream_pipeline_hardware.json'
    hardware = read(hardware_path)
    required = {f'top_stream_pipeline_{e}_{c}' for e in
                ('adaptive', 'adaptive6', 'fixed2', 'lut2', 'lut3', 'fixed3', 'hybrid') for c in ('const', 'prog')}
    required |= {f'top_stream_pipeline_{e}_cw_{c}' for e in ('adaptive', 'fixed2', 'hybrid') for c in ('const', 'prog')}
    required |= {f'top_stream_pipeline_{e}_{c}' for e in ('lut3strong', 'hybridstrong') for c in ('const', 'prog')}
    required |= {f'top_stream_pipeline_hybridstrong_cw_{c}' for c in ('const', 'prog')}
    assert len(hardware) == len(required) == 26 and {h['top'] for h in hardware} == required
    build_pins = {name: sha(P / name) for name in BUILD}
    pins.update(build_pins)
    route_evidence = {}
    for row in hardware:
        assert row['target_ns'] == 6.0
        assert row['source_sha256'] == build_pins, row['top']
        match = re.fullmatch(r'top_stream_pipeline_([a-z0-9]+)(_cw)?_(const|prog)', row['top'])
        prefix = 'stream_pipeline_strong' if 'strong' in match[1] else 'stream_pipeline'
        if match[2]:
            prefix += '_centered'
        gates = [prefix + '_main_25_0_checks.json']
        if match[3] == 'prog':
            gates.append(prefix + '_main_-1_1_checks.json')
        assert set(row['functional_check_sha256']) == set(gates), row['top']
        for name, stamp in row['functional_check_sha256'].items():
            assert sha(R / name) == stamp, (row['top'], name)
        assert row['fixture_overhead'] == dict(LUT=0, FF=83, DSP=0)
        assert row['full_fixture']['FF'] == row['core']['FF'] + 83
        route = R / (row['top'] + '_route')
        assert (route / 'provenance.txt').read_text().splitlines()[0] == row['provenance_sha256']
        route_evidence[row['top']] = {
            name: sha(route / name) for name in
            ('design.dcp', 'provenance.txt', 'core_util.rpt', 'util.rpt', 'timing.rpt', 'slack.txt', 'fixture_accounting.txt')}
    pins[str(hardware_path.relative_to(P))] = sha(hardware_path)

    math_path = R / 'stream_pipeline_whole_math_checks.json'
    math = read(math_path)
    for name, stamp in {**math['source_sha256'], **math['script_sha256']}.items():
        assert sha(P / name) == stamp
        pins[name] = stamp
    assert [row['cases'] for row in math['rows']] == [65536, 48672, 7760]
    assert all(row['mismatches'] == 0 for row in math['rows'])
    pins[str(math_path.relative_to(P))] = sha(math_path)
    pins[Path(__file__).name] = sha(Path(__file__))
    whole_rows = {row['engine']: row for row in checks['stream_pipeline_whole_models']['rows']}
    a, pair, triple = (whole_rows[e]['clocks'] for e in (0, 1, 4))
    return dict(created_utc=datetime.now(timezone.utc).isoformat(),
                status='verified checkpoint; final WHOLE routing pending', final_report_complete=False,
                route_wait=dict(required_free_GiB=2.3, observed_free_GiB=free_gib(),
                                coordinated_queue_session=56718, final_routes_pending=17,
                                planned_constant_target_ns=6.0, planned_programmable_target_ns=8.0),
                verification=dict(checksets=40, engine_configuration_runs=runs,
                                  detected_arithmetic_state_spike_mismatches=0,
                                  model_images=images, model_neurons_per_engine=neurons,
                                  inputs_repeated_across_configurations=True,
                                  model_and_stress_schedule='K+4 clocks',
                                  model_accuracies=[dict(seed=m['seed'], images=m['sampled_images'], accuracy=m['sampled_reference_accuracy']) for m in ledger['metadata']]),
                model_schedule=dict(adaptive_clocks=a, pair_clocks=pair, triple_clocks=triple,
                                    fewer_than_pair_fraction=1-a/pair, more_than_triple_fraction=a/triple-1),
                source_and_input_sha256=pins, stimulus_sha256=stimulus_pins,
                checks=checks, original_strong_hardware=hardware,
                original_strong_route_evidence_sha256=route_evidence,
                whole_product_numerical_screen=math,
                final_whole_hardware_claims=None,
                limitations=['Repeated traces are not 240 independent datasets or unique exhaustive triple cases.',
                             'Model replay uses beta231 on 144 sampled images without retraining.',
                             'Kernel clocks exclude routed state RAM, synaptic integration, threshold/reset and host costs.',
                             'No final WHOLE area, timing, power, Fmax, FireFly comparison or publication claim.'])


def render(summary):
    v, wait, schedule = summary['verification'], summary['route_wait'], summary['model_schedule']
    old = {h['top']: h for h in summary['original_strong_hardware']}
    lut = old['top_stream_pipeline_lut3strong_const']
    prog = old['top_stream_pipeline_adaptive_prog']
    return f"""# Adaptive membrane leakage: verified checkpoint

**Exact replay is complete; final hardware evaluation is pending.** The existing route queue is waiting for at least {wait['required_free_GiB']:.1f} GiB free RAM. This checkpoint observed {wait['observed_free_GiB']:.2f} GiB. The 17 final WHOLE routes are planned at 6 ns for constant coefficients and 8 ns for programmable coefficients. The queue is configured to resume when its RAM gate permits. This is a recoverable progress record, not the final trial report.

- **Verification:** all {v['checksets']} check sets and {v['engine_configuration_runs']} engine/configuration runs passed their source and stimulus hash checks. Arithmetic mismatches are zero; all declared model membrane-state and spike mismatch fields are zero. Unsigned and centered wider encodings, constant/programmed coefficients, tails and stalled handshakes are covered. Inputs are repeated across configurations; these totals are not unique exhaustive triple cases.
- **Model scope:** 144 sampled images across three seeds, with {v['model_neurons_per_engine']:,} membrane values per engine, using the declared beta = 231/256 (Q8 coefficient 231) integer update without retraining. Model and synthetic stress replays take K+4 clocks for K uninterrupted requests. The final adaptive policy uses {schedule['adaptive_clocks']:,} model clocks versus {schedule['pair_clocks']:,} for the pair and {schedule['triple_clocks']:,} for fixed triples: **{100*schedule['fewer_than_pair_fraction']:.1f}% fewer than the pair, but {100*schedule['more_than_triple_fraction']:.2f}% more than the triple.** These are kernel scheduling counts, not measured full-neuron or host latency.
- **Existing hardware:** 26 original/strong routes and their current source, functional-evidence and route-provenance hashes were validated. The stronger local constant LUT triple has {lut['core']['LUT']} LUTs, {lut['core']['FF']} FFs and zero DSPs, and passes registered setup/hold at 6 ns ({lut['WNS_ns']:+.3f}/{lut['WHS_ns']:+.3f} ns slack). Each timing fixture adds 83 FFs outside the core. Full-fixture slices are recorded in the JSON; core and fixture touched slices are nonadditive. The earlier programmable adaptive core fails setup at 6 ns ({prog['WNS_ns']:+.3f} ns), so its schedule cannot establish a closed-clock latency win.

The proposed exact update is `U - floor(delta*U/256)` for signed 11-bit U. Actual membrane values select three narrow lanes when all fit [-32,31], or [-64,63] for delta <= 25; otherwise two wider lanes are used. The narrow arithmetic uses five-bit residuals plus small high-part corrections. The stored membrane remains exact int11.

The final WHOLE CW0 implementation moves the wider high-part correction into DSP C: each independent 16-bit field becomes `32768 + delta*U`, bounded by [1024,64481]. This removes the input-side high-product-to-U subtraction from that implementation. Its numerical screen passed 65,536 scalar combinations, 48,672 adversarial packed pairs and 7,760 stale-word bypass checks; separate RTL replays passed. This is a mathematical and functional improvement whose routed resource/timing benefit remains unmeasured. Shared and encoded intermediates were checked but not routed.

The previously discussed **137-LUT, zero-DSP triple was our local LUT implementation, not FireFly**. The matched pipelined LUT reference above is a different measured implementation. No FireFly RTL comparison, certified Fmax, power/energy benefit, first novelty or publication-strength conclusion follows from this checkpoint. Routed state-memory bandwidth, synaptic accumulation and complete accelerator costs remain outside this trial.

Raw evidence remains in the workspace: {link('checkpoint JSON', O/(STEM+'.summary.json'))}; {link('all existing hardware rows', R/'stream_pipeline_hardware.json')}; {link('final WHOLE model checks', R/'stream_pipeline_whole_models_checks.json')}; {link('WHOLE core', P/'stream_pipeline_whole_leak.sv')}; {link('original core', P/'stream_pipeline_leak.sv')}; {link('strong baseline core', P/'stream_pipeline_strong_leak.sv')}; {link('whole-product numerical checks', R/'stream_pipeline_whole_math_checks.json')}; {link('checkpoint writer', Path(__file__))}. The JSON pins all 40 check files and current stimulus files and links their retired outputs through the check directories. Final WHOLE area/timing metrics will be added only after those routes finish.
"""


def main():
    summary = collect()
    report = render(summary)
    summary['checkpoint_report_sha256'] = hashlib.sha256(report.encode('utf-8')).hexdigest()
    O.mkdir(exist_ok=True)
    for suffix, payload in [('.md', report), ('.summary.json', json.dumps(summary, indent=2) + '\n')]:
        target = O / (STEM + suffix)
        temporary = target.with_suffix(target.suffix + '.tmp')
        temporary.write_text(payload, encoding='utf-8', newline='')
        temporary.replace(target)
    print('CHECKPOINT PASS: 40 check sets, 240 engine runs, 26 original/strong routes; final WHOLE routes pending.', flush=True)
    print(O / (STEM + '.md'), flush=True)
    print(O / (STEM + '.summary.json'), flush=True)


if __name__ == '__main__':
    main()
