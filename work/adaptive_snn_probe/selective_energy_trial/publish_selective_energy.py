"""Publish the frozen V2/V3 pilot after read-only arithmetic/activity audits.

No HDL or vendor tools run here. Prior publications are immutable dependencies.
"""
from pathlib import Path
import json
import re
import sys
sys.dont_write_bytecode = True
import audit_selective_energy as audit
import run_selective_energy as base
import verify_selective_native_trace as native

P = Path(__file__).resolve().parent
OUT = P.parents[2] / 'outputs'
STEM = 'membrane_selective_energy_trial'
NATIVE = P / 'results/native_models_0_a1'
REPLAYS = {2: P/'results/replay_v2_a1', 3: P/'results/replay_v3_a0'}
POWERS = {2: P/'results/annotated_power_v2_a1', 3: P/'results/annotated_power_v3_a0'}
EXPORTS = {2: P/'results/export_v2_a1', 3: P/'results/export_v3_a0'}


def link(path, label):
    return f'[{label}](<{Path(path).resolve().as_posix()}>)'


def main():
    destinations = [OUT/(STEM+suffix) for suffix in ('.md', '.summary.json', '.manifest.json')]
    assert not any(path.exists() for path in destinations), 'Preserve published attempts'
    frozen = base.frozen()
    checked = native.verify_dir(NATIVE)
    assert checked == base.read(NATIVE/'native_checks.json')
    power = {v: audit.annotation(path) for v, path in POWERS.items()}
    for v, value in power.items():
        assert value == base.read(POWERS[v]/'power_audit.json')
    fixed, adaptive = power[2], power[3]
    assert fixed['device_settings'] == adaptive['device_settings']
    assert fixed['clock_period_ns'] == adaptive['clock_period_ns'] == 6
    assert fixed['native_interval_audit']['scalar_updates'] == adaptive['native_interval_audit']['scalar_updates'] == 635904
    assert [(x['name'], x['voltage']) for x in fixed['voltage_sources']] == [(x['name'], x['voltage']) for x in adaptive['voltage_sources']]
    # With user-specified Tj, Vivado derives ambient from each design's power.
    thermal = lambda row: {k: v for k, v in row['thermal_settings'].items() if k != 'AMBIENT'}
    assert thermal(fixed) == thermal(adaptive)
    assert thermal(fixed)['USER_JUNCTION']['value'] == '25.0 (C)'
    hardware = {x['variant']: x for x in base.read(base.COMMON/'results/selective_hardware.json') if x['variant'] in (2, 3)}
    ratio = adaptive['dynamic_energy_J']/fixed['dynamic_energy_J']
    # Use coarse 1 mW report rounding as a conservative display-resolution check.
    coarse = {v: float(re.search(r'\| Dynamic \(W\)\s*\|\s*([\d.]+)', (POWERS[v]/'power.rpt').read_text())[1]) for v in (2, 3)}
    duration_ratio = adaptive['native_interval_audit']['duration_ps']/fixed['native_interval_audit']['duration_ps']
    display_bounds = [(coarse[3]-.0005)/(coarse[2]+.0005)*duration_ratio,
                      (coarse[3]+.0005)/(coarse[2]-.0005)*duration_ratio]
    assert display_bounds[0] > 1
    activity = {}
    for line in (POWERS[3]/'switching_activity.rpt').read_text().splitlines():
        if any(f'fixture/core/{name}:' in line for name in ('corrected_high[1]', 'corrected_high[2]', 'correction_step', 'bad_mask[0]')):
            name = line.split(':', 1)[0]
            activity[name] = float(re.search(r'signal rate = ([\d.eE+-]+) \(S\)', line)[1])
    assert len(activity) == 4
    jobs = {str(path): base.read(path) for directory in [NATIVE, *EXPORTS.values(), *REPLAYS.values(), *POWERS.values()]
            for path in directory.glob('*.job.json')}
    assert all(value['returncode'] == 0 for value in jobs.values())
    sources = dict(frozen)
    for v in (2, 3):
        evidence = base.read(POWERS[v]/'evidence.json')
        sources.update(evidence['source_sha256'])
        sources.update(evidence['artifact_sha256'])
        replay = base.read(REPLAYS[v]/'replay_checks.json')
        sources.update(replay['source_sha256'])
        sources.update(replay['artifact_sha256'])
        base.verify(base.read(EXPORTS[v]/'artifacts.json'))
        producer = base.read(EXPORTS[v]/'provenance.json')
        for path, pin in producer.items():
            original = Path(path)
            if base.sha(original) != pin:
                # V2 exported before adding report_operating_conditions; its
                # exact executed Tcl version was preserved before that change.
                assert v == 2 and original.name == 'selective_energy_tools.tcl'
                original = EXPORTS[v]/'export_source.tcl'
                assert base.sha(original) == pin
            sources[str(original)] = pin
    base.verify(sources)
    summary = dict(status='pass', experiment='Frozen fixed residue V2 versus adaptive shared correction V3',
        architecture_changed=False, useful_scalar_updates=635904, useful_requests=110592,
        native_exactness=checked['status'], numeric_retirement_sha256=checked['rows'][0]['numeric_retirement_sha256'],
        power_audits=power, adaptive_over_fixed_dynamic_energy_ratio=ratio,
        adaptive_dynamic_energy_increase_percent=(ratio-1)*100,
        dynamic_power_increase_percent=(adaptive['dynamic_power_W']/fixed['dynamic_power_W']-1)*100,
        service_clock_increase_percent=(110710/110596-1)*100,
        coarse_report_rounding_energy_ratio_interval=display_bounds,
        precision_scope='Display/serialization rounding only; no bound on vendor-model or physical-measurement error',
        core_resources={v: hardware[v]['core'] for v in (2, 3)},
        selected_adaptive_signal_rates_Mtransitions_per_s=activity,
        primary_conditions_equal=True, derived_ambient_C={v: power[v]['thermal_settings']['AMBIENT']['value'] for v in (2, 3)},
        measurement_scope=fixed['scope'], source_sha256=sources,
        audit_authorship='Root reviewed and executed separate read-only audit; delegated agents hit usage limits before completing an independent energy review',
        decision='No adaptive energy advantage for this frozen version on this saved workload',
        next_bounded_hypothesis='Isolate fallback-corrector operands when no correction is needed; preserve fixed layout, exactness and service contract, then measure net area/timing/energy against both frozen references')
    base.write(destinations[1], summary)
    body = f'''# Frozen fixed versus adaptive correction: routed energy pilot

The adaptive V3 implementation uses **{(ratio-1)*100:.2f}% more estimated dynamic energy per completed scalar update** than the fixed V2 implementation on the unchanged saved workload. Both preserve the declared integer outputs exactly. This pilot establishes no energy benefit for the current shared-correction design.

## Equal-work results

Vivado 2025.2; Artix7 xc7a100tcsg324-1; 6 ns clock; routed timing-netlist activity; typical process; user junction temperature 25 C. Each variant completes 110,592 ordered requests containing 635,904 scalar additions. Both use the same signed11 membrane plus certified signed8 current domain and exact signed12 result.

- Fixed V2: **{fixed['dynamic_power_W']*1000:.3f} mW**, activity duration **{fixed['native_interval_audit']['duration_ps']/1e6:.3f} us**, total dynamic energy **{fixed['dynamic_energy_J']*1e6:.6f} uJ**, **{fixed['estimated_dynamic_energy_pJ_per_scalar_update']:.5f} pJ/update**. Native service: 110,596 clocks. Core: 43 LUT / 262 FF / 1 DSP.
- Adaptive V3: **{adaptive['dynamic_power_W']*1000:.3f} mW**, activity duration **{adaptive['native_interval_audit']['duration_ps']/1e6:.3f} us**, total dynamic energy **{adaptive['dynamic_energy_J']*1e6:.6f} uJ**, **{adaptive['estimated_dynamic_energy_pJ_per_scalar_update']:.5f} pJ/update**. Native service: 110,710 clocks. Core: 147 LUT / 268 FF / 1 DSP.

The extra 114 physical clocks increase native service by {(110710/110596-1)*100:.4f}%. Most of the energy difference comes from the higher average dynamic estimate, which increases by {(adaptive['dynamic_power_W']/fixed['dynamic_power_W']-1)*100:.2f}%. Energy is calculated as dynamic watts times actual SAIF seconds divided by completed updates; unequal service durations are retained.

The estimates cover the complete registered OOC fixture, including 219 launch/capture FFs. They are neither board measurements nor core-only values. Core resource counts above exclude those FFs. Static device estimates are {fixed['device_static_W']*1000:.4f} mW for both designs and remain separate from dynamic energy. No fixture power has been subtracted using resource fractions.

## What adapts, and why correction avoidance is insufficient

The six eight-bit DSP fields and lane count remain fixed. The DSP performs unsigned seven-bit residue additions. Fixed V2 reconstructs every high part in parallel. V3 uses actual membrane high bits, current sign and residue carry to choose a cheap exact result or shared exact correction. It executes 1,008 exceptional scalar corrections, with 114 extra freeze clocks: **{(1-1008/635904)*100:.5f}% of useful scalar updates avoid that general correction**.

That fraction measures arithmetic decisions, not switching suppression. The frozen RTL has no operand isolation around the fallback corrector: the default selected lane is zero, and the selected membrane high part still feeds its combinational arithmetic while no correction is used. The classifier, lane selector and output assembly also remain active.

Mapped routed activity directly shows corrected_high[1] at **{activity['fixture/core/corrected_high[1]']:.3f} million transitions/s** and corrected_high[2] at **{activity['fixture/core/corrected_high[2]']:.3f} million transitions/s**, while correction_step is **{activity['fixture/core/correction_step']:.5f} million transitions/s**. The bad_mask[0] classifier net is **{activity['fixture/core/bad_mask[0]']:.4f} million transitions/s**. These are specific net activities, including mapped timing glitches; they do not separately quantify each block's energy or conditional idle activity. They support testing operand isolation, rather than assuming correction avoidance already gates switching.

The DSP remains active for the ordinary low-part work in both designs. Its annotated enable is near one in each run. Sharing the high corrector does not skip the DSP computation or increase packed lane capacity. In this version the adaptive decision adds 104 LUT and 6 FF relative to a small fixed high-recovery circuit; the measured energy estimate also increases.

## Exactness, timing and annotation checks

Both native traces are rechecked against Python integer U+I, archived retirement bytes, clock columns and request order. Their numeric retirement hash is identical. Gate-level replays check all 110,642 fixed trace rows and 110,756 adaptive trace rows, including the reset prelude and exceptional clocks. Slow-corner SDF backannotation succeeds; no timing-check suppression, useful-result unknowns, mismatches or SDF timing violations are accepted.

Activity starts at 401,999 ps, one picosecond before the first useful replay drive. Each interval includes all native service clocks plus the same two launch/capture settling clocks. The actual recorded duration, root-clock transition count and every scalar state-time total are audited. Clock annotation uses the identical 6 ns constraint, as Vivado requires for its clock network.

XSim emitted escaped-name wrappers around some scalar net names. A deterministic name-only repair changes 47 fixed and 154 adaptive NET tokens, preserving instance hierarchy, duration and every ordered activity value. Both original and repaired SAIF files are retained. After repair, **726/726 fixed and 856/856 adaptive physical design nets match**, with no unmatched physical design nets. The audit verifies every reported simulated alias against its SAIF state probability and transition rate. Clock aliases come from the constraint; the only default-source aliases are verified constants. No fabric toggle fallback is accepted. DSP enable and controller nets are explicitly checked.

Raw SAIF files retain 1,369 fixed and 1,458 adaptive unknown-time records in simulator internals or optimized aliases. They are not globally discarded: every physical simulated activity record is independently checked to have zero unknown/high-impedance time. Constant physical aliases are separately audited. The expected clock-annotation warning and all original logs remain in the evidence. Vivado's medium activity advisories are retained and their named signals have measured, checked activity; no values are overridden to improve power.

Exported rail currents give the numeric dynamic values above. The ordinary power report displays 1 mW increments; even using its conservative half-increment endpoints, the adaptive/fixed energy ratio lies in **[{display_bounds[0]:.4f}, {display_bounds[1]:.4f}]** and remains above one. This is a report-resolution check, not a physical error bar. Vendor-model accuracy, environmental assumptions and board measurement uncertainty are not bounded by the export's decimal precision.

Part, process, rail voltages, clock, user junction temperature, airflow, heatsink and board-model settings are equal. Under fixed user junction temperature, Vivado derives slightly different ambient temperatures: {fixed['thermal_settings']['AMBIENT']['value']} C and {adaptive['thermal_settings']['AMBIENT']['value']} C. These are derived values, not independently changed inputs. Both registered routes pass at 6 ns; archived raw-port hold budgets remain negative (-1.146 ns fixed, -1.072 ns adaptive). This pilot does not validate a production board interface or board Fmax.

All heavy jobs ran serially with RAM gates. Successful power jobs started with {jobs[str(POWERS[2]/'annotation.job.json')]['free_GiB_at_start']:.2f}/{jobs[str(POWERS[3]/'annotation.job.json')]['free_GiB_at_start']:.2f} GiB free; sampled descendant working-set sums peaked near 1.37 GiB. This sampling can double-count shared pages and is not a unique-physical-memory peak. User applications were not closed.

## Research decision and next bounded experiment

This result removes energy as the justification for the frozen V3 implementation on this workload. Accuracy cannot offset the overhead here: both implementations already match the same exact outputs. Fewer exceptional correction jobs also do not establish faster service, since fixed V2 handles all high parts in parallel.

The next small implementation hypothesis is to isolate the fallback corrector's operands whenever no correction is required, then measure whether saved switching exceeds the new gating cost without worsening timing or changing exactness/service. That optimization is not implemented or measured in this pilot. It does not alone solve the 104-LUT gap or establish variable-width DSP packing. The current contribution should be described as membrane/current/carry-aware adaptive exact correction over a fixed DSP layout.

The saved workload uses beta231 leakage and differs from original training. Equivalence is to its declared saved integer reference; this is not an original trained-model accuracy result. No FireFly RTL is reproduced. The matched I8 hybrid and LUT routes remain valid resource comparators, but their energy is unmeasured here. Backpressure energy, unfavorable workloads, burst latency and complete neuron-update energy remain unmeasured. They are needed before a broad adaptive superiority claim, and workload selection must retain unfavorable cases.

## Reproducible evidence

{link(NATIVE/'native_checks.json', 'Native checks')}; {link(REPLAYS[2]/'replay_checks.json', 'fixed timing replay')}; {link(REPLAYS[3]/'replay_checks.json', 'adaptive timing replay')}; {link(POWERS[2]/'power_audit.json', 'fixed activity/power audit')}; {link(POWERS[3]/'power_audit.json', 'adaptive activity/power audit')}; {link(P/'audit_notes.md', 'audit notes')}; {link(destinations[1], 'numeric summary')}; {link(destinations[2], 'SHA256 manifest')}.

The root reviewed and executed a separate read-only measurement audit. Delegated agents reached usage limits before completing an independent energy review; no completed agent review is claimed. Frozen architecture sources, routed checkpoints and prior publications are unchanged.

Flow references: [AMD SAIF collection](https://docs.amd.com/r/en-US/ug900-vivado-logic-simulation/Generating-SAIF-Dumping), [AMD read_saif](https://docs.amd.com/r/2025.2-English/ug835-vivado-tcl-commands/read_saif), [AMD report_power](https://docs.amd.com/r/2025.2-English/ug835-vivado-tcl-commands/report_power).
'''
    destinations[0].write_text(body, encoding='utf-8')
    files = set(Path(path) for path in sources)
    files.update(path for path in P.iterdir() if path.is_file())
    for directory in [NATIVE, *EXPORTS.values(), *REPLAYS.values(), *POWERS.values()]:
        files.update(path for path in directory.iterdir() if path.is_file())
    # Include exact saved model/reference input files in the reproducible closure.
    for name, stamp in checked['reference_hashes']['model_input_sha256'].items():
        path = base.COMMON.parent/'results'/name
        assert base.sha(path) == stamp
        files.add(path)
    files.update(destinations[:2])
    base.verify(frozen)
    hashes = base.pins(files)
    base.write(destinations[2], dict(status='pass', file_count=len(hashes),
        bytes=sum(Path(path).stat().st_size for path in hashes), files=hashes,
        manifest_scope='Reproducible successful pilot evidence, executed source versions, frozen references and report; compiled vendor snapshots and failed-attempt logs remain on disk outside this result closure',
        comparison='Equal completed scalar work; whole-fixture vendor-estimated dynamic energy'))
    print(json.dumps(dict(status='published', report=str(destinations[0]),
        file_count=len(hashes), adaptive_energy_increase_percent=(ratio-1)*100), indent=2))


if __name__ == '__main__':
    main()
