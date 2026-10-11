"""Publish one matched common-layout/selective-correction trial after --ready.

No HDL tools run here. Without --ready no reports or evidence are written.
Publication requires eight exact selective suites, sixteen saved SNN replays,
four current routes, the common fixed reference, policy/bound proofs, and
revalidated immutable original/layout/retimed publications. Large files are
hashed in streamed 1 MiB blocks; simulator objects and waveforms are excluded.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib
import json
import math
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
R = P/'results'
ORIGINAL = P.parent
O = P.parents[2]/'outputs'
STEM = 'membrane_selective_correction_trial'
for directory in (ORIGINAL, ORIGINAL/'layout_trial', ORIGINAL/'baseline_retime_trial', P):
    sys.path.insert(0, str(directory))
import run_guard_add_selective_route as selective
import run_guard_add_common_route as common
import publish_guard_add_retime_trial as retime

KEYS = ('LUT', 'FF', 'DSP')
LABELS = {0: 'Fixed six high corrections, full signed11 current',
          1: 'Shared exact correction, full signed11 current',
          2: 'Fixed six high corrections, statically signed8 current',
          3: 'Shared exact correction, statically signed8 current'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return selective.sha(path)


def stamp(path):
    path = path.resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def link(path, label):
    return f'[{label}](<{path.resolve().as_posix()}>)'


def passes(row):
    return row['WNS_ns'] >= 0 and row['WHS_ns'] >= 0


def vector(row):
    return ' / '.join(f"{row['core'][key]} {key}" for key in KEYS)


def delta(a, b):
    return {key: a['core'][key]-b['core'][key] for key in KEYS}


def delta_text(values):
    return ' / '.join(f'{values[key]:+d} {key}' for key in KEYS)


def evidence_path(name):
    path = R/name
    return path if path.is_file() else P/name


def validate_route_rows(helper, name, source, checks, required, marker):
    rows = read(R/name)
    assert len(rows) == len({row['top'] for row in rows}), ('Duplicate route', name)
    assert required <= {row['top'] for row in rows} <= set(helper.TOPS), name
    validated = {}
    for row in rows:
        top, variant = row['top'], helper.TOPS[row['top']]
        assert row['engine'] == row['variant'] == variant and row['target_ns'] == 6.0, top
        assert row['source_sha256'] == source and row['functional_check_sha256'] == checks, top
        assert row['hd_clk_src'] == 'BUFGCTRL_X0Y0', top
        provenance = hashlib.sha256(json.dumps(dict(
            top=top, engine=variant, variant=variant, target_ns=6.0,
            sources=source, checks=checks, part='xc7a100tcsg324-1',
            hd_clk_src='BUFGCTRL_X0Y0'), sort_keys=True).encode()).hexdigest()
        assert row['provenance_sha256'] == provenance, top
        pre, dest = (R/(top+suffix) for suffix in ('_synth', '_route'))
        assert (pre/'provenance.txt').read_text().strip() == provenance, top
        lines = (dest/'provenance.txt').read_text().splitlines()
        assert lines[0] == provenance, top
        details = dict(line.split(maxsplit=1) for line in lines[1:])
        assert details == {'TOP': top, 'TARGET_NS': '6.0', 'VIVADO': '2025.2',
                           'HD_CLK_SRC': 'BUFGCTRL_X0Y0'}, top
        for report in retime.baseline.REPORTS:
            assert (dest/report).is_file(), (top, report)
        for report in ('util.rpt', 'hierarchical_util.rpt', 'design.dcp', 'provenance.txt'):
            assert (pre/report).is_file(), (top, report)
        paths = {str(path.relative_to(P)): path for folder in (pre, dest)
                 for path in sorted(folder.rglob('*')) if path.is_file()}
        assert set(row['route_artifact_sha256']) == set(paths), (top, 'Artifact coverage')
        assert all(sha(path) == row['route_artifact_sha256'][key]
                   for key, path in paths.items()), (top, 'Routed artifact changed')
        suffix = '_resume' if row['retried_checkpoint'] else ''
        assert f'{marker} {top}' in (R/(top+suffix+'_build.log')).read_text(), top
        accounting = {key: int(value) for key, value in (line.split() for line in
                      (dest/'fixture_accounting.txt').read_text().splitlines())}
        assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81, top
        assert accounting['fixture_FF'] == 219, top
        assert accounting['core_slices_touched'] + accounting['fixture_slices_touched'] \
               - accounting['shared_slices'] == accounting['full_occupied_slices'], top
        full, core = helper.util(dest/'util.rpt'), helper.util(dest/'core_util.rpt', False)
        core['occupied_slices_reported'] = core['occupied_slices']
        core['occupied_slices'] = accounting['core_slices_touched']
        assert row['core'] == core and row['full_fixture'] == full, top
        assert row['slice_accounting'] == accounting, top
        assert full['FF']-core['FF'] == 219 and full['LUT'] == core['LUT'], top
        assert full['DSP'] == core['DSP'] == 1, top
        assert full['occupied_slices'] == accounting['full_occupied_slices'], top
        assert row['fixture_overhead'] == {'LUT': 0, 'FF': 219, 'DSP': 0}, top
        assert all(x['RAMB18'] == x['RAMB36'] == 0 for x in (core, full)), top
        for report, keys in [('slack.txt', ('WNS_ns', 'WHS_ns')),
                             ('boundary_slack.txt', ('boundary_WNS_ns', 'boundary_WHS_ns'))]:
            values = list(map(float, (dest/report).read_text().splitlines()))
            assert len(values) == 2 and all(math.isfinite(value) for value in values), top
            assert all(math.isclose(value, row[key], abs_tol=1e-9, rel_tol=0)
                       for value, key in zip(values, keys)), (top, report)
        if helper is not common:
            assert row['current_contract'] == ('signed8' if variant >= 2 else 'signed11'), top
            assert row['shared_correction'] == (variant in (1, 3)), top
        validated[variant] = row
    return validated


def validate_decode(data):
    """Optional separate cohort; parent gates remain mandatory and unchanged."""
    helper = importlib.import_module('run_guard_add_selective_decode_route')
    source = helper.hashes()
    assert len(source) == 12 and len(helper.FUNCTIONAL_SOURCES) == 9
    assert set(helper.TOPS.values()) == {1, 3}
    assert source['guard_add_selective.sv'] == data['source']['guard_add_selective.sv']
    parent_text = (P/'guard_add_selective.sv').read_text(encoding='utf-8')
    expected_text = parent_text.replace('module guard_add_selective #',
        'module guard_add_selective_decode #').replace("(fast_copy?hu5:5'd0)", 'hu5')
    assert (P/'guard_add_selective_decode.sv').read_text(encoding='utf-8') == expected_text, \
        'Decode source must differ only by module rename and the declared provisional-high mux expression'
    checks = helper.functional(next(iter(helper.TOPS)), source)
    functional_source = {name: source[name] for name in helper.FUNCTIONAL_SOURCES}
    parent_functional = {name: data['source'][name] for name in selective.FUNCTIONAL_SOURCES}
    suites = {name: read(R/name) for name in helper.SUITES}
    assert len(suites) == 8
    checked = 0
    for name, suite in suites.items():
        parent_name = name.replace('selective_decode_', 'selective_', 1)
        parent = data['suites'][parent_name]
        assert suite['source_hashes'] == functional_source
        assert suite['parent_source_hashes'] == parent_functional
        assert suite['parent_check_file'] == str((R/parent_name).relative_to(P))
        assert suite['parent_check_sha256'] == sha(R/parent_name)
        assert suite['outputs_byte_identical_to_parent'] is True and suite['parent_rows_identical'] is True
        assert suite['rows'] == parent['rows'], (name, 'Parent physical/numeric rows differ')
        assert suite['stimulus_sha256'] == parent['stimulus_sha256']
        assert suite['profile'] == parent['profile'] and suite['backpressure'] == parent['backpressure']
        parent_tag = parent_name.removesuffix('_checks.json')
        output_pins = {str((R/parent_tag/f'stream_out{variant}.txt').relative_to(P)):
                       next(row for row in parent['rows'] if row['variant'] == variant)['output_sha256']
                       for variant in range(4)}
        assert suite['parent_output_hashes'] == output_pins
        assert all(sha(P/path) == value for path, value in output_pins.items())
        checked += sum(row['neurons'] for row in suite['rows'])
    assert checked == 23158640
    snn = read(R/'selective_decode_snn_checks.json')
    assert snn['source_hashes'] == functional_source and snn['parent_source_hashes'] == parent_functional
    assert snn['parent_snn_check_file'] == str((R/'selective_snn_checks.json').relative_to(P))
    assert snn['parent_snn_check_sha256'] == sha(R/'selective_snn_checks.json')
    assert snn['parent_snn_rows_identical'] is True and snn['rows'] == data['snn']['rows']
    assert snn['parent_output_hashes'] == data['snn']['output_hashes']
    assert len(snn['rows']) == len(snn['output_hashes']) == 16
    for name, value in snn['output_hashes'].items():
        assert value == data['snn']['output_hashes'][name.replace('selective_decode_', 'selective_', 1)]
        assert sha(P/name) == value
    hardware = validate_route_rows(helper, 'selective_decode_hardware.json', source, checks,
                                  set(helper.TOPS), 'GUARD_ADD_SELECTIVE_DECODE_TIMING_ROUTED')
    assert set(hardware) == {1, 3} and helper.hashes() == source
    assert (P/'decode_audit.md').is_file()
    return dict(helper=helper, source=source, checks=checks, suites=suites, snn=snn,
                hardware=hardware, checked_outputs=checked, single_expression_transformation_verified=True)


def validate(with_decode=False):
    source, common_source = selective.hashes(), common.hashes()
    assert len(source) == 11 and len(common_source) == 10
    assert source['guard_add_selective.sv'] == selective.SELECTIVE_CORE_SHA
    assert source['../guard_add.sv'] == common_source['../guard_add.sv'] == selective.REFERENCE_CORE_SHA
    checks = selective.functional(next(iter(selective.TOPS)), source)
    common_checks = common.functional('top_guard_add_common_v0', common_source)
    assert len(checks) == 18, 'Eight selective suites, SNN and nine policy artifacts are required'
    prior = retime.validate()
    prior_pub = retime.publication(retime.STEM, prior['source'], prior['checks'],
                                  prior['hardware'], 'source_sha256')
    assert source['../baseline_retime_trial/guard_add_retime.sv'] == prior['source']['guard_add_retime.sv']
    assert source['guard_add_common.sv'] == common_source['guard_add_common.sv']
    assert {key: prior['hardware'][2]['core'][key] for key in KEYS} == {'LUT': 66, 'FF': 248, 'DSP': 1}
    assert {key: prior['hardware'][3]['core'][key] for key in KEYS} == {'LUT': 79, 'FF': 304, 'DSP': 0}

    policy = read(P/'common_adaptation_policy_results.json')
    assert policy['arithmetic_proof'] == dict(full_signed11_pairs=4194304,
        signed7_fast_path_pairs=16384, signed8_fast_path_pairs=65536,
        current_signed8_pairs=524288, current_signed8_direct_high_copy_pairs=262144, mismatches=0)
    assert policy['packed_stress'] == {'packed_cases': 18432, 'mismatches': 0}
    prior_policy = policy['prior_screen_artifact']
    assert sha(P/prior_policy['path']) == prior_policy['sha256']
    certificate = read(P/'common_i8_current_bounds.json')
    model = policy['models']
    assert model['eligible_scalar_pairs']['signed8_or_highcopy'] == 634896
    assert model['exception_jobs_per_window']['signed8_or_highcopy'] == {
        '0': 109698, '1': 789, '2': 96, '3': 9}
    cache = model['temporal_cache_storage_scenarios']
    assert cache['one_live_image_payload_bits'] == 1794
    assert cache['all_dataset_identities_payload_bits'] == 258336
    math_screen = read(R/'common_math_checks.json')
    assert math_screen['script_sha256'] == sha(P/'screen_common_math.py')
    assert math_screen['core_sha256'] == common_source['guard_add_common.sv']
    assert math_screen['scalar_cases'] == 4194304 and math_screen['packed_cases'] == 100000
    assert math_screen['mismatches'] == 0

    suites = {name: read(R/name) for name in selective.SUITES}
    model_rows = {}
    checked = sum(row['neurons'] for suite in suites.values() for row in suite['rows'])
    assert checked == 23158640
    for variant in range(4):
        profile, local = divmod(variant, 2)
        row = next(x for x in suites[f'selective_models_p{profile}_0_checks.json']['rows']
                   if x['variant'] == local)
        pred = next(x for x in model['predicted_fused_global_freeze_variants']
                    if x['variant'] == variant)
        assert row['clocks'] == pred['predicted_service_clocks']
        assert row['correction_freezes'] == pred['extra_globally_frozen_clocks']
        assert row['correction_steps'] == pred['exceptional_fallback_jobs']
        model_rows[variant] = row
    common_suites = {name: read(R/name) for name in common.SUITES}
    common_checked = sum(row['neurons'] for suite in common_suites.values() for row in suite['rows'])
    assert common_checked == 11579320
    for name, suite in common_suites.items():
        old = prior['original']['suites'][name.replace('common_', 'guard_add_', 1)]
        assert suite['stimulus_sha256'] == old['stimulus_sha256']
        for row in suite['rows']:
            reference = next(x for x in old['rows'] if x['engine'] == (3 if row['variant'] == 3 else 2))
            assert row['output_sha256'] == reference['output_sha256']
            assert row['requests'] == reference['requests'] and row['clocks'] == reference['clocks']
    hardware = validate_route_rows(selective, 'selective_hardware.json', source, checks,
                                  set(selective.TOPS), 'GUARD_ADD_SELECTIVE_TIMING_ROUTED')
    common_hw = validate_route_rows(common, 'common_hardware.json', common_source, common_checks,
                                   {'top_guard_add_common_v0'}, 'GUARD_ADD_COMMON_TIMING_ROUTED')
    assert {key: common_hw[0]['core'][key] for key in KEYS} == {'LUT': 82, 'FF': 262, 'DSP': 1}
    assert selective.hashes() == source and common.hashes() == common_source
    data = dict(source=source, checks=checks, common_source=common_source, common_checks=common_checks,
        prior=prior, prior_publication=prior_pub, suites=suites, model_rows=model_rows,
        common_suites=common_suites, policy=policy, certificate=certificate, math_screen=math_screen,
        snn=read(R/'selective_snn_checks.json'), common_snn=read(R/'common_snn_checks.json'),
        hardware=hardware, common_hardware=common_hw, checked_outputs=checked,
        common_checked_outputs=common_checked)
    if with_decode:
        data['decode'] = validate_decode(data)
    return data


def compare(a, ac, b, bc):
    comparable = passes(a) and passes(b)
    return dict(resource_delta=delta(a, b), service_clock_delta=ac-bc,
        service_clock_change=ac/bc-1, registered_timing_comparable=comparable,
        service_rate_change=bc/ac-1 if comparable else None,
        lut_normalized_service_change=bc*b['core']['LUT']/(ac*a['core']['LUT'])-1 if comparable else None,
        ff_normalized_service_change=bc*b['core']['FF']/(ac*a['core']['FF'])-1 if comparable else None,
        resource_and_service_dominance=comparable and ac <= bc
            and all(a['core'][key] <= b['core'][key] for key in KEYS)
            and (ac < bc or any(a['core'][key] < b['core'][key] for key in KEYS)),
        normalization_scope='Equal saved work at 6 ns per individual core LUT/FF; no weighted area, replication, memory or energy measurement.')


def findings(data):
    out = {}
    old = data['prior']['original']
    for variant in range(4):
        hw, clocks = data['hardware'][variant], data['model_rows'][variant]['clocks']
        comparisons = {}
        if variant in (1, 3):
            fixed = variant-1
            comparisons['matched_fixed_correction'] = compare(hw, clocks, data['hardware'][fixed],
                                                              data['model_rows'][fixed]['clocks'])
        for engine, label in ((1, 'native4'), (2, 'retimed_hybrid6'), (3, 'retimed_lut6')):
            base = old['hardware'][engine] if engine == 1 else data['prior']['hardware'][engine]
            comparisons[label] = compare(hw, clocks, base, old['model_rows'][engine]['supplied_window_clocks'])
        comparisons['fixed_common_v0'] = compare(hw, clocks, data['common_hardware'][0], 110596)
        if 1 in data['common_hardware']:
            comparisons['fixed_common_v1'] = compare(hw, clocks, data['common_hardware'][1], 110596)
        comparisons['prior_adaptive_layout_v1'] = compare(hw, clocks, data['prior']['adaptive'], 115758)
        out[variant] = dict(label=LABELS[variant], core=hw['core'], service_clocks=clocks,
            registered_timing_pass=passes(hw), correction_steps=data['model_rows'][variant]['correction_steps'],
            correction_freezes=data['model_rows'][variant]['correction_freezes'],
            physical_latency_histogram=data['model_rows'][variant]['physical_latency_histogram'],
            comparisons=comparisons)
    counts = data['policy']['models']['eligible_scalar_pairs']
    assert counts['signed8'] == 627273 and counts['signed8_or_highcopy'] == 634896
    assert counts['zero_current'] == 46336
    range_jobs = 635904-counts['signed8']
    range_hist = data['policy']['models']['exception_jobs_per_window']['signed8']
    range_freezes = sum(max(int(k)-1, 0)*n for k, n in range_hist.items())
    assert range_jobs == 8631 and range_freezes == 3672
    nonzero_eligible = counts['signed8_or_highcopy']-counts['zero_current']
    nonzero_updates = 635904-counts['zero_current']
    assert nonzero_eligible == 588560 and nonzero_updates == 589568
    result = dict(variants=out, eligible_fast_path_scalar_pairs=634896, scalar_pairs=635904,
        fast_path_fraction=634896/635904, exceptional_corrector_jobs=1008,
        exceptional_windows=894, model_extra_global_freeze_clocks=114,
        fixed6_service_clocks=110596, shared_service_clocks=110710,
        shared_service_clock_penalty=114/110596,
        shared_clock_reduction_vs_native4=1-110710/159540,
        software_range_only_diagnostic=dict(signed8_only_eligible_pairs=counts['signed8'],
            signed8_only_exception_jobs=range_jobs, union_exception_jobs=1008,
            exceptional_job_reduction=1-1008/range_jobs,
            signed8_only_fused_control_predicted_freezes=range_freezes,
            signed8_only_fused_control_predicted_clocks=110596+range_freezes,
            union_measured_freezes=114, union_measured_clocks=110710,
            scope='Arithmetic/control screen of a range-only certificate; no range-only RTL/controller/hardware baseline was measured.'),
        nonzero_current_updates=nonzero_updates, nonzero_current_eligible_pairs=nonzero_eligible,
        nonzero_current_fast_path_fraction=nonzero_eligible/nonzero_updates,
        classification='Membrane/current/carry-aware selective exact correction for a constant six-field packed DSP addition; lane count does not adapt.',
        resource_differences_are_separate_axes=True, power_or_energy_claim=False,
        first_ever_claim=False, universal_best_fixed_claim=False)
    if 'decode' in data:
        variants = {}
        for variant, hw in sorted(data['decode']['hardware'].items()):
            clocks = data['model_rows'][variant]['clocks']
            comparisons = dict(
                unchanged_parent_variant=compare(hw, clocks, data['hardware'][variant], clocks),
                matched_fixed_correction=compare(hw, clocks, data['hardware'][variant-1], 110596),
                fixed_common_v0=compare(hw, clocks, data['common_hardware'][0], 110596),
                retimed_hybrid6=compare(hw, clocks, data['prior']['hardware'][2], 110596),
                retimed_lut6=compare(hw, clocks, data['prior']['hardware'][3], 110596))
            if 1 in data['common_hardware']:
                comparisons['fixed_common_v1'] = compare(hw, clocks, data['common_hardware'][1], 110596)
            variants[variant] = dict(core=hw['core'], registered_timing_pass=passes(hw),
                service_clocks=clocks, identical_retirement_bytes_and_physical_rows=True,
                comparisons=comparisons)
        result['optional_decode_optimization'] = dict(variants=variants,
            transformation='Replace fast_small ? small_extension : (fast_copy ? hU : 0) with fast_small ? small_extension : hU; retain fast_copy in bad-mask policy.',
            parent_core_and_evidence_unchanged=True, new_policy_claim=False,
            scope='Isolated provisional high-data mux simplification; correction policy and physical service are unchanged.')
    return result


def decode_report(data, result):
    lines = ['## Separately verified provisional-high decode optimization', '',
        'The optional decode cohort changes one provisional-data expression: '
        'fast_small ? small_extension : (fast_copy ? hU : 0) becomes '
        'fast_small ? small_extension : hU. The fast_copy predicate remains in '
        'the bad-lane mask. For an exceptional lane, the provisional high bits '
        'are hidden while output valid is zero and are overwritten by exact '
        'correction before the completed window is visible. Fixed variants use '
        'their unchanged parallel answer. The source and evidence of the four '
        'original selective variants remain intact.', '',
        'All eight decode suites reproduce their parent retirement files byte '
        'for byte, including physical clock columns, and match every parent row. '
        'They add 23,158,640 repeated scalar checks without a new workload or '
        'domain. Sixteen decode SNN replays match the same parent states, spikes, '
        'counts and sampled classifications. The separate read-only invariant '
        'audit is a reasoning artifact; simulation and routing provide the '
        'separate measured evidence.', '',
        'Only shared decode V1/V3 are routed. Fixed decode V0/V2 are functionally '
        'checked; their existing parent fixed routes remain the cost comparators.', '']
    for variant, row in sorted(data['decode']['hardware'].items()):
        item = result['optional_decode_optimization']['variants'][variant]
        change = item['comparisons']['unchanged_parent_variant']['resource_delta']
        lines.append(f"- Decode V{variant}: {vector(row)}, change from original shared V{variant} "
            f"{delta_text(change)}; registered WNS {row['WNS_ns']:+.3f} ns / "
            f"WHS {row['WHS_ns']:+.3f} ns, {'passes' if passes(row) else 'fails'} registered timing. "
            f"Saved physical service remains {item['service_clocks']:,} clocks. "
            f"Raw-port WNS {row['boundary_WNS_ns']:+.3f} ns / WHS {row['boundary_WHS_ns']:+.3f} ns.")
        for key, label in (('matched_fixed_correction', f'matched parent fixed V{variant-1}'),
                           ('fixed_common_v0', 'fixed common V0'),
                           ('retimed_hybrid6', 'retimed hybrid6'), ('retimed_lut6', 'retimed LUT6')):
            comp = item['comparisons'][key]
            lines.append(f"- Decode V{variant} versus {label}: {delta_text(comp['resource_delta'])}; "
                f"{comp['service_clock_delta']:+,} saved service clocks "
                f"({100*comp['service_clock_change']:+.3f}%).")
    if all(delta(row, data['hardware'][variant])['LUT'] > 0
           for variant, row in data['decode']['hardware'].items()):
        lines += ['', 'The provisional-high simplification increases routed LUT count in both '
            'tested profiles. Registers, DSP count and physical service are unchanged. '
            'The original current8 shared variant remains the lower-LUT choice at this '
            'target; the general-current decode variant still fails the 6 ns registered '
            'constraint. This is a verified implementation experiment without an area '
            'saving or a repair of the general-current timing failure.']
    lines += ['', 'This isolates a hardware implementation change within the same exact adaptive '
        'policy. It supplies no new lane-count adaptation or service-count gain. Any LUT/FF/timing '
        'difference is measured for these routed OOC cores. Hidden provisional values may change '
        'activity, so output equivalence does not establish a power or energy reduction. '
        'The current-I8 specialization and stronger fixed-comparator qualifications above still apply.', '',
        'Decode evidence: ' + ', '.join([link(P/'guard_add_selective_decode.sv', 'isolated source'),
            link(P/'decode_audit.md', 'invariant audit'),
            link(R/'selective_decode_hardware.json', 'two decode routes')]) + '.', '']
    return lines


def report(data, result):
    lines = ['# Membrane-aware selective exact correction trial', '',
        'This is one coordinated common-layout study: first establish a strong fixed exact reference, '
        'then adapt its high-part correction using actual membrane/current values and DSP carry. '
        'All outputs remain exact signed12 U+I; the generic domain is signed11 U and signed11 I, '
        'and the separately certified specialization uses signed11 U and signed8 I.', '',
        '## Mechanism and scope', '',
        'Every DSP request uses six fixed eight-bit fields containing unsigned7 residues. '
        'For U=128hU+rU and I=128hI+rI, the DSP returns s=rU+rI, c=s[7], and low=s[6:0]. '
        'The exact high result is H=hU+hI+c and the output is {H[4:0],low[6:0]}. '
        'Field positions never change and no significant bit is discarded.', '',
        'If both operands fit signed8, H=c-signU-signI fits signed2. If current fits signed8 '
        'and c equals signI, H=hU exactly even for a wider membrane. The union of these '
        'certificates selects a cheap exact recovery; otherwise one shared full high corrector '
        'repairs the exceptional lanes in order. Its first correction is fused into the normal '
        'output stage; k bad lanes add max(k-1,0) globally frozen clocks. Output backpressure, '
        'input retention, reset cancellation and ordered output assembly are part of the RTL.', '',
        'For example, U=-257 and I=-1 have residue carry one, equal to the current sign, '
        'so the exact high part can be copied and the result is -258. U=-256 with the same '
        'current has residue carry zero and needs a high-part decrement to produce -257. '
        'Both membranes are outside signed8; the current/carry certificate distinguishes '
        'whether the update crosses a residue boundary. Monitoring membrane magnitude alone '
        'would send both through the general corrector. Neither path changes a threshold decision '
        'because both produce the same exact integer sum as the reference.', '',
        'The adaptive choice concerns correction work. The DSP still issues a constant six-field '
        'layout for every accepted request. This is membrane-aware adaptive exact correction for '
        'packed DSP addition, rather than a claim that DSP lane count changes.', '',
        'The common fixed V0 reference precomputes five-bit hU+hI at acceptance and applies '
        'the DSP residue carry later. V1 retains both four-bit highs until the output merge. '
        'Selective V0/V1 compare fixed versus shared full-current correction. Selective V2/V3 '
        'compare fixed versus shared correction with a declared static signed8-current contract.', '',
        '## Measured hardware and service', '',
        'Routes use Vivado 2025.2, xc7a100tcsg324-1, one thread and a 6 ns target with the same '
        'registered OOC fixture. Core counts exclude 219 fixture FFs (138 launch and 81 capture). '
        'Core/fixture slice sets overlap; their occupied slices are not additive.', '']
    for variant, row in sorted(data['common_hardware'].items()):
        lines.append(f"- Common fixed V{variant}: {vector(row)}, registered WNS {row['WNS_ns']:+.3f} ns / "
            f"WHS {row['WHS_ns']:+.3f} ns; {'passes' if passes(row) else 'fails'} registered timing. "
            f"Core touches {row['core']['occupied_slices']} slices; 110,596 saved service clocks.")
    if 1 not in data['common_hardware']:
        lines += ['', 'Common fixed V1 has no completed route in this publication; its RTL exactness is checked.']
    for variant, row in sorted(data['hardware'].items()):
        measured = data['model_rows'][variant]
        lines.append(f"- Selective V{variant}, {LABELS[variant]}: {vector(row)}, "
            f"registered WNS {row['WNS_ns']:+.3f} ns / WHS {row['WHS_ns']:+.3f} ns; "
            f"{'passes' if passes(row) else 'fails'} registered timing. "
            f"Core touches {row['core']['occupied_slices']} slices; "
            f"{measured['clocks']:,} saved service clocks, {measured['correction_steps']:,} shared-corrector steps "
            f"and {measured['correction_freezes']:,} internal freeze clocks. "
            f"Separate raw-port WNS {row['boundary_WNS_ns']:+.3f} ns / WHS {row['boundary_WHS_ns']:+.3f} ns.")
    lines += ['', 'The saved model stream offers 110,592 windows covering 635,904 scalar pairs. '
        'The union certificate handles 634,896 pairs (99.84%); 1,008 pairs require shared correction '
        'in 894 windows. Only 96 windows contain two exceptions and nine contain three, so the '
        'fused controller adds 114 clocks. This gives 0.103% more service clocks than always-six '
        'fixed correction/hybrid/LUT kernels, and 30.61% fewer than native4 with its ordered identity copies. '
        'These are physical RTL service clocks with continuously offered inputs and ready output, '
        'not arrival-burst latency or full-neuron-update latency.', '',
        'The carry certificate materially strengthens a membrane range check. A software '
        'signed8 range-only screen leaves 8,631 exceptional pairs; the union leaves 1,008 '
        '(88.32% fewer exceptional jobs). For the same fused control model, range-only would '
        'predict 3,672 freezes and 114,268 clocks, whereas the implemented union measures '
        '114 freezes and 110,710 clocks. The range-only case is an arithmetic/controller '
        'diagnostic, not a measured hardware baseline. The extension is exact because it '
        'recognizes when the high part of a wide actual membrane is unchanged by the residue carry/current sign.', '',
        'All 46,336 zero-current pairs satisfy exact high copy, but the fast path also handles '
        '588,560 of 589,568 nonzero-current updates (99.829%). The same 1,008 exceptions '
        'remain after excluding identity updates, so the high recovery result is broader '
        'than zero-current skipping.', '',
        'The shared saved-stream physical-latency histograms are:', '']
    for variant in (1, 3):
        hist = data['model_rows'][variant]['physical_latency_histogram']
        lines.append(f"- V{variant}: " + ', '.join(f'{count:,} requests at {latency} clocks'
            for latency, count in hist.items()) + '.')
    lines += ['', 'A request can wait for preceding windows to finish correction; its latency is '
        'not determined only by its own bad-lane count. Stress tests include full-range negative '
        'and positive sums, poisoned unavailable tails, range/carry transitions, reset interruption '
        'and output stalls. Observed no-backpressure stress statistics are:', '']
    for profile in (0, 1):
        row = next(x for x in data['suites'][f'selective_main_p{profile}_0_checks.json']['rows'] if x['variant'] == 1)
        fixed = next(x for x in data['suites'][f'selective_main_p{profile}_0_checks.json']['rows'] if x['variant'] == 0)
        lines.append(f"- Profile {profile}: {row['correction_steps']:,} correction steps, "
            f"{row['correction_freezes']:,} correction freezes; maximum internal freeze run "
            f"{row['max_internal_correction_freeze_run']} clocks, physical request latency "
            f"{row['physical_latency_min']}–{row['physical_latency_max']} clocks and "
            f"{row['clocks']:,} shared versus {fixed['clocks']:,} fixed service clocks "
            f"({100*(row['clocks']/fixed['clocks']-1):+.3f}%). Source gaps are present in these stress streams.")
    lines += ['', 'Independent arithmetic/control models also cover sustained six-exception windows '
        'in both domains: each adds five freeze clocks. A 64-window all-bad burst predicts 388 clocks '
        'in that control model; this particular burst figure is not an RTL or arrival-queue measurement. '
        'Wide membranes with zero current use exact high copy and need no exceptional correction. '
        'The much higher stress penalties than the saved model penalty expose the workload dependence: '
        'sharing pays latency when exceptional lanes are frequent.', '',
        '## Strong fixed comparisons and interpretation', '',
        'Immutable local references remain: native4 at 25 LUT/240 FF/1 DSP and 159,540 saved clocks; '
        'retimed hybrid6 at 66 LUT/248 FF/1 DSP and 110,596 clocks; retimed LUT6 at 79 LUT/304 FF/0 DSP '
        'and 110,596 clocks. The prior adaptive layout is 130 LUT/247 FF/1 DSP and 115,758 clocks. '
        'These are matched arithmetic kernels, not reproduced FireFly accelerators.', '']
    for variant in (1, 3):
        item = result['variants'][variant]
        for name, label in [('matched_fixed_correction', f'matched fixed V{variant-1}'),
                            ('fixed_common_v0', 'fixed common V0'),
                            ('retimed_hybrid6', 'retimed hybrid6'), ('retimed_lut6', 'retimed LUT6')]:
            comparison = item['comparisons'][name]
            lines.append(f"- Shared V{variant} versus {label}: "
                f"{delta_text(comparison['resource_delta'])}; "
                f"{comparison['service_clock_delta']:+,} saved service clocks "
                f"({100*comparison['service_clock_change']:+.3f}%).")
    primary = data['hardware'][3]
    primary_label = 'original shared V3'
    primary_delta = delta(primary, data['hardware'][2])
    lines += ['', f"For the certified current8 workload, {primary_label} versus matched fixed V2 "
        f"costs {delta_text(primary_delta)} and 114 extra saved service clocks. "
        'The corrector units being shared are small: current8 high recovery is an exact '
        'increment, decrement or copy. The controller additionally needs range predicates, '
        'priority/operand selection, retained operands and partial-output patching. Its mapped '
        'cost must be compared with the mapped fixed recovery, rather than counting abstract '
        'adder units removed. The fast-path certificate and its bounded exception cost are '
        'established; a practical benefit from that hardware tradeoff is a separate question.']
    lines += ['', 'The resource differences above decide whether sharing supplies a useful bounded '
        'tradeoff. LUTs, FFs, DSPs, timing and service are separate axes; no weighted total area '
        'or replicated throughput is measured. Fixed6 already consumes every supplied window in '
        'one issue, so adaptive sharing trades any measured arithmetic/resource saving for exception '
        'latency. A stronger adaptive capability does not by itself establish a hardware benefit.', '',
        'The signed8-current specialization is essential: independently summed negative and positive '
        'weights certify all binary-spike currents in [-100,70], for these saved matrices. '
        'Thus H=hU+c-signI can be statically implemented without an I8 detector. V2 is the matched '
        'static correction baseline; V3 must be judged against it. The general retimed hybrid/LUT '
        'kernels additionally support full I11, so their resource comparison with I8-only V2/V3 '
        'has this explicit contract difference. Independently specializing hybrid/LUT hardware to '
        'I8 could strengthen them further and remains unmeasured. No global best-fixed claim follows.', '',
        '99.84% fast-path membership means that most valid outputs do not require an exceptional '
        'corrector step. It does not mean 99.84% less circuit activity, power or energy: combinational '
        'shared-adder inputs and selection logic can still toggle when no correction step retires. '
        'Controller/mux/retained-register overhead is included in the routed core; switching power is not measured.', '',
        '## Exactness and evidence boundaries', '',
        f"Eight selective suites check {data['checked_outputs']:,} repeated scalar outputs across "
        'two domains, stress/model sets, four local variants and both backpressure settings. '
        'Four common fixed suites additionally check 11,579,320 repeated outputs. '
        'The selective arithmetic sequences match the direct retimed hybrid/LUT references in '
        'numeric order, while clock columns differ for shared correction. Fixed output files are '
        'byte-identical within each suite. This is repeated checking, not exhaustive six-neuron vectors.', '',
        'The independent common arithmetic screen covers 4,194,304 scalar pairs and 100,000 packed cases. '
        'The policy screen covers the same full scalar domain and 18,432 packed/tail cases, including '
        '524,288 signed11-U/signed8-I pairs. All report zero mismatches. Profile0 stress retains '
        'the original U11/I11 data. Profile1 maps stress currents by signed8 modular projection '
        'and explicitly changes the declared test domain; it is not lossless requantization of '
        'the original full-current stress operation. Saved model operands are identical in both profiles.', '',
        'Sixteen selective saved-output replays and eight common-output replays match every reference '
        'state, spike, spike count and sampled classification for the same 144 images across three seeds. '
        'Leakage at beta 231/256 and threshold/subtractive reset execute in Python; exact U+I executes '
        'in RTL. Integer-equivalent sums preserve that declared threshold behavior. The leakage was '
        'changed from original training, so this is equivalence to the saved integer reference, '
        'not preservation of original trained-model accuracy or a complete RTL SNN.', '',
        'The considered temporal cache stores 13 payload bits per live neuron: 1,794 bits for one '
        '138-neuron image before valid/ports, rather than the sum across all offline image identities. '
        'It was screened without RTL and is not part of this implementation. Signed13–15 widening '
        'and alternative leakage ranges are outside this measured trial; no padded saved data are '
        'used to manufacture a wider-baseline advantage.', '',
        'Registered timing is OOC fixture timing. Raw ports have a separate 1 ns setup/0.1 ns minimum '
        'budget; a negative raw-port hold result is not production interface closure. No board Fmax '
        'is inferred from target minus WNS. Memory supply, dependent-neuron scheduling, host work, '
        'full threshold/reset RTL, arrival-burst latency, power and energy remain unmeasured. '
        'This trial establishes no first-ever claim.', '',
        'Evidence: ' + ', '.join([link(P/'guard_add_selective.sv', 'selective RTL'),
            link(R/'selective_hardware.json', 'four routes'),
            link(P/'common_adaptation_policy_results.json', 'policy/control proofs'),
            link(P/'common_i8_current_bounds.json', 'known-weight current certificate'),
            link(O/(STEM+'.manifest.json'), 'complete streamed manifest')]) + '.', '']
    if 'decode' in data:
        index = lines.index('## Exactness and evidence boundaries')
        lines[index:index] = decode_report(data, result)
    return '\n'.join(lines)


def assets(data):
    files = {Path(__file__), P/'CONTRACT.md', P/'SELECTIVE_CONTRACT.md',
             P/'hardware_notes.md', P/'selective_notes.md', P/'adaptation_notes.md',
             P/'screen_common_math.py', R/'common_math_checks.json',
             P/'common_adaptation_policy_results_pre_fused.json',
             R/'common_hardware.json', R/'selective_hardware.json'}
    for helper, source, checks in ((selective, data['source'], data['checks']),
                                   (common, data['common_source'], data['common_checks'])):
        files |= {P/name for name in source}
        files |= {evidence_path(name) for name in checks}
        for name in helper.SUITES:
            wd = R/name.removesuffix('_checks.json')
            files.add(wd/'stream_stim.txt')
            files |= {wd/f'stream_out{variant}.txt' for variant in range(4)}
            files |= {wd/f'tool_{index}.log' for index in range(4)}
    rows = list(data['hardware'].values()) + list(data['common_hardware'].values())
    if 'decode' in data:
        decode = data['decode']
        files.add(P/'decode_audit.md')
        files.add(P/'decode_hardware_notes.md')
        files.add(P/'prepare_selective_decode_helpers.py')
        files.add(R/'selective_decode_hardware.json')
        files |= {P/name for name in decode['source']}
        files |= {evidence_path(name) for name in decode['checks']}
        for name in decode['helper'].SUITES:
            wd = R/name.removesuffix('_checks.json')
            files.add(wd/'stream_stim.txt')
            files |= {wd/f'stream_out{variant}.txt' for variant in range(4)}
            files |= {wd/f'tool_{index}.log' for index in range(4)}
        rows += list(decode['hardware'].values())
    for row in rows:
        files |= {P/name for name in row['route_artifact_sha256']}
        for suffix in ('', '_resume'):
            for ending in ('_build.log', '_vivado.log', '_vivado.jou'):
                path = R/(row['top']+suffix+ending)
                if path.is_file():
                    files.add(path)
    for publication in (data['prior_publication'], data['prior']['original_publication'],
                        data['prior']['layout_publication']):
        files |= set(publication['paths'])
        files |= {Path(entry['path']) for entry in publication['evidence']}
    resolved = sorted({path.resolve() for path in files}, key=str)
    assert all(path.is_file() for path in resolved), 'Publication asset missing'
    return resolved


def recheck(data, entries):
    assert selective.hashes() == data['source'] and common.hashes() == data['common_source']
    assert selective.functional(next(iter(selective.TOPS)), data['source']) == data['checks']
    assert common.functional('top_guard_add_common_v0', data['common_source']) == data['common_checks']
    for name, pins in (('selective_hardware.json', data['hardware']), ('common_hardware.json', data['common_hardware'])):
        assert {row['variant']: row for row in read(R/name)} == pins, ('Route summary changed', name)
    if 'decode' in data:
        decode = data['decode']
        assert decode['helper'].hashes() == decode['source']
        assert decode['helper'].functional(next(iter(decode['helper'].TOPS)), decode['source']) == decode['checks']
        assert {row['variant']: row for row in read(R/'selective_decode_hardware.json')} == decode['hardware']
    retime.verify_entries(entries)
    for publication in (data['prior_publication'], data['prior']['original_publication'],
                        data['prior']['layout_publication']):
        retime.verify_entries(publication['pins'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready', action='store_true')
    parser.add_argument('--with-decode', action='store_true',
                        help='Additionally require and integrate the separately verified decode cohort and its two routes.')
    args = parser.parse_args()
    if not args.ready:
        print('Publisher prepared; no files written. Use --ready after eight full suites, SNN replay and four routes finish.')
        return
    data = validate(with_decode=args.with_decode)
    result = findings(data)
    report_text = report(data, result)
    entries = [stamp(path) for path in assets(data)]
    recheck(data, entries)
    now = datetime.now(timezone.utc).isoformat()
    summary = dict(created_utc=now, status='Completed common-layout/selective exact correction trial',
        findings=result, source_sha256=data['source'], functional_check_sha256=data['checks'],
        common_source_sha256=data['common_source'], common_functional_check_sha256=data['common_checks'],
        hardware=[data['hardware'][variant] for variant in range(4)],
        common_hardware=[data['common_hardware'][variant] for variant in sorted(data['common_hardware'])],
        retimed_reference_hardware=[data['prior']['hardware'][engine] for engine in (2, 3)],
        original_reference_hardware=[data['prior']['original']['hardware'][engine] for engine in range(4)],
        prior_adaptive_layout_hardware=data['prior']['adaptive'],
        model_measured_rows=data['model_rows'], selective_suites=data['suites'],
        selective_checked_scalar_outputs=data['checked_outputs'],
        common_checked_scalar_outputs=data['common_checked_outputs'],
        input_domains={0: 'signed11 U/signed11 I -> signed12', 1: 'signed11 U/sign-extended signed8 I -> signed12'},
        stress_profile1_transformation='signed8 modular current projection; original U and source gaps retained',
        mathematical_screen=data['math_screen'], policy_proof=data['policy'],
        known_weight_current_certificate=data['certificate'], model_images=144, model_seeds=3,
        saved_selective_replay_outputs=16, common_replay_outputs=8,
        beta_q8=231, trained_model_accuracy_preservation_claim=False,
        old_publication_sha256={entry['path']: entry['sha256']
            for publication in (data['prior_publication'], data['prior']['original_publication'],
                                data['prior']['layout_publication']) for entry in publication['pins']},
        scope='Exact constant-six-field packed DSP addition with selective high-part correction; local 6 ns OOC cores, RTL service clocks and saved Python neuron reconstruction')
    summary['decode_included'] = 'decode' in data
    if 'decode' in data:
        decode = data['decode']
        summary['optional_decode_cohort'] = dict(source_sha256=decode['source'],
            functional_check_sha256=decode['checks'], hardware=[decode['hardware'][v] for v in (1, 3)],
            suites=decode['suites'], checked_scalar_outputs=decode['checked_outputs'],
            saved_replay_outputs=16, rows_and_output_bytes_identical_to_parent=True,
            single_expression_transformation_verified=decode['single_expression_transformation_verified'],
            parent_source_sha256=data['source'], parent_functional_check_sha256=data['checks'])
    O.mkdir(exist_ok=True)
    paths = [O/(STEM+suffix) for suffix in ('.md', '.summary.json', '.manifest.json')]
    paths[0].write_text(report_text, encoding='utf-8', newline='')
    paths[1].write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8', newline='')
    manifest = dict(created_utc=now, hash_algorithm='SHA-256, streamed 1 MiB chunks',
        source_sha256=data['source'], common_source_sha256=data['common_source'],
        evidence=entries, deliverables=[stamp(path) for path in paths[:2]],
        scope='Selective/common sources, two-domain transformed stimuli, checks, outputs, logs, current/bound proofs, routed DCPs/reports and all prior publication evidence; unique paths without copied payloads',
        exclusions=['Simulator object directories, WDBs, waveforms and temporary runtime directories.',
                    'No adaptive DSP lane-count, first-ever or globally best fixed implementation claim.',
                    'No power/energy, replicated placement, memory, host, board Fmax or arrival-burst latency measurement.',
                    'No complete SNN RTL or preservation of original trained-model accuracy.'])
    if 'decode' in data:
        manifest['optional_decode_source_sha256'] = data['decode']['source']
        manifest['scope'] += '; optional isolated decode sources/checks/outputs, invariant audit and two routed DCP/report sets'
    paths[2].write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='')
    print('SELECTIVE CORRECTION TRIAL PUBLISHED', *paths, flush=True)


if __name__ == '__main__':
    main()
