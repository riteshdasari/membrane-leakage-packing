"""Publish the bounded, negative operand-isolation trial with evidence hashes."""
from pathlib import Path
import json
import sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import run_operand_isolation as trial


def publish():
    root = P.parents[2]
    out = root/'outputs'
    stem = out/'membrane_operand_isolation_trial'
    targets = [Path(str(stem)+s) for s in ('.md', '.summary.json', '.manifest.json')]
    assert not any(path.exists() for path in targets), 'Preserve publications'
    records = []
    allpins = trial.frozen() | trial.pins([Path(__file__)])

    def add(mapping):
        trial.verify(mapping)
        for path, digest in mapping.items():
            assert path not in allpins or allpins[path] == digest, ('Pin conflict', path)
            allpins[path] = digest

    def artifact(path):
        add(trial.pins([path]))

    # Verify the complete frozen energy evidence, not only its publication hash.
    prior_manifest = trial.read(out/'membrane_selective_energy_trial.manifest.json')
    add(prior_manifest['files'])
    total = 0
    for folder, label in ((P, 'postselection'), (P.parent/'operand_isolation_folded_trial', 'folded')):
        suites = []
        for kind in ('main', 'models'):
            for stall in (0, 1):
                wd = folder/'results'/f'native_{kind}_{stall}_a0'
                check = wd/'comparison_checks.json'
                d = trial.read(check)
                assert d['status'] == 'pass'
                assert d['matched_archived_retirement_bytes'] and d['matched_reference_retirement_bytes']
                assert d['output_controls_and_internal_service_cycle_identical']
                assert d['reset_and_backpressure_preludes_checked']
                add(d['source_sha256']); add(d['candidate_file_sha256'])
                add(trial.read(wd/'provenance.json'))
                for filename in ('comparison_checks.json', 'provenance.json'):
                    artifact(wd/filename)
                for path in wd.glob('*.job.json'):
                    job = trial.read(path)
                    assert job['returncode'] == 0
                    add(job['source_sha256']); artifact(path)
                for path in wd.glob('*.log'):
                    artifact(path)
                add({d['log_file']:d['log_sha256'],d['archived_check_file']:d['archived_check_sha256'],
                     d['archived_retirement_file']:d['archived_retirement_sha256']})
                if kind == 'models' and stall == 0:
                    t = d['trace']
                    assert t['matched_all_eighteen_columns'] and t['sha256'] == t['reference_sha256']
                    add({t['file']:t['sha256'],t['reference']:t['reference_sha256']})
                total += d['arithmetic']['neurons']
                suites.append(dict(kind=kind, backpressure=bool(stall),
                    scalar_checks=d['arithmetic']['neurons'], physical_service=d['physical_service'],
                    arithmetic_sha256=d['arithmetic']['numeric_retirement_sha256'],
                    checks_file=str(check), checks_sha256=trial.sha(check)))
        hardware = []
        for hw in sorted((folder/'results').glob('route*/hardware.json')):
            d = trial.read(hw)
            assert d['status'] == 'timing_failed' and d['WNS_ns'] < 0 and d['WHS_ns'] >= 0
            assert d['clock_period_ns'] == 6 and d['part'] == 'xc7a100tcsg324-1'
            assert d['slice_accounting']['fixture_FF'] == 219 and d['core']['DSP'] == 1
            add(d['source_sha256']); add(d['artifact_sha256']); add(d['functional_check_sha256'])
            artifact(hw)
            hardware.append({k:d[k] for k in ('status','core','WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns')}
                            | dict(directory=str(hw.parent), hardware_sha256=trial.sha(hw)))
        assert hardware
        for name in ('review_checks.json', 'review_operand_isolation.py', 'mechanism_review.md',
                     'audit_operand_isolation.py', 'audit_notes.md', 'CONTRACT.md'):
            artifact(folder/name)
        assert not any((folder/'results').glob('power_a*'))
        records.append(dict(candidate=label, native_suites=suites, hardware=hardware,
                            isolated_energy_measured=False))
    assert total == 5789660
    originals = trial.read(trial.COMMON/'results/selective_hardware.json')
    refs = {str(d['variant']):{k:d[k] for k in ('core','WNS_ns','WHS_ns')}
            for d in originals if d['variant'] in (2,3)}
    energy = trial.read(out/'membrane_selective_energy_trial.summary.json')
    summary = dict(status='complete', outcome='Exact RTL variants; both fail matched6ns timing; isolated energy unmeasured',
        repeated_scalar_checks=total, unique_source_updates_across_stress_and_models=1447415,
        candidates=records, frozen_hardware_references=refs,
        frozen_energy_reference_pJ_per_update={k:v['estimated_dynamic_energy_pJ_per_scalar_update']
                                               for k,v in energy['power_audits'].items()},
        scope='Six fixed DSP lanes with membrane/current/carry-aware exact correction, not variable lane-count packing',
        comparison='Constructed fixed and adaptive references; not FireFly RTL',
        isolated_sdf_replay_performed=False, isolated_power_estimate=None,
        decision='Do not promote either isolation candidate; retain frozen V3 as functional reference',
        limitations=['No trained-model accuracy study','No board timing/power measurement',
                     'Raw-port hold audit remains negative','Candidate-only physical optimization is not matched baseline optimization'])
    trial.write(targets[1], summary)
    report = '''**Operand isolation did not produce a timing-valid improvement in this bounded trial.** Both implementations preserved every tested result and service cycle, but neither met the original 6 ns registered timing target. No isolated energy estimate was accepted.

The smaller candidate zeros the selected membrane-high and signed adjustment operands when no valid exception requires the shared corrector. The folded candidate incorporates a zero default into one-hot lane selection. Both keep signed11 membrane, statically certified signed8 current and exact signed12 sums; the DSP still has six fixed eight-bit residue fields. This adapts correction work, not lane count or packing width.

- Frozen fixed V2: 43 LUTs, 262 FFs, one DSP; setup slack +2.141 ns, hold +0.130 ns.
- Frozen adaptive V3: 147 LUTs, 268 FFs, one DSP; setup +0.108 ns, hold +0.132 ns.
- Post-selection isolation: 152 LUTs, 268 FFs, one DSP; setup −0.230 ns, hold +0.026 ns.
- Folded isolation: 167 LUTs, 268 FFs, one DSP; setup −0.114 ns, hold +0.105 ns.
- One post-route physical optimization pass on the smaller candidate: 152 LUTs, 268 FFs, one DSP; setup −0.227 ns, hold +0.026 ns. All 538 routable nets are fully routed; routing errors are zero.

These core counts exclude the identical 219-FF registered fixture (138 launch and 81 capture FFs). Physical optimization preserved its register counts, 6 ns clock and OOC clock-source location. It was an extra candidate-only implementation pass, so it is not evidence of a comparison under equally optimized implementation flows. The original references remain immutable.

Each RTL variant passed stress and saved-model workloads, both with and without output backpressure. Across eight suites there were 5,789,660 repeated scalar checks, covering 1,447,415 unique source updates across the two workload files. All result lanes, zero tails, retirement clocks and settled output/control/service pins matched frozen V3. Both no-backpressure model traces were byte-identical to its 110,756-row, 18-column archived trace. Reset, busy cancellation and stalls were checked. Independent algebra/source review covered all 524,288 signed11/signed8 scalar pairs per variant and the relevant correction/controller cases; this is not a whole-design sequential formal proof.

The smaller candidate's original critical path runs through membrane classification, exception detection and the pipeline register-enable network. Routing contributes about 76% of its data delay. The folded candidate has a different critical path through DSP residue carry, exception selection, isolated membrane-high bits and output arithmetic, with about 82% routing contribution. Therefore reducing toggles in the small corrector does not remove the actual timing bottlenecks. The physical pass improved worst setup by only 0.003 ns.

For the saved model stream, isolation leaves the original 635,904 scalar updates, 110,592 requests, 1,008 correction steps and 114 extra service clocks unchanged. No DSP operation is skipped and no additional useful operation is packed. The previously measured whole-fixture estimates remain 18.053 pJ/update for fixed V2 and 20.997 pJ/update for adaptive V3; these are vendor estimates of the frozen designs, not measurements of either new isolated circuit. No switching-saving claim follows from a zero-default RTL expression alone.

Vivado completed the physical pass successfully. The first recording helper expected a route-completion sentence absent from this tool's report format. A separate read-only collector verified the preserved source/checkpoint hashes and job record, then proved route completeness from its numeric net counts. The physical optimization was not repeated and timing failure was not waived.

The result limits this optimization, not the broader research direction. Keep the exactness certificate and correction policy as reusable evidence. A stronger subsequent experiment must reduce classifier/scheduler cost or increase useful operations per DSP; suppressing a five-bit corrector alone has not established that benefit. Accuracy is already exact to the declared integer reference in fixed V2, so it cannot be claimed as an advantage over that comparator. These baselines are constructed primitives, not FireFly reproductions; novelty still needs a scoped prior-art review.

Routed SDF replay, SAIF collection and power estimation were intentionally not run after the 6 ns setup failures. The separate raw-port audit also has negative hold slack (about −1.075 ns for the smaller candidate); this registered OOC experiment is not a board-ready interface or board power measurement. Original trained-model accuracy and total neuron-update energy remain outside this trial.

Machine-readable checks, source hashes, job/RAM logs, checkpoints and all failed results are retained in the accompanying summary and manifest.
'''
    targets[0].write_text(report, encoding='utf-8')
    artifact(targets[0]); artifact(targets[1])
    trial.verify(allpins)
    manifest = dict(status='pass', file_sha256=dict(sorted(allpins.items())),
                    files=len(allpins), bytes=sum(Path(path).stat().st_size for path in allpins),
                    scope='Pinned trial and frozen reference evidence; this manifest excludes its own hash')
    trial.write(targets[2], manifest)
    trial.verify(manifest['file_sha256'])
    print('PUBLICATION COMPLETE', manifest['files'], 'files', manifest['bytes'], 'bytes', targets[0])


if __name__ == '__main__':
    publish()
