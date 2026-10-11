"""Publish the completed matched-pipeline trial; never launch simulations/routes.

Run only after both CW0/CW1 functional replays and all selected routes finish.
The report deliberately uses measured setup/hold slack at the common target,
not an Fmax inferred by subtracting slack. Exact stimuli and retired outputs
are archived, while simulator object trees and waveform databases are omitted.
"""
from pathlib import Path
import argparse
import ctypes
import datetime
import hashlib
import json
import re
import zipfile
import numpy as np

P = Path(__file__).resolve().parent
R = P / 'results'
O = P.parents[1] / 'outputs'
STEM = 'pipelined_adaptive_leakage_trial'
LABELS = {0:'adaptive 7/6-bit packing', 1:'fixed DSP pair', 2:'LUT pair',
          3:'LUT triple', 4:'fixed DSP triple', 5:'fixed DSP/LUT hybrid triple',
          6:'adaptive 6-bit packing'}
TOP_ENGINES = {'adaptive':0, 'fixed2':1, 'lut2':2, 'lut3':3,
               'fixed3':4, 'hybrid':5, 'adaptive6':6, 'lut3strong':3, 'hybridstrong':5}
CORE_NAMES = ['stream_pipeline_leak.sv', 'tb_stream_pipeline_leak.sv']
STRONG_CHECK_NAMES = ['stream_pipeline_strong_leak.sv','tb_stream_pipeline_strong_leak.sv',
                      'check_stream_pipeline.py']
SHARED_CHECK_NAMES = ['stream_pipeline_shared_leak.sv','tb_stream_pipeline_shared_leak.sv',
                      'check_stream_pipeline.py']
ENCODED_CHECK_NAMES = ['stream_pipeline_encoded_leak.sv','tb_stream_pipeline_encoded_leak.sv',
                       'check_stream_pipeline.py','check_stream_pipeline_encoded.py']
WHOLE_CHECK_NAMES = ['stream_pipeline_whole_leak.sv','tb_stream_pipeline_whole_leak.sv',
                     'check_stream_pipeline.py','check_stream_pipeline_whole.py']
BUILD_NAMES = ['stream_pipeline_leak.sv', 'stream_pipeline_timing.sv',
               'stream_pipeline_strong_leak.sv','stream_pipeline_strong_timing.sv',
               'route_stream_pipeline.tcl', 'run_stream_pipeline_route.py']
SHARED_BUILD_NAMES = ['stream_pipeline_shared_leak.sv','stream_pipeline_shared_timing.sv',
                      'route_stream_pipeline_shared.tcl','run_stream_pipeline_shared_route.py']
ENCODED_BUILD_NAMES = ['stream_pipeline_encoded_leak.sv','stream_pipeline_encoded_timing.sv',
                       'route_stream_pipeline_encoded.tcl','run_stream_pipeline_encoded_route.py']
WHOLE_BUILD_NAMES = ['stream_pipeline_whole_leak.sv','stream_pipeline_whole_timing.sv',
                     'route_stream_pipeline_whole.tcl','run_stream_pipeline_whole_route.py']
CHECK_FAMILIES = {
    'original':('stream_pipeline',CORE_NAMES,set(range(7))),
    'strong':('stream_pipeline_strong',STRONG_CHECK_NAMES,{3,5}),
    'shared':('stream_pipeline_shared',SHARED_CHECK_NAMES,set(range(7))),
    'encoded':('stream_pipeline_encoded',ENCODED_CHECK_NAMES,set(range(7))),
    'whole':('stream_pipeline_whole',WHOLE_CHECK_NAMES,set(range(7)))
}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def read(name):
    return json.loads((R/name).read_text())


def mem_free_gib():
    class Mem(ctypes.Structure):
        _fields_ = [('length',ctypes.c_ulong), ('load',ctypes.c_ulong),
                    ('total',ctypes.c_ulonglong), ('free',ctypes.c_ulonglong),
                    ('rest',ctypes.c_ulonglong*5)]
    m = Mem(); m.length = ctypes.sizeof(m)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.free/2**30


def top_fields(top):
    m = re.fullmatch(r'top_stream_pipeline_((?:shared|encoded|whole)_)?([a-z0-9]+)(_cw)?_(const|prog)', top)
    assert m and m[2] in TOP_ENGINES, top
    return TOP_ENGINES[m[2]], bool(m[3]), m[4]


def is_strong(top):
    return 'lut3strong' in top or 'hybridstrong' in top


def family_of(top):
    if top.startswith('top_stream_pipeline_whole_'):
        return 'whole'
    if top.startswith('top_stream_pipeline_encoded_'):
        return 'encoded'
    if top.startswith('top_stream_pipeline_shared_'):
        return 'shared'
    return 'strong' if is_strong(top) else 'original'


def check_row(checks, cw, part, engine, variant=False):
    family = variant if isinstance(variant,str) else ('strong' if variant else 'original')
    prefix = CHECK_FAMILIES[family][0]
    if cw:
        prefix += '_centered'
    return next(row for row in checks[prefix+'_'+part]['rows'] if row['engine'] == engine)


def compare(adaptive, baseline, checks):
    ae, acw, coef = top_fields(adaptive['top'])
    be, bcw, bcoef = top_fields(baseline['top'])
    assert coef == bcoef
    ar = check_row(checks, acw, 'models', ae, family_of(adaptive['top']))
    br = check_row(checks, bcw, 'models', be, family_of(baseline['top']))
    matched = adaptive['target_ns']==baseline['target_ns']
    primary = family_of(adaptive['top'])==family_of(baseline['top'])=='whole'
    return dict(adaptive=adaptive['top'], baseline=baseline['top'], coefficient=coef,
                adaptive_family=family_of(adaptive['top']),baseline_family=family_of(baseline['top']),
                adaptive_clocks=ar['clocks'], baseline_clocks=br['clocks'],
                adaptive_target_ns=adaptive['target_ns'],baseline_target_ns=baseline['target_ns'],
                same_target=matched,primary_final_comparison=primary,
                cycle_saving=1-ar['clocks']/br['clocks'],
                core_resource_difference={k:adaptive['core'][k]-baseline['core'][k]
                                          for k in ['LUT','FF','DSP','RAMB18','RAMB36']},
                full_fixture_slice_difference=adaptive['full_fixture']['occupied_slices']-
                                              baseline['full_fixture']['occupied_slices'],
                adaptive_setup_hold_pass=adaptive['WNS_ns']>=0 and adaptive['WHS_ns']>=0,
                baseline_setup_hold_pass=baseline['WNS_ns']>=0 and baseline['WHS_ns']>=0,
                note=(f"Primary comparison: final whole-product candidates/baselines share a {adaptive['target_ns']:g} ns target and delta25 replay schedule. "
                      if primary else 'Resource/schedule diagnostic across recorded implementations; targets are shown explicitly. ')+
                     ('The targets match. ' if matched else 'Different synthesis targets: no matched-clock hardware or latency claim. ')+
                     'Resources form a vector; no scalar LUT-only winner is selected. Cycle counts do not establish board latency.')


def final_cohort_findings(hardware, checks):
    """Concrete measured conclusions; accepts partial rows without inventing wins.

    A minimum-LUT hybrid is identified explicitly, not called universally best.
    Both constant hybrid vectors remain visible. Dominance uses LUT/FF/DSP and
    sample clocks together, only at a shared target with registered closure.
    """
    tops = {h['top']:h for h in hardware}
    findings = []
    for coef,target in [('const',6.0),('prog',8.0)]:
        stem = 'top_stream_pipeline_whole_'
        hybrid_names = [stem+'hybrid_'+coef]
        if coef=='const': hybrid_names.append(stem+'hybrid_cw_const')
        fixed_name,lut_name = stem+'fixed3_'+coef,stem+'lut3_'+coef
        candidate_names = [stem+'adaptive_'+coef,stem+'adaptive6_'+coef]
        if coef=='const': candidate_names.append(stem+'adaptive_cw_const')
        needed = hybrid_names+[fixed_name,lut_name]+candidate_names
        missing = [name for name in needed if name not in tops]
        if missing:
            findings.append(dict(coefficient=coef,target_ns=target,status='pending',missing_routes=missing))
            continue
        hybrids = [tops[name] for name in hybrid_names]
        minimum_lut_hybrid = min(hybrids,key=lambda h:(h['core']['LUT'],h['core']['FF'],h['top']))
        candidates = []
        for name in candidate_names:
            candidate = tops[name]
            assert candidate['target_ns']==target
            closed = candidate['WNS_ns']>=0 and candidate['WHS_ns']>=0
            baseline_rows = [tops[fixed_name],minimum_lut_hybrid,tops[lut_name]]
            details = []
            for baseline in baseline_rows:
                assert baseline['target_ns']==target
                comparison = compare(candidate,baseline,checks)
                cc,bc = candidate['core'],baseline['core']
                same_dsp = cc['DSP']==bc['DSP']
                resource_keys = ['LUT','FF','DSP','RAMB18','RAMB36']
                baseline_closed = comparison['baseline_setup_hold_pass']
                vector_no_worse = all(bc[k]<=cc[k] for k in resource_keys)
                objective_strict = any(bc[k]<cc[k] for k in resource_keys) or comparison['baseline_clocks']<comparison['adaptive_clocks']
                comparison.update(
                    baseline_core=bc,
                    baseline_kind=('fixed DSP triple' if baseline['top']==fixed_name else
                                   'zero-DSP LUT triple' if baseline['top']==lut_name else 'minimum-LUT measured hybrid'),
                    same_DSP=same_dsp,
                    adaptive_LUT_and_FF_no_greater_at_same_DSP=(same_dsp and cc['LUT']<=bc['LUT'] and cc['FF']<=bc['FF']),
                    adaptive_reduces_at_least_one_fabric_component_at_same_DSP=(same_dsp and (cc['LUT']<bc['LUT'] or cc['FF']<bc['FF'])),
                    baseline_dominates_resource_vector_and_model_clocks=(closed and baseline_closed and vector_no_worse and
                                                                        comparison['baseline_clocks']<=comparison['adaptive_clocks'] and objective_strict))
                details.append(comparison)
            candidates.append(dict(top=name,core=candidate['core'],setup_hold_pass=closed,
                                   WNS_ns=candidate['WNS_ns'],WHS_ns=candidate['WHS_ns'],
                                   clocks=details[0]['adaptive_clocks'],comparisons=details))
        findings.append(dict(coefficient=coef,target_ns=target,status='measured',
                             hybrid_vectors=[dict(top=h['top'],core=h['core'],WNS_ns=h['WNS_ns'],WHS_ns=h['WHS_ns']) for h in hybrids],
                             minimum_LUT_hybrid=minimum_lut_hybrid['top'],
                             minimum_LUT_selection_note='Minimum measured LUT count only; both hybrid vectors/slack are retained, and FF/DSP differences are not erased.',
                             candidates=candidates))
    return findings


def conclusion_lines(findings):
    lines = []
    for cohort in findings:
        label = 'Constant coefficient' if cohort['coefficient']=='const' else 'Programmable coefficient'
        if cohort['status']!='measured':
            lines.append(f"- **{label}:** baseline/candidate routing is incomplete; a benefit conclusion is pending.")
            continue
        vectors = '; '.join(f"{h['top']}: {h['core']['LUT']} LUT/{h['core']['FF']} FF/{h['core']['DSP']} DSP "
                            f"(setup/hold {h['WNS_ns']:+.3f}/{h['WHS_ns']:+.3f} ns)"
                            for h in cohort['hybrid_vectors'])
        lines.append(f"- **{label}, {cohort['target_ns']:g} ns cohort:** hybrid vectors are {vectors}. "
                     f"The minimum-LUT hybrid is {cohort['minimum_LUT_hybrid']}; this selection does not merge the resource dimensions.")
        for candidate in cohort['candidates']:
            core = candidate['core']
            closed = 'passes registered setup/hold' if candidate['setup_hold_pass'] else 'fails registered setup or hold'
            pieces = []
            for comparison in candidate['comparisons']:
                delta = comparison['core_resource_difference']
                clock_change = 100*(comparison['adaptive_clocks']/comparison['baseline_clocks']-1)
                bc = comparison['baseline_core']
                pieces.append(f"versus {comparison['baseline_kind']} {comparison['baseline']}, "
                              f"baseline {bc['LUT']} LUT/{bc['FF']} FF/{bc['DSP']} DSP and {comparison['baseline_clocks']:,} clocks, "
                              f"LUT/FF/DSP differences {delta['LUT']:+d}/{delta['FF']:+d}/{delta['DSP']:+d} "
                              f"and {clock_change:+.2f}% model clocks")
            lines.append(f"- **{candidate['top']}:** {core['LUT']} LUTs, {core['FF']} FFs, {core['DSP']} DSPs, "
                         f"{candidate['clocks']:,} model clocks; {closed} "
                         f"({candidate['WNS_ns']:+.3f}/{candidate['WHS_ns']:+.3f} ns). "+'; '.join(pieces)+'.')
            dominated = [c['baseline'] for c in candidate['comparisons'] if c['baseline_dominates_resource_vector_and_model_clocks']]
            same_dsp_savings = [c['baseline'] for c in candidate['comparisons']
                                if c['same_DSP'] and c['adaptive_reduces_at_least_one_fabric_component_at_same_DSP']]
            if not candidate['setup_hold_pass']:
                interpretation = 'This candidate is not closed at the cohort target; its schedule does not establish a latency benefit.'
            elif dominated:
                interpretation = 'A measured fixed reference is no worse in every reported core resource and model clocks: '+', '.join(dominated)+'.'
            elif same_dsp_savings:
                interpretation = 'A fabric-component reduction at the same DSP count is measured against '+', '.join(same_dsp_savings)+'. The explicit FF/LUT and clock differences above define the tradeoff.'
            else:
                interpretation = 'No LUT or FF reduction at the same DSP count appears against the measured fixed triple/minimum-LUT hybrid.'
            lut = next(c for c in candidate['comparisons'] if c['baseline_kind']=='zero-DSP LUT triple')
            interpretation += (f" The LUT-only triple uses zero DSPs and {lut['baseline_clocks']:,} clocks; "
                               'the adaptive DSP cost remains in this comparison.')
            lines.append('- '+interpretation)
    return lines


def gather():
    all_names = CORE_NAMES+STRONG_CHECK_NAMES+SHARED_CHECK_NAMES+ENCODED_CHECK_NAMES+WHOLE_CHECK_NAMES+BUILD_NAMES+SHARED_BUILD_NAMES+ENCODED_BUILD_NAMES+WHOLE_BUILD_NAMES
    hashes = {n:sha(P/n) for n in all_names if (P/n).exists()}
    checks = {}
    for family,(stem,expected_sources,expected_engines) in CHECK_FAMILIES.items():
        for cw in [False,True]:
            prefix = stem
            if cw: prefix += '_centered'
            for part in ['main_25_0','main_-1_1','models','stress']:
                key = prefix+'_'+part
                data = read(key+'_checks.json')
                assert data['source_hashes'] == {n:hashes[n] for n in expected_sources}, key
                assert data['centered_wide'] == cw and data['acceptance_to_handshake_advances'] == 4, key
                assert {row['engine'] for row in data['rows']} == expected_engines, key
                assert all(row['mismatches']==0 and row['neurons']>0 for row in data['rows']), key
                if family!='original':
                    assert data['matched_original_stimulus'] is True, key
                if part=='models':
                    assert all(row['state_mismatches']==row['spike_mismatches']==0 for row in data['rows']), key
                if part in ['models','stress']:
                    assert all(row['clocks']==row['requests']+4 for row in data['rows']), key
                if family in ['encoded','whole'] and part=='models':
                    original_key = ('stream_pipeline_centered' if cw else 'stream_pipeline')+'_models'
                    original_rows = {row['engine']:row for row in checks[original_key]['rows']}
                    assert all(row['requests']==original_rows[row['engine']]['requests'] and
                               row['clocks']==original_rows[row['engine']]['clocks'] for row in data['rows']), key
                if part=='main_-1_1':
                    assert all(row['input_stall_checks']>0 and row['output_stall_checks']>0 for row in data['rows']), key
                checks[key] = data
    original_hardware = read('stream_pipeline_hardware.json')
    whole_hardware = read('stream_pipeline_whole_hardware.json')
    hardware = original_hardware + whole_hardware
    assert hardware and len({h['top'] for h in hardware})==len(hardware)
    tops = {h['top']:h for h in hardware}
    required = {f'top_stream_pipeline_{engine}_{coef}'
                for engine in ['adaptive','adaptive6','fixed2','lut2','lut3','fixed3','hybrid']
                for coef in ['const','prog']}
    required |= {f'top_stream_pipeline_{engine}_cw_{coef}'
                 for engine in ['adaptive','fixed2','hybrid'] for coef in ['const','prog']}
    required |= {f'top_stream_pipeline_{engine}_{coef}'
                 for engine in ['lut3strong','hybridstrong'] for coef in ['const','prog']}
    required |= {f'top_stream_pipeline_hybridstrong_cw_{coef}' for coef in ['const','prog']}
    required |= {f'top_stream_pipeline_whole_{engine}_const'
                 for engine in ['adaptive','adaptive6','fixed2','lut2','lut3','fixed3','hybrid']}
    required |= {f'top_stream_pipeline_whole_{engine}_cw_const'
                 for engine in ['adaptive','fixed2','hybrid']}
    required |= {f'top_stream_pipeline_whole_{engine}_prog'
                 for engine in ['adaptive','adaptive6','fixed2','lut2','lut3','fixed3','hybrid']}
    assert len(required)==43, ('Expected 26 original/strong and 17 whole-product routes',len(required))
    assert required <= set(tops), ('Required strong baseline routes missing',sorted(required-set(tops)))
    for h in hardware:
        top_fields(h['top'])
        expected_target = 8.0 if family_of(h['top'])=='whole' and top_fields(h['top'])[2]=='prog' else 6.0
        assert h['target_ns']==expected_target, ('Incorrect family clock target',h['top'],h['target_ns'])
        build_names = WHOLE_BUILD_NAMES if family_of(h['top'])=='whole' else BUILD_NAMES
        assert h['source_sha256']=={n:sha(P/n) for n in build_names}, h['top']
        for name, expected in h['functional_check_sha256'].items():
            assert sha(R/name)==expected, (h['top'],name)
        assert h['fixture_overhead']==dict(LUT=0,FF=83,DSP=0), h['top']
        assert h['full_fixture']['FF']==h['core']['FF']+83, h['top']
        assert (R/(h['top']+'_route')/'provenance.txt').read_text().splitlines()[0]==h['provenance_sha256'], h['top']
    assert not any(family_of(h['top']) in ['shared','encoded'] for h in hardware), 'Shared/encoded intermediates are explicitly unrouted'
    ledger = read('adaptive_delta_model_input.json')
    with np.load(R/'adaptive_delta_model_25_1/expected.npz') as data:
        groups = data['groups'].astype(np.int64)
    nonzero = changed = neurons = 0
    for rec in ledger['ledger']:
        u = groups[rec['start']:rec['start']+rec['blocks']].reshape(-1)[:rec['neurons']]
        neurons += len(u); nonzero += int(np.count_nonzero(u))
        changed += int(np.count_nonzero(u-(25*u//256)!=u))
    images = sum(m['sampled_images'] for m in ledger['metadata'])
    assert images==144 and neurons==635904 and changed==299884
    for family,(_,_,engines) in CHECK_FAMILIES.items():
        for cw in [False,True]:
            for e in sorted(engines):
                row = check_row(checks,cw,'models',e,family)
                assert row['neurons']==neurons
                assert sum(m['images'] for m in row['model_rows'])==images
                for metadata,model in zip(ledger['metadata'],row['model_rows']):
                    assert metadata['seed']==model['seed']
                    assert metadata['sampled_reference_accuracy']==model['accuracy']
                    assert model['spike_counts_matched']
    comparisons = []
    for h in hardware:
        e,cw,coef = top_fields(h['top'])
        if e not in [0,6]: continue
        for baseline in hardware:
            be,bcw,bcoef = top_fields(baseline['top'])
            if be in [1,2,3,4,5] and bcoef==coef:
                comparisons.append(compare(h,baseline,checks))
    metrics = dict(routed_fixtures=len(hardware),
                   routed_fixtures_by_family={family:sum(family_of(h['top'])==family for h in hardware)
                                             for family in CHECK_FAMILIES},
                   engine_configuration_runs=sum(len(c['rows']) for c in checks.values()),
                   neuron_output_comparisons=sum(r['neurons'] for c in checks.values() for r in c['rows']),
                   request_output_comparisons=sum(r['requests'] for c in checks.values() for r in c['rows']),
                   detected_output_state_spike_mismatches=0,
                   model_images=images,model_frames=len(ledger['ledger']),model_neurons_per_engine=neurons,
                   nonzero_model_membranes=nonzero,changed_model_membranes=changed,
                   model_accuracies=[dict(seed=m['seed'],images=m['sampled_images'],
                                          accuracy=m['sampled_reference_accuracy']) for m in ledger['metadata']])
    assert len(checks)==40 and metrics['engine_configuration_runs']==240
    audit = read('pipeline_register_cost_audit.json')
    assert sha(P/'audit_pipeline_register_cost.py')==audit['script_sha256']
    for observation in audit['observations']:
        rtl = Path(observation['rtl_path']).resolve()
        assert rtl.is_relative_to(P) and sha(rtl)==observation['rtl_sha256']
        rows = hardware if observation['label']=='new_four_stage' else read('stream_fold_hardware.json')
        row = next(row for row in rows if row['top']==observation['top'])
        assert hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()==observation['route_row_sha256']
        for cp in observation['checkpoints']:
            checkpoint = Path(cp['path']).resolve()
            assert checkpoint.is_relative_to(P) and sha(checkpoint)==cp['checkpoint_sha256']
    whole_math = read('stream_pipeline_whole_math_checks.json')
    for name, stamp in {**whole_math['source_sha256'],**whole_math['script_sha256']}.items():
        assert sha(P/name)==stamp, ('Whole-product numerical screen pin mismatch',name)
        hashes[name] = stamp
    assert [row['cases'] for row in whole_math['rows']]==[65536,48672,7760]
    assert all(row['mismatches']==0 for row in whole_math['rows'])
    activity = read('stream_pipeline_whole_activity.json')
    for name, stamp in activity['source_hashes'].items():
        assert sha(P/name)==stamp, ('Trace accounting pin mismatch',name)
        hashes[name] = stamp
    for part in ['models','stress']:
        assert {row['engine'] for row in activity[part]['rows']}=={0,1,4,5,6}
        for row in activity[part]['rows']:
            for cw in [False,True]:
                measured = check_row(checks,cw,part,row['engine'],'whole')
                assert all(row[k]==measured[k] for k in
                           ['requests','neurons','arithmetic_issues','narrow_requests','bypass_requests'])
            assert row['original_simulation_schedule_matched']
            assert row['dsp_changing_operations']+row['lut_third_changing_operations']==row['all_changing_membranes']
    activity_audit = read('stream_pipeline_whole_activity_audit.json')
    assert sha(P/'audit_stream_pipeline_whole_activity.py')==activity_audit['script_sha256']
    assert sha(P/'stream_pipeline_whole_leak.sv')==activity_audit['source_sha256']
    assert sha(R/'stream_pipeline_whole_activity.json')==activity_audit['reviewed_report_sha256']
    for dataset in activity_audit['audited']:
        gate = Path(dataset['whole_completed_simulation']).resolve()
        assert gate.is_relative_to(R) and sha(gate)==dataset['whole_completed_simulation_sha256']
        assert {row['engine'] for row in dataset['rows']}=={0,1,4,5,6}
        assert all(row['disjoint_neuron_accounting']==activity[dataset['dataset']]['real_neurons'] for row in dataset['rows'])
    optional = {}
    for path in sorted(R.glob('*quotient*')):
        if path.is_file() and path.suffix in ['.json','.txt','.log']:
            optional[path.name] = dict(bytes=path.stat().st_size,sha256=sha(path),
                                      scope='Scalar arithmetic resource screen; its own synthesis results do not establish routed three-lane timing.')
    quotient_screen = None
    if (R/'quotient_screen_summary.json').is_file():
        quotient_screen = read('quotient_screen_summary.json')
        # Pin the exact scalar screen sources, rather than silently attaching
        # current files to a screen performed on an older source revision.
        for name, stamp in quotient_screen['source_sha256'].items():
            assert sha(P/name)==stamp, ('Quotient screen source changed',name)
            hashes[name] = stamp
        for check in quotient_screen.get('checks',[]):
            assert check['source_sha256']==quotient_screen['source_sha256']
            assert check['mismatches']==0 and check['comparisons']>0
        for synth in quotient_screen.get('synthesis',[]):
            assert synth['source_sha256']==quotient_screen['source_sha256']
            assert synth['DSP']==0
    limitations = [
        'Leakage primitive only. Current integration, threshold/reset, state and classification comparisons are reconstructed in Python.',
        'Three raw lookahead values and up to three results per clock require corresponding state-memory bandwidth. No state RAM, bank rotation, pointer update, lookahead cache or three-read/write interface is routed.',
        'Shared delta0..31 per request, signed int11 U. The policy is not validated for arbitrary coefficients, arbitrary widths or other neuron dynamics.',
        'The registered fixture contributes exactly 83 FFs outside the reported core. It samples input/output unconditionally and is not a production handshake wrapper.',
        'Occupied slices are shared between core and fixture. Core touched slices are nonadditive and alone do not establish an area win.',
        'Hierarchy preservation constrains optimization across fixture/core boundaries. All candidates share the same rule.',
        'Vivado OOC original/strong targets are6ns. Final whole-product constant targets are6ns, programmable targets8ns, with HD.CLK_SRC BUFGCTRL_X0Y0. Primary comparisons stay within each coefficient cohort. Cross-target resource/cycle comparisons are labeled diagnostics. No Fmax, board latency, power or energy is certified.',
        'The beta231 reference changes the saved models original leakage. No retraining was performed. Only 144 images, the first48 of each seed, receive this RTL replay.',
        'Programmable hardware comparisons reuse the delta25 model schedule; they are not evaluations of a different programmable-coefficient SNN.',
        'Arithmetic issues count non-bypassed kernel requests for every engine, including LUT-only engines. They do not prove all DSP lanes contain changing useful work.',
        'For delta25 U in[0,10] is unchanged by leakage. An extra identity-aware monitor is an analytic opportunity, not an implemented/routed improvement.',
        'Synthetic burst replay does not establish a natural-model burst latency win or worst-case guarantee.',
        'No FireFly RTL or accelerator measurement was reproduced. LUT3 is our matched scalar-leakage reference, not FireFly.',
        'Novelty remains unproved. Generic DSP packing and correction are established; this trial measures an actual-membrane-driven exact leakage policy.'
    ]
    return dict(source_hashes=hashes,metrics=metrics,checks=checks,hardware=hardware,
                hardware_by_family={family:[h for h in hardware if family_of(h['top'])==family]
                                    for family in CHECK_FAMILIES},
                family_build_source_hashes={
                    'original_and_strong':{n:hashes[n] for n in BUILD_NAMES},
                    'shared_unrouted':{n:hashes[n] for n in SHARED_BUILD_NAMES},
                    'encoded_unrouted':{n:hashes[n] for n in ENCODED_BUILD_NAMES},
                    'whole':{n:hashes[n] for n in WHOLE_BUILD_NAMES}},
                family_status=dict(original='routed',strong='routed',shared='exact checks passed; not routed',
                                   encoded='exact checks passed; not routed',whole='routed'),
                implementation_audit=audit,
                whole_product_numerical_screen=whole_math,
                trace_useful_work_accounting=activity,
                independent_trace_accounting_audit=activity_audit,
                final_cohort_findings=final_cohort_findings(hardware,checks),
                comparisons=comparisons,optional_quotient_screens=optional,
                quotient_screen=quotient_screen,limitations=limitations)


def hardware_line(h):
    core,full,sites = h['core'],h['full_fixture'],h['slice_accounting']
    closed = 'passes setup and hold at this target' if h['WNS_ns']>=0 and h['WHS_ns']>=0 else 'does not pass both setup and hold'
    return (f"- **{h['top']}:** core {core['LUT']} LUTs, {core['FF']} FFs, {core['DSP']} DSPs; "
            f"full fixture {full['LUT']} LUTs/{full['FF']} FFs/{full['DSP']} DSPs, "
            f"{full['occupied_slices']} occupied slices, {full['RAMB18']} RAMB18/{full['RAMB36']} RAMB36. "
            f"At {h['target_ns']:g} ns, registered setup/hold slack {h['WNS_ns']:+.3f}/{h['WHS_ns']:+.3f} ns: {closed}. "
            f"Core/fixture sites touched {sites['core_slices_touched']}/{sites['fixture_slices_touched']}, "
            f"including {sites['shared_slices']} shared slices. Separate port-audit setup/hold "
            f"{h['boundary_WNS_ns']:+.3f}/{h['boundary_WHS_ns']:+.3f} ns.")


def comparison_line(c):
    d = c['core_resource_difference']
    return (f"- **{c['adaptive']} versus {c['baseline']}:** {100*c['cycle_saving']:+.2f}% fewer "
            f"sampled clocks; core LUT/FF/DSP differences {d['LUT']:+d}/{d['FF']:+d}/{d['DSP']:+d}; "
            f"full-fixture occupied-slice difference {c['full_fixture_slice_difference']:+d}. "
            f"Adaptive/baseline targets {c['adaptive_target_ns']:g}/{c['baseline_target_ns']:g} ns, "
            f"setup-and-hold pass {c['adaptive_setup_hold_pass']}/{c['baseline_setup_hold_pass']}. "
            +('Primary same-target comparison.' if c['primary_final_comparison'] else
              'Different-target resource/schedule diagnostic; no matched-clock latency claim.' if not c['same_target'] else
              'Additional same-target reference comparison.'))


def report(summary):
    m,checks,hardware = summary['metrics'],summary['checks'],summary['hardware']
    tops = {h['top']:h for h in hardware}
    adaptive = tops['top_stream_pipeline_whole_adaptive_const']
    ar = check_row(checks,False,'models',0,'whole')
    hr = check_row(checks,False,'models',5,'whole')
    lr = check_row(checks,False,'models',3,'whole')
    old_strong_lut = tops['top_stream_pipeline_lut3strong_const']
    hybrid = [tops['top_stream_pipeline_hybrid_const'],tops['top_stream_pipeline_hybrid_cw_const'],
              tops['top_stream_pipeline_hybridstrong_const'],tops['top_stream_pipeline_hybridstrong_cw_const']]
    hybrid += [tops['top_stream_pipeline_whole_hybrid_const'],tops['top_stream_pipeline_whole_hybrid_cw_const']]
    hybrid_vector = '; '.join(f"{family_of(h['top'])} "
                             f"{'centered' if top_fields(h['top'])[1] else 'unsigned'} "
                             f"{h['core']['LUT']} LUT/{h['core']['FF']} FF/{h['core']['DSP']} DSP" for h in hybrid)
    model_lines = []
    for cw in [False,True]:
        for e in range(7):
            r = check_row(checks,cw,'models',e)
            model_lines.append(f"- **{'Centered' if cw else 'Unsigned'} wide residual, {LABELS[e]}:** "
                               f"{r['requests']:,} requests, {r['clocks']:,} continuous clocks, "
                               f"{r['arithmetic_issues']:,} non-bypassed kernel requests, "
                               f"{r['narrow_requests']:,} narrow-mode requests; zero output/state/spike mismatches.")
    for cw in [False,True]:
        for e in [3,5]:
            r = check_row(checks,cw,'models',e,True)
            model_lines.append(f"- **Screened stronger baseline, {'centered' if cw else 'unsigned'} wide residual, {LABELS[e]}:** "
                               f"{r['requests']:,} requests, {r['clocks']:,} continuous clocks, "
                               f"{r['arithmetic_issues']:,} non-bypassed kernel requests; zero output/state/spike mismatches.")
    for cw in [False,True]:
        for e in range(7):
            r = check_row(checks,cw,'models',e,'shared')
            model_lines.append(f"- **Shared repair, {'centered' if cw else 'unsigned'} wide residual, {LABELS[e]}:** "
                               f"{r['requests']:,} requests, {r['clocks']:,} continuous clocks, "
                               f"{r['arithmetic_issues']:,} non-bypassed kernel requests, "
                               f"{r['narrow_requests']:,} narrow requests; zero output/state/spike mismatches.")
    for cw in [False,True]:
        for e in range(7):
            r = check_row(checks,cw,'models',e,'encoded')
            model_lines.append(f"- **Encoded metadata intermediate, {'centered' if cw else 'unsigned'} wide residual, {LABELS[e]}:** "
                               f"{r['requests']:,} requests, {r['clocks']:,} continuous clocks, "
                               f"{r['arithmetic_issues']:,} non-bypassed kernel requests, "
                               f"{r['narrow_requests']:,} narrow requests; zero output/state/spike mismatches.")
    for cw in [False,True]:
        for e in range(7):
            r = check_row(checks,cw,'models',e,'whole')
            model_lines.append(f"- **Final whole-product correction, {'centered' if cw else 'unsigned'} wide residual, {LABELS[e]}:** "
                               f"{r['requests']:,} requests, {r['clocks']:,} continuous clocks, "
                               f"{r['arithmetic_issues']:,} non-bypassed kernel requests, "
                               f"{r['narrow_requests']:,} narrow requests; zero output/state/spike mismatches.")
    accuracy = ', '.join(f"seed {r['seed']}: {100*r['accuracy']:.2f}%" for r in m['model_accuracies'])
    stress_lines = []
    for cw in [False,True]:
        for e in [0,1,3,4,5,6]:
            r = check_row(checks,cw,'stress',e)
            stress_lines.append(f"- **{'Centered' if cw else 'Unsigned'}, {LABELS[e]}:** "
                                f"{r['requests']:,} requests and {r['clocks']:,} continuous clocks.")
    for cw in [False,True]:
        for e in [3,5]:
            r = check_row(checks,cw,'stress',e,True)
            stress_lines.append(f"- **Screened stronger baseline, {'centered' if cw else 'unsigned'}, {LABELS[e]}:** "
                                f"{r['requests']:,} requests and {r['clocks']:,} continuous clocks.")
    for cw in [False,True]:
        for e in [0,1,3,4,5,6]:
            r = check_row(checks,cw,'stress',e,'shared')
            stress_lines.append(f"- **Shared repair, {'centered' if cw else 'unsigned'}, {LABELS[e]}:** "
                                f"{r['requests']:,} requests and {r['clocks']:,} continuous clocks.")
    for cw in [False,True]:
        for e in [0,1,3,4,5,6]:
            r = check_row(checks,cw,'stress',e,'encoded')
            stress_lines.append(f"- **Encoded metadata intermediate, {'centered' if cw else 'unsigned'}, {LABELS[e]}:** "
                                f"{r['requests']:,} requests and {r['clocks']:,} continuous clocks.")
    for cw in [False,True]:
        for e in [0,1,3,4,5,6]:
            r = check_row(checks,cw,'stress',e,'whole')
            stress_lines.append(f"- **Final whole-product correction, {'centered' if cw else 'unsigned'}, {LABELS[e]}:** "
                                f"{r['requests']:,} requests and {r['clocks']:,} continuous clocks.")
    hardware_sections = '\n\n'.join('### '+family.capitalize()+' family\n\n'+
                                     ('\n'.join(hardware_line(h) for h in summary['hardware_by_family'][family])
                                      if summary['hardware_by_family'][family] else 'No hardware results: this intermediate passed exact functional replay and was not routed.')
                                     for family in CHECK_FAMILIES)
    primary_comparisons = [c for c in summary['comparisons'] if c['primary_final_comparison']]
    measured_conclusions = '\n\n'.join(conclusion_lines(summary['final_cohort_findings']))
    cross_diagnostics = [c for c in summary['comparisons'] if c['adaptive_family']=='whole' and
                         c['baseline_family']!='whole' and top_fields(c['baseline'])[0] in [1,3,4,5]]
    optional = ('The scalar quotient-screen sources, checks and resource reports are included in the manifest. '
                'The screened constant signed-digit arithmetic is separately integrated into the stronger LUT/hybrid '
                'baseline core and checked/routed above. Programmable arithmetic retains the original full expression '
                'because the scalar screen tied. Scalar synthesis alone does not establish three-lane timing or an adaptive benefit.'
                if summary['optional_quotient_screens'] else 'No optional quotient-selector artifacts were present at publication.')
    return f'''# Matched pipelined membrane-aware DSP leakage trial

Completed {datetime.date.today().isoformat()}. **The input arithmetic is now included in registered timing, and the final whole-product adaptive policy is compared with strong fixed DSP/LUT hybrids and a LUT-only triple.** Primary comparisons use a common6ns constant-coefficient target and a common8ns programmable target within each cohort. The final constant adaptive core uses {adaptive['core']['LUT']} LUTs, {adaptive['core']['FF']} FFs and {adaptive['core']['DSP']} DSP; fixed hybrid encodings across the original, screened and whole-product families use {hybrid_vector}. The sampled adaptive schedule requires {ar['clocks']:,} clocks versus {hr['clocks']:,} final fixed-hybrid clocks and {lr['clocks']:,} final LUT-triple clocks. The resource vector, scheduling penalty and measured target slack below must be read together; a lower LUT count or one favorable slice placement is not an overall hardware win.

The original screened constant LUT triple remains relevant: {old_strong_lut['core']['LUT']} LUTs, {old_strong_lut['core']['FF']} FFs and zero DSPs, with setup/hold slack {old_strong_lut['WNS_ns']:+.3f}/{old_strong_lut['WHS_ns']:+.3f}ns at6ns, matching the final constant cohort target. Original/strong programmable6ns results are retained alongside final programmable8ns results with that target difference made explicit.

## Measured cohort conclusions

{measured_conclusions}

## Exact operation and scope

The declared integer update is leak(U)=ceil((256-delta)*U/256)=U-floor(delta*U/256), for signed 11-bit U and shared delta in[0,31]. Constant delta=25 means beta=231 in Q8. This trial concerns membrane leakage in a declared LIF update; it does not measure synaptic accumulation or a complete accelerator. The state representation stays exact integer U, with no approximate exponent shift.

The adaptive 7/6-bit policy consumes three available neurons when every actual membrane fits[-32,31], or when delta<=25 and all three fit[-64,63]. Otherwise it uses two exact wider lanes. The adaptive six-bit variant uses only[-32,31]. Each narrow product uses a five-bit residual and a small high-part correction; the eligibility interval does not mean that a whole seven-bit multiplication occupies each DSP field. The DSP add input supplies the folded fractional correction. The actual stored/returned membrane remains signed int11 U. CW0 uses unsigned wider residuals; CW1 uses centered wider residuals. Both arithmetic encodings are checked and routed for the strong fixed pair and hybrid references so the comparison cannot depend on a weak encoding choice.

The fixed DSP pair, fixed DSP triple, DSP/LUT hybrid triple, LUT pair and LUT triple implement the same exact update. The hybrid uses two DSP lanes and one exact fabric lane; it can always consume three full-range values. The original LUT constant coefficient is factorized for delta25 and DSP mapping is disabled. The separate stronger-baseline core replaces constant scalar arithmetic with the exact signed-digit winner from the scalar screen; programmable arithmetic stays unchanged because that screen tied. Strong-core checks replay byte-identical stimuli against the original unit. The fixed pair has the same zero/identity bypass opportunity and can return a zero third neuron. These are matched locally implemented references. The LUT-only triple is **not FireFly**.

## Separate shared repair

The shared family is an isolated implementation repair built from the stronger scalar baseline. It shares the first two adaptive pre-subtractions, replaces the constant DSP bypass control with its exact constant value, and expresses the narrow selector as an equivalent nested choice. Its actual-membrane eligibility policy, int11 state, integer update and four-clock handshake contract stay the same. Shared checks use the original stimulus bytes and cover all seven engines in both CW0/CW1 encodings. These changes are intended to reduce controller/arithmetic duplication; intent alone does not establish a mapped hardware benefit.

The tied checkpoint audit compares `top_stream_pipeline_adaptive_const` against the earlier three-stage `top_stream_fold_offset_const`, in both synthesized and routed checkpoints. It finds two 33-FF metadata banks versus two 22-FF banks, and 18 CARRY4 cells versus14. Core FF counts are151 versus86: the difference decomposes into33 raw-capture FFs,22 additional metadata FFs,4 output-sign FFs and6 control FFs. Name-derived pre-correction carry chains are12 versus8; this supports a duplication explanation without proving formal expression-to-cell correspondence. These versions have different latency, fixture and constraints, so the audit explains implementation costs rather than establishing a matched timing/throughput result. Exact source, checkpoint and decompressed EDIF hashes, cell names and indices are preserved in the audit JSON.

The shared family passed all exact checks but **was not routed**. No resource, timing or occupied-slice count is assigned to this intermediate. Its observations led to the encoded representation below.

## Verified encoded metadata intermediate

The encoded family reconstructs identity/bypass outputs from the same regular encoded metadata with a zero product floor, instead of carrying a separate full-width raw bypass payload through the output stages. The stored and returned membrane values remain exact int11. The repair and stronger scalar arithmetic apply to adaptive and fixed implementations alike, including DSP and LUT pairs, so the comparison includes strengthened fixed baselines.

The only consume-policy difference is for delta0 wide pair requests: identity alone no longer permits a third wide membrane. Three are consumed only when a fixed triple engine, the adaptive narrow condition or a zero third value permits it. The input stimuli stay byte-identical and numerical outputs match the same scalar integer oracle. Programmable main-test request counts can therefore differ legitimately. The delta25 model replay has identical request counts and K+4 clocks across the corresponding original/encoded engines, and the publisher verifies that equality.

The encoded family passed exact checks and **was not routed**. Its full-range metadata still included an input-side high-product subtraction, motivating the final whole-product correction below. No encoded hardware results are assigned to this intermediate.

## Final whole-product correction

For CW0 wide lanes, write U=256h+r with h=floor(U/256) and0<=r<=255. Pack the two r values for the DSP multiplier and put C_i=(128+delta*h_i)<<8 into each16-bit add field. The resulting field is P_i=32768+delta*U_i. Over all signed-int11 U and delta0..31, P_i lies in[1024,64481], so the two16-bit fields cannot carry into each other. Decode floor(delta*U_i/256) from the high byte by flipping its sign bit, then subtract that signed quotient from the original U stored in regular metadata. This moves the high correction into the existing DSP add input and removes the high-product-to-U subtraction from the input metadata path. Narrow arithmetic and the encoded consume policy remain unchanged; CW1 keeps the previously checked centered formulation.

The numerical wide-C screen checks all65,536 scalar U/delta combinations,48,672 adversarial packed pairs and7,760 stale-word bypass cases, with no mismatches. This validates the packing/bypass identities, not the controller, whole-core timing or every possible full-range pair. The complete RTL replay and routing below include those other costs.

Seventeen final whole-product versions are routed: all seven constant engines plus constant CW1 adaptive/fixed2/hybrid at6ns, and all seven programmable engines at8ns. They join the26 original/strong references retained at6ns. The original programmable adaptive core has setup slack−0.510ns at6ns; adaptive6 and the fixed pair also fail that target. The final programmable8ns target is conservative and shared by every final programmable candidate/baseline. The constant cohort uses the common6ns target. A negative setup or hold slack prevents calling any version closed, and a smaller schedule alone cannot establish a latency win. No operating clock is inferred by subtracting WNS from the target.

## Working core pipeline and timing fixture

All working cores have four advancing clocks from an accepted request to its output handshake, and can accept one request per advancing clock. For K uninterrupted requests, measured service spans K+4 clocks. Output backpressure freezes arithmetic, metadata and DSP stages; the source must hold valid and its complete payload while backpressured. Reset cancels queued requests. Tail availability counts real neurons, with poisoned unavailable input bits tested independently of the arithmetic oracle.

The synthesis fixture adds 43 unconditional input-launch registers and 40 unconditional output-capture registers, exactly **83 fabric FFs outside the core**. It makes the raw-U monitor, input correction, availability/coefficient processing and backpressure paths clock-to-clock. It is deliberately a timing fixture, not a production handshake adapter. Its extra registers are not included in the functional K+4 core schedule or hidden inside core resource counts.

Vivado2025.2 routes xc7a100tcsg324-1 out of context with original/strong6ns targets, final constant6ns targets and final programmable8ns targets, using explicit HD.CLK_SRC=BUFGCTRL_X0Y0. Hierarchy/register preservation applies equally to all candidates and constrains optimization across boundaries. Core LUT/FF/DSP counts are separated from the full fixture. Core and fixture can share SLICE sites: touched slices are nonadditive. The complete fixture occupied-slice count is therefore shown alongside the core resource vector; no area win is inferred solely from the core touched-site count.

The main setup/hold reports now include registered input arithmetic. They are not the earlier unregistered-port timing measurements. Raw-port max1ns/min0.1ns budgets are applied afterward and reported separately. A candidate passes its declared target only when both registered setup and hold slack are nonnegative. Subtracting WNS from6ns or8ns does not certify an operating frequency. No board clock, physical board latency, power or energy measurement is provided.

## Verification and sampled SNN equality

The40 CW0/CW1 check sets across original, stronger-baseline, shared, encoded and whole-product families cover **{m['engine_configuration_runs']} engine/configuration runs**, {m['neuron_output_comparisons']:,} neuron-output comparisons and {m['request_output_comparisons']:,} retired-request comparisons, with zero detected numerical mismatches. These totals repeat inputs across configurations and references; they are not distinct exhaustive triples. Scalar range/coefficient cases, boundary triples, narrow triples, random longer windows, coefficient changes, one/two/three-neuron tails, identity/zero bypass, source gaps, held-input backpressure, output stability and reset cancellation are checked. Acceptance-to-retirement timing is checked for four advancing clocks. No claim of exhaustive full-range triple verification follows from this test set.

The model replay contains {m['model_neurons_per_engine']:,} real neuron updates in {m['model_frames']:,} frames: first48 images from each of three saved seeds, for **144 images total**. Python adds recorded currents and applies threshold/subtractive reset after the RTL leakage outputs. Every reconstructed membrane, spike and output spike count matches the scalar beta231 reference. Sampled classification accuracy is {accuracy}. This is equality to the declared beta231 update, not proof of unchanged accuracy versus the models' originally trained leakage; there was no retraining and no full360-image streaming RTL evaluation.

## Sampled clocks and useful work

{chr(10).join(model_lines)}

Within each final whole-product coefficient cohort (constant6ns, programmable8ns), these cycle counts express scheduling differences. They exclude state-memory transfers, synaptic integration, threshold/reset hardware, frame barriers and host costs. Cross-family programmable results retain their distinct6ns/8ns targets and are resource/schedule diagnostics. Programmable hardware comparisons use the same **delta25 model schedule**, not a different trained or programmable-coefficient SNN. Setup/hold failures prevent treating a target as closed even when the cycle count is smaller.

Of {m['model_neurons_per_engine']:,} model membranes, {m['nonzero_model_membranes']:,} are nonzero and only {m['changed_model_membranes']:,} change under leakage. The `arithmetic_issues` field means non-bypassed kernel requests for every engine, including LUT engines; it is not automatically an active DSP count or proof that every lane performs changing useful work. With delta25, U in[0,10] is an exact fixed point. An additional identity-aware filter remains an analytic opportunity and was not implemented or routed. The existing zero/identity bypass must not be described as covering all unchanged nonzero values.

The pinned trace-accounting audit separately counts changing DSP operations, unchanged nonzero operations, zero lanes, unused tail slots and the hybrid's LUT lane. On the model traces, changing operations per issued DSP are 1.3866 for adaptive7/6, 1.3188 for adaptive6, 1.0091 for the fixed pair, 1.4316 for the fixed DSP triple, and 0.9566 for the hybrid's DSP pair. The hybrid additionally executes 99,503 changing operations in its LUT third lane. Adaptive7/6 improves changing operations per issue by37.4% over the pair but is3.14% below the fixed DSP triple. When divided by the actual two/three-lane capacity of issued requests, its changing fraction is48.66%, versus50.45% for the pair and47.72% for the fixed triple. These distinct denominators answer different questions; neither establishes measured clock utilization, power or energy. The JSON includes seed and synthetic reset-policy breakdowns, and schedule counts match the final RTL checks.

An independent recount confirms these numerators and denominators. Zero-third-copy counts and all-valid hybrid LUT-third counts include bypassed requests, so they overlap the bypassed-neuron total and must not be summed as disjoint categories. The audit records active/bypassed splits and verifies a separate disjoint neuron sum. The hybrid fabric lane computes on valid requests even when DSP arithmetic is bypassed; its DSP metric alone cannot determine total core throughput.

## Routed resource vectors and target slack

{hardware_sections}

## Primary final comparisons within each coefficient cohort

Final adaptive and fixed/LUT references share the same6ns constant target or8ns programmable target within each coefficient cohort. Both routed wider-residual encodings of the constant pair/hybrid appear. Positive cycle-saving values mean fewer adaptive cycles; positive resource/slice differences mean more adaptive resources. The numbers are separate dimensions of a tradeoff, not a weighted area score or accelerator throughput result.

{chr(10).join(comparison_line(c) for c in primary_comparisons)}

## Original6ns reference diagnostics

Constant comparisons share the6ns target and retain additional original/strong references. Programmable comparisons cross6ns/8ns targets: resource vectors and request counts remain useful evidence, but they do not establish a matched-clock hardware or latency win. Every line displays both targets and closure. The full JSON also retains all earlier same-target comparisons.

{chr(10).join(comparison_line(c) for c in cross_diagnostics)}

## Synthetic burst replay

{chr(10).join(stress_lines)}

This stream is a synthetic sparse/burst stimulus. It does not prove a natural-model burst latency improvement or a worst-case guarantee. For complete three-neuron windows that force a two-lane fallback, fixed triples consume fewer request slots. Three available input states and three result writes per clock require enough memory bandwidth; the memory/controller costs remain unmeasured.

## Interpretation and unresolved work

This trial includes monitored input arithmetic between registers and measures a small arithmetic/policy unit. The concrete cohort conclusions above use the resource vector, target timing and sample schedule together. They establish only the stated implementation tradeoffs. A single component count or placement does not justify an overall hardware win, and the zero-DSP reference remains part of the comparison.

{optional}

No FireFly RTL, network throughput, power, host cost or accelerator accuracy comparison was reproduced. FireFly is related work rather than the matched LUT baseline here. Novelty remains unproved: the policy depends on actual membranes, but this implementation study does not establish first-ever novelty. Generic DSP packing and correction are already documented in the prior literature.

{chr(10).join('- '+s for s in summary['limitations'])}

## Reproduction and evidence

The archive contains current core/fixture RTL, testbench and checking/route/publisher scripts, exact stimuli and retired outputs, scalar/model check JSON, model inputs and ledger, range evidence, selected build/simulation logs, routed reports/checkpoints, this report and the summary. Simulator object trees and waveform databases are excluded. The SHA256 manifest identifies exact archive members; every payload hash and ZIP CRC is verified before final publication. No tool binaries, new packages, datasets or model downloads are included. The original external research folder is unchanged.
'''.replace('in[','in [').replace('fit[','fit [').replace('first48','first 48').replace('full360','full 360').replace('Vivado2025.2','Vivado 2025.2').replace('common8ns','common 8 ns').replace('at8ns','at 8 ns').replace('8ns','8 ns').replace('6ns','6 ns').replace('max1ns/min0.1ns','max 1 ns/min 0.1 ns').replace('from6ns','from 6 ns').replace('delta25','delta = 25').replace('delta0','delta = 0').replace('beta231','beta = 231').replace('the26','the 26').replace('The40','The 40').replace('original/strong6','original/strong 6').replace('constant6','constant 6').replace('programmable6','programmable 6').replace('programmable8','programmable 8').replace('final8','final 8').replace('Original6','Original 6').replace('at6','at 6').replace('or8','or 8').replace('same6','same 6').replace('common6','common 6').replace('common8','common 8').replace('are151 versus86','are 151 versus 86').replace('into33','into 33').replace('FFs,22','FFs, 22').replace('FFs,4','FFs, 4').replace('and6 control','and 6 control').replace('are12 versus8','are 12 versus 8').replace('versus14','versus 14').replace('slack−0.510','slack −0.510').replace('and0<=','and 0<=').replace('each16-bit','each 16-bit').replace('two16-bit','two 16-bit').replace('all65,536','all 65,536').replace('and48,672','and 48,672')


def evidence_files(summary):
    files = set()
    for name in ['stream_pipeline_leak.sv','tb_stream_pipeline_leak.sv','stream_pipeline_timing.sv',
                 'stream_pipeline_strong_leak.sv','tb_stream_pipeline_strong_leak.sv','stream_pipeline_strong_timing.sv',
                 'stream_pipeline_shared_leak.sv','tb_stream_pipeline_shared_leak.sv','stream_pipeline_shared_timing.sv',
                 'stream_pipeline_encoded_leak.sv','tb_stream_pipeline_encoded_leak.sv','stream_pipeline_encoded_timing.sv',
                 'stream_pipeline_whole_leak.sv','tb_stream_pipeline_whole_leak.sv','stream_pipeline_whole_timing.sv',
                 'check_stream_pipeline.py','check_stream_pipeline_models.py','route_stream_pipeline.tcl',
                 'check_stream_pipeline_strong.py','check_stream_pipeline_strong_models.py',
                 'check_stream_pipeline_shared.py','check_stream_pipeline_shared_models.py',
                 'route_stream_pipeline_shared.tcl','run_stream_pipeline_shared_route.py',
                 'check_stream_pipeline_encoded.py','check_stream_pipeline_encoded_models.py',
                 'route_stream_pipeline_encoded.tcl','run_stream_pipeline_encoded_route.py',
                 'check_stream_pipeline_whole.py','check_stream_pipeline_whole_models.py',
                 'route_stream_pipeline_whole.tcl','run_stream_pipeline_whole_route.py',
                 'screen_pipeline_whole_math.py',
                 'audit_pipeline_register_cost.py','stream_fold_leak.sv',
                 'run_stream_pipeline_route.py','publish_stream_pipeline.py','audit_adaptive_delta_bounds.py']:
        assert (P/name).is_file(), name
        files.add(P/name)
    for glob in ['*stream_pipeline*.py','*quotient*.py']:
        files.update(path for path in P.glob(glob) if path.is_file())
    for key in summary['checks']:
        files.add(R/(key+'_checks.json'))
        directory = R/key
        assert directory.is_dir(), key
        files.update(path for path in directory.iterdir() if path.is_file() and
                     (path.suffix=='.txt' or path.name.startswith('tool_')))
    files.add(R/'stream_pipeline_hardware.json')
    files.add(R/'stream_pipeline_whole_hardware.json')
    files.add(R/'stream_pipeline_whole_math_checks.json')
    files.add(R/'stream_pipeline_whole_activity.json')
    files.add(P/'analyze_stream_pipeline_whole_activity.py')
    files.add(R/'stream_pipeline_whole_activity_audit.json')
    files.add(P/'audit_stream_pipeline_whole_activity.py')
    files.add(R/'pipeline_register_cost_audit.json')
    files.add(R/'stream_fold_hardware.json')
    for observation in summary['implementation_audit']['observations']:
        files.add(Path(observation['rtl_path']))
        for checkpoint in observation['checkpoints']:
            files.add(Path(checkpoint['path']))
    for h in summary['hardware']:
        directory = R/(h['top']+'_route')
        files.update(path for path in directory.iterdir() if path.is_file() and
                     path.suffix in ['.rpt','.txt','.dcp'])
        synth = R/(h['top']+'_synth')
        # Retain synth reports/provenance, but not a second large DCP per row.
        files.update(path for path in synth.iterdir() if path.is_file() and
                     path.suffix in ['.rpt','.txt'])
        for suffix in ['*build.log','*vivado.log','*vivado.jou']:
            files.update(R.glob(h['top']+suffix))
    for name in ['adaptive_delta_model_input.json','adaptive_delta_stress_input.json',
                 'adaptive_delta_model_bounds.json','final_selected.json',
                 'adaptive_delta_model_25_1/expected.npz','adaptive_delta_stress_25_1/expected.npz']:
        assert (R/name).is_file(), name
        files.add(R/name)
    files.update(R.glob('model_seed*.npz'))
    files.update(R/name for name in summary['optional_quotient_screens'])
    # Optional scalar quotient screen: sources, checked retired values and tool
    # logs are required evidence too. Exclude xsim object/waveform trees here.
    for name in ['quotient_screen.sv','tb_quotient_screen.sv',
                 'screen_pipeline_quotients.py','screen_pipeline_quotients.tcl']:
        if (P/name).is_file():
            files.add(P/name)
    screen_pin = (summary.get('quotient_screen') or {}).get('source_sha256')
    for check in R.glob('quotient_screen_*_checks.json'):
        data = json.loads(check.read_text())
        if screen_pin:
            assert data['source_sha256']==screen_pin, ('Quotient check source mismatch',check)
            assert data['mismatches']==0
        files.add(check)
        directory = R/check.name.removesuffix('_checks.json')
        if directory.is_dir():
            files.update(path for path in directory.iterdir() if path.is_file() and
                         (path.suffix=='.txt' or path.name.startswith('tool_')))
    for directory in R.glob('top_quotient_*_screen'):
        if directory.is_dir():
            files.update(path for path in directory.iterdir() if path.is_file() and
                         path.suffix in ['.rpt','.txt','.dcp'])
    for pattern in ['top_quotient_*_screen_build.log','top_quotient_*_screen_vivado.log',
                    'top_quotient_*_screen_vivado.jou']:
        files.update(R.glob(pattern))
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ready',action='store_true',help='Explicit completion signal; refuses publication without this flag.')
    args = ap.parse_args()
    assert args.ready, 'Wait until all simulations and routes finish, then run with --ready.'
    print('Publisher free GiB',round(mem_free_gib(),2),flush=True)
    assert mem_free_gib()>1.2, 'Insufficient free RAM to publish model evidence'
    summary = gather()
    pinned = {path:sha(path) for path in evidence_files(summary)}
    O.mkdir(exist_ok=True)
    staging = O/('.'+STEM+'_staging')
    staging.mkdir(exist_ok=True)
    summary_path = staging/(STEM+'.summary.json')
    report_path = staging/(STEM+'.md')
    summary_path.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    report_path.write_text(report(summary),encoding='utf-8')
    files = sorted(pinned)
    entries = []
    sources = []
    for path in files:
        entries.append(dict(path=str(path.relative_to(P)).replace('\\','/'),
                            bytes=path.stat().st_size,sha256=pinned[path]))
        sources.append(path)
    for path in [report_path,summary_path]:
        entries.append(dict(path='outputs/'+path.name,bytes=path.stat().st_size,sha256=sha(path)))
        sources.append(path)
    manifest = dict(source_hashes=summary['source_hashes'],metrics=summary['metrics'],files=entries,
                    omitted='Simulator objects and waveform databases; synthesis DCPs except the explicitly audited checkpoints.',
                    occupied_slice_accounting='Nonadditive core/fixture touched sites; compare full-fixture occupied slices.')
    manifest_path = staging/(STEM+'.manifest.json')
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive = staging/(STEM+'.evidence.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for index,(path,entry) in enumerate(zip(sources,entries)):
            assert sha(path)==entry['sha256'], ('Evidence changed during publication',path)
            z.write(path,entry['path'])
            if index%30==0:print('Archived',index+1,'of',len(entries),'files',flush=True)
        z.write(manifest_path,'outputs/'+manifest_path.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None, 'ZIP CRC failure'
        for entry in entries:
            h = hashlib.sha256()
            with z.open(entry['path']) as f:
                for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
            assert h.hexdigest()==entry['sha256'], ('Archived SHA mismatch',entry['path'])
        assert hashlib.sha256(z.read('outputs/'+manifest_path.name)).hexdigest()==sha(manifest_path)
    assert all(sha(path)==stamp for path,stamp in pinned.items()), 'Evidence changed while archive was built'
    for path in [report_path,summary_path,manifest_path,archive]:
        path.replace(O/path.name)
    staging.rmdir()
    print(json.dumps(dict(metrics=summary['metrics'],output_stem=str(O/STEM),
                          evidence_files=len(entries)+1,zip_bytes=(O/archive.name).stat().st_size,
                          verification='All payload SHA256 and ZIP CRC verified'),indent=2),flush=True)


if __name__=='__main__':
    main()
