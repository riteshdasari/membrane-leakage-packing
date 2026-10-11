"""Lightweight exact/common-layout policy screen. No HDL tools are launched.

This screen preserves six eight-bit DSP residue fields. Runtime changes affect
exact high-part correction, not the DSP lane count. Queue and serialized
service figures are explicitly ideal arithmetic models, not measured latency.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent))
import check_guard_add as original
import numpy as np


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def signed(bits, width):
    return bits - (1 << width) if bits & (1 << (width - 1)) else bits


def exact_scalar(u, i):
    residue = (u & 127) + (i & 127)
    high = (u >> 7) + (i >> 7) + (residue >> 7)
    assert -16 <= high <= 15
    return 128 * high + (residue & 127)


def proof_screen():
    """Exhaust every signed11 pair; enumerate high/carry shortcuts separately."""
    other = np.arange(-1024, 1024, dtype=np.int64)
    full = fast7 = fast8 = current8 = current8_copy = 0
    for u in range(-1024, 1024):
        s = (u & 127) + (other & 127)
        c = s >> 7
        high = (u >> 7) + (other >> 7) + c
        got = high * 128 + (s & 127)
        assert np.array_equal(got, u + other)
        full += len(other)
        f7 = (-64 <= u <= 63) & (other >= -64) & (other <= 63)
        if np.any(f7):
            corrected8 = ((s ^ (128 * ((u < 0) ^ (other < 0)))) & 255)
            got7 = np.where(corrected8 & 128, corrected8 - 256, corrected8)
            assert np.array_equal(got7[f7], (u + other)[f7])
            fast7 += int(np.count_nonzero(f7))
        f8 = (-128 <= u <= 127) & (other >= -128) & (other <= 127)
        if np.any(f8):
            high8 = c - int(u < 0) - (other < 0)
            assert np.array_equal(high8[f8] * 128 + (s[f8] & 127), (u + other)[f8])
            fast8 += int(np.count_nonzero(f8))
        i8 = (other >= -128) & (other <= 127)
        simplified = (u >> 7) + c - (other < 0)
        assert np.array_equal(simplified[i8] * 128 + (s[i8] & 127), (u + other)[i8])
        current8 += int(np.count_nonzero(i8))
        copy = i8 & (c == (other < 0))
        assert np.all(high[copy] == (u >> 7))
        current8_copy += int(np.count_nonzero(copy))
    return dict(full_signed11_pairs=full, signed7_fast_path_pairs=fast7,
                signed8_fast_path_pairs=fast8, current_signed8_pairs=current8,
                current_signed8_direct_high_copy_pairs=current8_copy, mismatches=0)


def packed_stress():
    """Every high pair/carry in every lane, plus poisoned unavailable tails."""
    cases = 0
    # Each high pair permits both residue carries. Field0/7 boundaries are
    # checked around these enumerations by the full scalar proof above.
    for hu in range(-8, 8):
        for hi in range(-8, 8):
            for carry in range(2):
                for lane in range(6):
                    u = [-1024, -1, 0, 127, 1023, -128]
                    i = [1023, -1, 127, 0, -1024, 127]
                    u[lane] = 128 * hu + (127 if carry else 0)
                    i[lane] = 128 * hi + (1 if carry else 0)
                    pa = sum((a & 127) << (8*j) for j, a in enumerate(u))
                    pb = sum((b & 127) << (8*j) for j, b in enumerate(i))
                    pp = pa + pb
                    assert pp < (1 << 48)
                    for available in range(1, 7):
                        got = []
                        for j in range(6):
                            residue = (pp >> (8*j)) & 255
                            high = (u[j] >> 7) + (i[j] >> 7) + (residue >> 7)
                            got.append(128 * high + (residue & 127) if j < available else 0)
                        assert got == [a+b if j < available else 0 for j, (a,b) in enumerate(zip(u, i))]
                        cases += 1
    return dict(packed_cases=cases, mismatches=0)


def ideal_queue(jobs, width, capacity):
    """One offered window/cycle; bounded job queue, no actual RTL/reorder cost.

    Service occurs first; a whole window is accepted only if all its jobs fit.
    All windows retain original order. Tail correction work is drained. DSP
    latency, high-result buffering and ready timing are not modeled here.
    """
    backlog = clocks = stalls = peak = 0
    for n in jobs:
        assert 0 <= n <= 6 and capacity >= 6
        while max(0, backlog-width) + n > capacity:
            backlog = max(0, backlog-width)
            clocks += 1
            stalls += 1
        backlog = max(0, backlog-width) + n
        peak = max(peak, backlog)
        clocks += 1
    while backlog:
        backlog = max(0, backlog-width)
        clocks += 1
    return dict(shared_correctors=width, capacity_jobs=capacity,
                offered_windows=len(jobs), correction_queue_clocks=clocks,
                admission_stalls=stalls, peak_jobs=peak,
                qualification='Ideal job admission only; no DSP pipeline, output reorder, dependency, memory or RTL timing cost.')


def fused_service(jobs, width=1):
    """Declared controller model: first correction is fused into output stage.

    A window with k corrections takes ceil(k/width) output-stage attempts,
    with the first included in the ordinary four-advance pipeline. All other
    attempts freeze the entire pipeline; their clocks are additive. No queue,
    memory controller, input gap or output backpressure is modeled.
    """
    extra = sum(max(0, (k+width-1)//width - 1) for k in jobs)
    clocks = len(jobs) + 4 + extra
    return dict(fallback_corrections_per_output_attempt=width, offered_windows=len(jobs),
                exceptional_fallback_jobs=sum(jobs), exception_windows=sum(k != 0 for k in jobs),
                extra_globally_frozen_clocks=extra,
                predicted_service_clocks=clocks,
                fixed6_service_clocks=len(jobs)+4,
                service_clock_penalty=extra/(len(jobs)+4),
                qualification='Declared fused-output/global-freeze controller model, continuous input and out_ready=1; not measured RTL or physical burst latency.')


def cycle_model_global_freeze(jobs):
    """Independent control-only model with three internal stages and output.

    The oldest output is consumed independently of a new window's correction
    freeze, preventing repeated retirement of a held valid output. This is a
    reference model, not an implementation or a substitute for RTL testing.
    """
    pipeline = [None, None, None]
    output = None
    correction_remaining = None
    clock = accepted = retired = freezes = 0
    accept_clocks, latency_hist = {}, Counter()
    while retired < len(jobs):
        if output is not None:
            assert output == retired
            latency_hist[clock-accept_clocks.pop(output)] += 1
            retired += 1
            output = None
        oldest = pipeline[2]
        freeze = False
        if oldest is not None:
            if correction_remaining is None:
                correction_remaining = max(0, jobs[oldest]-1)
                freeze = correction_remaining != 0
            elif correction_remaining > 1:
                correction_remaining -= 1
                freeze = True
            else:
                assert correction_remaining == 1
                correction_remaining = 0
        if freeze:
            freezes += 1
        else:
            output = oldest
            correction_remaining = None
            pipeline[2] = pipeline[1]
            pipeline[1] = pipeline[0]
            pipeline[0] = accepted if accepted < len(jobs) else None
            if accepted < len(jobs):
                accept_clocks[accepted] = clock
                accepted += 1
        clock += 1
        assert clock <= len(jobs)*6+4
    assert accepted == retired == len(jobs) and not accept_clocks
    assert clock == len(jobs)+4+sum(max(k-1,0) for k in jobs)
    assert freezes == sum(max(k-1,0) for k in jobs)
    return dict(service_clocks=clock, accepted_requests=accepted, retired_requests=retired,
                global_freeze_clocks=freezes, latency_clock_histogram=dict(sorted(latency_hist.items())),
                repeated_or_out_of_order_retirements=0,
                qualification='Independent Python control-only model of declared fused-output/global-freeze behavior, continuously ready source/sink. Does not execute RTL.')


def correction_burst_proof():
    """Exact adversarial windows for generic and current8-specialized variants."""
    out = []
    patterns = [
        ('full_signed11', [1023]*6, [1023]*6),
        ('static_signed8_current', [1023]*6, [127]*6),
        ('static_signed8_current_negative', [-1024]*6, [-128]*6),
        ('highcopy_wide_positive', [1023]*6, [0]*6),
        ('highcopy_wide_negative', [-1024]*6, [0]*6),
    ]
    for name, u, i in patterns:
        bad = []
        for a, b in zip(u, i):
            c = ((a & 127)+(b & 127)) >> 7
            fit_u = -128 <= a <= 127
            fit_i = -128 <= b <= 127
            fast = fit_i and (fit_u or c == int(b < 0))
            bad.append(int(not fast))
            assert exact_scalar(a, b) == a+b
        k = sum(bad)
        count = 64
        series = [k]*count
        schedule = fused_service(series)
        assert schedule['extra_globally_frozen_clocks'] == count * max(k-1, 0)
        out.append(dict(pattern=name, windows=count, membrane=u, current=i,
                        correction_mask=bad, output=[a+b for a,b in zip(u,i)],
                        scalar_mismatches=0, cycle_model=cycle_model_global_freeze(series), **schedule))
    return out


def static_current_certificate(ledger):
    """Exact known-weight bound for arbitrary incoming binary spike vectors."""
    pins, rows, arrays = {}, [], {}
    for seed in range(3):
        path = original.R / f'model_seed{seed}.npz'
        pins[path.name] = sha(path)
        with np.load(path) as saved:
            for layer, key in enumerate(('w0', 'w1')):
                w = saved[key].astype(np.int64)
                assert np.array_equal(w, saved[key])
                negative = np.minimum(w, 0).sum(axis=0)
                positive = np.maximum(w, 0).sum(axis=0)
                assert np.all(negative >= -128) and np.all(positive <= 127)
                arrays[seed, layer] = negative, positive
                rows.append(dict(seed=seed, layer=layer, inputs=w.shape[0], outputs=w.shape[1],
                                 minimum_current=int(negative.min()), maximum_current=int(positive.max()),
                                 all_neuron_binary_spike_currents_fit_signed8=True))
    for rec in ledger:
        negative, positive = arrays[rec['seed'], rec['layer']]
        current = np.asarray(rec['current'])
        assert current.shape == negative.shape
        assert np.all(current >= negative) and np.all(current <= positive)
    assert pins == {name: sha(original.R/name) for name in pins}
    old_paths = ['audit_adaptive_delta_bounds.py', 'results/adaptive_delta_model_bounds.json']
    existing_bounds = {name: sha(P.parent/name) for name in old_paths}
    return dict(weight_files_sha256=pins, rows=rows, failures=0,
                prior_bound_artifact_sha256=existing_bounds,
                proof='For any x_j in {0,1}, sum_j min(w_j,0) <= sum_j x_j*w_j <= sum_j max(w_j,0).',
                qualification='Exact for these saved integer weights and binary spikes/current prefixes; unrelated weights, nonbinary spikes or additional currents need their own bounds.',
                hardware_implication='A separately declared signed11-U/signed8-I baseline may statically implement H = hU + c - signI without a runtime I8 detector. General signed11-U/signed11-I hardware still requires fallback.')


def model_screen():
    frames, model_pin = original.model_frames()
    files = original.R / original.MODEL_INPUTS[1]
    ledger = json.loads(files.read_text())['ledger']
    assert len(frames) == len(ledger)
    nscalar = windows = 0
    hist = Counter()
    window_hist = {'signed7': Counter(), 'signed8': Counter(), 'current8': Counter(),
                   'signed8_or_highcopy': Counter(), 'highcopy': Counter()}
    distributions = {k: Counter() for k in ['hU', 'hI', 'hU_plus_hI', 'H', 'c', 'operand_sign_pair']}
    jobs = {k: [] for k in window_hist}
    pair_counts = {k: Counter() for k in ['signed7', 'signed8', 'signed8_or_highcopy', 'highcopy']}
    block_counts = {k: Counter() for k in ['signed7', 'signed8', 'signed8_or_highcopy', 'highcopy']}
    reuse = Counter()
    prev = {}
    per_seed = {0: Counter(), 1: Counter(), 2: Counter()}
    temporal_high = Counter()
    full_ref_mismatch = 0
    for (u, i, _), rec in zip(frames, ledger):
        status = []
        for neuron, (a, b) in enumerate(zip(u, i)):
            ru, ri = a & 127, b & 127
            c = (ru + ri) >> 7
            hu, hi = a >> 7, b >> 7
            h = hu + hi + c
            f7 = -64 <= a <= 63 and -64 <= b <= 63
            f8 = -128 <= a <= 127 and -128 <= b <= 127
            i8 = -128 <= b <= 127
            copy = i8 and c == int(b < 0)
            union = f8 or copy
            sums = exact_scalar(a, b)
            fired = int(sums >= rec['threshold'])
            state = sums - fired * rec['threshold']
            full_ref_mismatch += int(fired != rec['expected_spikes'][neuron])
            full_ref_mismatch += int(state != rec['expected_state'][neuron])
            assert sums == a + b
            if f7:
                restored = ((ru+ri) ^ (128 * ((a < 0) ^ (b < 0)))) & 255
                assert signed(restored, 8) == sums
            if f8:
                assert 128 * (c-int(a < 0)-int(b < 0)) + ((ru+ri) & 127) == sums
            if copy:
                assert h == hu
            stats = dict(signed7=f7, signed8=f8, current8=i8,
                         signed8_or_highcopy=union, highcopy=copy)
            status.append(stats)
            for key, eligible in stats.items():
                hist[key] += int(eligible)
                per_seed[rec['seed']][key] += int(eligible)
            hist['zero_current'] += int(b == 0)
            hist['zero_low_carry'] += int(c == 0)
            hist['hI_zero'] += int(hi == 0)
            hist['hI_minus1'] += int(hi == -1)
            hist['hU_plus_hI_zero'] += int(hu + hi == 0)
            hist['nontrivial_hU'] += int(hu not in (-1, 0))
            per_seed[rec['seed']]['scalars'] += 1
            for key, value in [('hU', hu), ('hI', hi), ('hU_plus_hI', hu+hi),
                               ('H', h), ('c', c), ('operand_sign_pair', f'{int(a<0)}{int(b<0)}')]:
                distributions[key][value] += 1
            identity = (rec['seed'], rec['image'], rec['layer'], neuron)
            if identity in prev:
                last_t, old_hu, old_hi, old_sum = prev[identity]
                assert rec['t'] == last_t + 1
                reuse['eligible_timestep_pairs'] += 1
                reuse['same_hU'] += int(old_hu == hu)
                reuse['same_hI'] += int(old_hi == hi)
                reuse['same_both_keys'] += int((old_hu, old_hi) == (hu, hi))
                reuse['same_hU_plus_hI'] += int(old_sum == hu+hi)
                temporal_high[(old_hu, hu)] += 1
            prev[identity] = (rec['t'], hu, hi, hu+hi)
            nscalar += 1
        for key in block_counts:
            block_counts[key][sum(not x[key] for x in status)] += 1
        for pos in range(0, len(u), 6):
            group = status[pos:pos+6]
            windows += 1
            for key in window_hist:
                k = sum(not x[key] for x in group)
                window_hist[key][k] += 1
                jobs[key].append(k)
            for key in pair_counts:
                for j in range(0, len(group), 2):
                    pair_counts[key][sum(not x[key] for x in group[j:j+2])] += 1
    assert nscalar == 635904 and windows == 110592 and full_ref_mismatch == 0
    serial = []
    for key in ('signed7', 'signed8', 'signed8_or_highcopy'):
        for width in (1, 2):
            # Explicit conservative, non-overlapped exception phase: one base
            # issue plus ceil(k/width) correction issue slots per request.
            extra = sum((k + width - 1)//width for k in jobs[key])
            clocks = windows + extra + 4
            serial.append(dict(certificate=key, shared_correctors=width,
                               exception_jobs=sum(jobs[key]), extra_correction_slots=extra,
                               ideal_serial_service_clocks=clocks,
                               native4_service_clocks=159540, hybrid6_service_clocks=110596,
                               rate_vs_native4=159540/clocks-1,
                               rate_vs_hybrid6=110596/clocks-1,
                               qualification='Arithmetic schedule assumption only; one six-lane base slot, added correction slots, four startup/drain clocks. Not RTL or burst latency.'))
    queued = {key: [ideal_queue(jobs[key], width, capacity)
                   for width in (1, 2) for capacity in (6, 12, 24)]
              for key in ('signed7', 'signed8', 'signed8_or_highcopy')}
    static_certificate = static_current_certificate(ledger)
    certificate_path = P/'common_i8_current_bounds.json'
    certificate_path.write_text(json.dumps(dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        script_sha256=sha(Path(__file__)), model_input_sha256=model_pin,
        **static_certificate), indent=2), encoding='utf-8')
    fused = []
    for variant in range(4):
        adaptive = variant in (1, 3)
        schedule = fused_service(jobs['signed8_or_highcopy']) if adaptive else fused_service([0]*windows)
        fused.append(dict(variant=variant, shared_correction=adaptive,
                          declared_general_corrector_units=1 if adaptive else 6,
                          current_contract='signed8' if variant >= 2 else 'signed11',
                          policy='signed8 U/I recovery OR current8 carry-certified high copy' if adaptive else 'fixed six exact high corrections',
                          actual_exception_jobs=sum(jobs['signed8_or_highcopy']) if adaptive else None,
                          cycle_model=cycle_model_global_freeze(jobs['signed8_or_highcopy'] if adaptive else [0]*windows),
                          **schedule))
    return dict(model_input_sha256=model_pin, frames=len(frames), scalars=nscalar,
                fixed6_windows=windows, reference_state_spike_mismatches=full_ref_mismatch,
                eligible_scalar_pairs=dict(hist), per_seed={str(k): dict(v) for k,v in per_seed.items()},
                metadata_distributions={k: {str(a): b for a,b in sorted(v.items())} for k,v in distributions.items()},
                exception_jobs_per_window={k: dict(sorted(v.items())) for k,v in window_hist.items()},
                exception_jobs_per_adjacent_pair={k: dict(sorted(v.items())) for k,v in pair_counts.items()},
                exception_jobs_per_neuron_record={k: dict(sorted(v.items())) for k,v in block_counts.items()},
                temporal_cache_diagnostic=dict(reuse), persistent_neuron_identities=len(prev),
                temporal_cache_storage_scenarios=dict(
                    explicit_key_plus_high_sum_bits_per_live_neuron=13,
                    neurons_per_saved_image=138,
                    one_live_image_payload_bits=138*13,
                    forty_eight_live_images_payload_bits=48*138*13,
                    all_dataset_identities_payload_bits=len(prev)*13,
                    qualification='Payload-only scenarios, before valid/ownership/address/ports. Dataset identity count is cumulative over144 images/3 seeds; it is not a measured peak-concurrent hardware footprint. Cache can be invalidated/reused across images.'),
                temporal_hU_transitions={f'{a}->{b}': n for (a,b),n in sorted(temporal_high.items())},
                ideal_nonoverlapped_correction_schedules=serial,
                ideal_bounded_correction_admission=queued,
                predicted_fused_global_freeze_variants=fused,
                expected_fixed6_four_advance_service_clocks=windows+4,
                static_current_certificate=static_certificate,
                static_current_certificate_artifact=dict(path=certificate_path.name,
                    bytes=certificate_path.stat().st_size, sha256=sha(certificate_path)),
                qualification='Saved beta231 integer reference only; sampled144 images/3 seeds, no retraining or preserved trained-model accuracy claim.')


def main():
    pins = {'contract_sha256': sha(P/'CONTRACT.md'),
            'oracle_sha256': sha(P.parent/'check_guard_add.py'),
            'script_sha256': sha(Path(__file__))}
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(), **pins,
                  operation='Exact signed11 U + signed11 I -> signed12, six fixed eight-bit residue fields',
                  classification='Adaptive exact high-part correction for fixed packed DSP addition; DSP lane count is unchanged.',
                  arithmetic_proof=proof_screen(), packed_stress=packed_stress(),
                  declared_controller='First bad-lane correction is fused into output stage; one shared corrector globally freezes max(k-1,0) extra clocks for k bad lanes.',
                  correction_adversarial_bursts=correction_burst_proof(),
                  models=model_screen(),
                  policies=[
                      dict(name='A: sign-certified fast path with shared exact fallback',
                           certificate='Signed8 U and I; signed7 is checked as the prior stricter special case.',
                           fast_path='H = c - sU - sI; signed2 H is sign extended. Signed7 can instead restore/sign-extend signed8 sum.',
                           fallback='Exact full signed5 H = hU + hI + c, shared among exception lanes.',
                           required_overhead=['Per-lane signed8 fit detection and operand signs.',
                                              'General high operands must survive until fallback; do not count their registers as removed.',
                                              'Exception masks, selection muxes, ready/backpressure control and output assembly.',
                                              'Overlapped correction requires job tags and bounded result/reorder storage.']),
                      dict(name='B: safely certified direct high copy / high-sum reuse',
                           certificate='Current fits signed8 and residue carry c equals current sign sI.',
                           fast_path='H = hU; otherwise signed8 current needs exact H = hU +/- 1, and other currents need full fallback.',
                           strengthened_A='A signed8 U/I fast path OR the high-copy certificate can handle some wide membranes without a general correction job.',
                           temporal_reuse='Reuse cached hU+hI only when both stored four-bit high keys match; equal sum alone is a retrospective diagnostic, not a free certificate.',
                           required_overhead=['Carry arrives from DSP; high-copy selection and saved hU are needed.',
                                              'Signed8-current certificate, plus increment/decrement or shared fallback.',
                                              'A plain explicit-key persistent reuse cache stores 8 key bits + 5 cached high-sum bits per neuron and valid/ownership state; reuse of existing state bits might change incremental storage.',
                                              'Cache state must be invalidated/updated across reset, coefficient changes and dependent neuron updates.'])],
                  prior_screen_artifact=dict(path='common_adaptation_policy_results_pre_fused.json',
                      sha256=sha(P/'common_adaptation_policy_results_pre_fused.json')),
                  caveats=['No hardware, switching power, memory bandwidth or arrival-burst latency is measured here.',
                           'Avoiding general correction means only a runtime path count; area or power savings require actual sharing/removed units plus the LUT/mux/register/controller cost.',
                           'Same-clock fixed hybrid6 and LUT6 already consume every supplied six-value window in one issue.',
                           'Full signed11 and static-I8 worst cases have six exceptions/window: one shared corrector has five extra global-freeze clocks per window with the fused first correction.',
                           'The common fixed layout is a strong algebraic baseline, not evidence of adaptive DSP lane-count packing.',
                           'Certificates also depend on current I and DSP residue carry; actual U alone is insufficient.',
                           'Saved weights certify signed8 current independent of the trace, so a static current-specialized baseline is necessary before claiming runtime adaptation is uniquely beneficial.'])
    assert pins == {'contract_sha256': sha(P/'CONTRACT.md'),
                    'oracle_sha256': sha(P.parent/'check_guard_add.py'),
                    'script_sha256': sha(Path(__file__))}
    (P/'common_adaptation_policy_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    compact = {'proof': result['arithmetic_proof'], 'packed_stress': result['packed_stress'],
               'eligible_scalar_pairs': result['models']['eligible_scalar_pairs'],
               'exception_jobs_per_window': result['models']['exception_jobs_per_window'],
               'cache': result['models']['temporal_cache_diagnostic'],
               'ideal_nonoverlapped_correction_schedules': result['models']['ideal_nonoverlapped_correction_schedules'],
               'json_path': str(P/'common_adaptation_policy_results.json')}
    print(json.dumps(compact, indent=2), flush=True)


if __name__ == '__main__':
    main()
