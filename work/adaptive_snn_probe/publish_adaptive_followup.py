"""Save the completed continuous/quad engineering trial and evidence hashes.

Read-only toward all frozen sources and tool outputs. No tool jobs are launched.
This is an implementation/verification note, not a publication claim.
"""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

P = Path(__file__).resolve().parent
R = P / 'results'
O = P.parents[1] / 'outputs'
LABELS = ['Adaptive six-bit', 'Adaptive seven-bit', 'Fixed DSP three-lane with fourth copy',
          'Fixed DSP four-lane', 'LUT four-lane']

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    import run_quad_route as q
    import run_continuous_route as c
    quad = json.loads((R / 'quad_hardware.json').read_text())
    continuous = json.loads((R / 'continuous_hardware.json').read_text())
    assert {r['top'] for r in quad} == {'top_quad_' + n for n in q.ENGINES}
    assert len(quad) == 5 and len(continuous) == 4
    qp, cp = q.hashes(), c.hashes()
    for row in quad:
        assert row['target_ns'] == 6 and row['source_sha256'] == qp
        assert row['functional_check_sha256'] == q.functional(row['top'], qp)
    for row in continuous:
        assert row['source_sha256'] == cp
        assert row['functional_check_sha256'] == c.check_functional(row['top'], cp)
    models = json.loads((R / 'quad_models_0_checks.json').read_text())
    snn = json.loads((R / 'quad_snn_checks.json').read_text())
    checks = [json.loads((R / (n + '_checks.json')).read_text()) for n in
              ['quad_main_0', 'quad_main_1', 'quad_models_0', 'quad_models_1']]
    comparisons = sum(row['neurons'] for check in checks for row in check['rows'])
    clocks = {r['engine']: r['clocks'] for r in models['rows']}
    O.mkdir(exist_ok=True)
    lines = [
        '# Exact membrane-aware packing: continuous and four-output RTL follow-up', '',
        'This note records completed local implementation trials. The arithmetic is leakage, '
        'not synaptic accumulation: L(U)=U-floor(25U/256)=ceil(231U/256), with signed eleven-bit '
        'inputs/outputs. No membrane is rescaled or rounded.', '',
        '## Continuous three-output trial', '',
        'The adaptive controller uses DSP three-lane arithmetic for eligible actual membranes; '
        'otherwise it uses DSP two-lane arithmetic plus the LUT third lane. Both it and the fixed '
        'hybrid retire three results per request. Saved-model service is 216,580 clocks for both. '
        'This trial increases hardware without reducing service cycles.', '']
    for r in sorted(continuous, key=lambda x: x['top']):
        k = r['core']
        lines.append(f"- {r['top']}: {k['LUT']} LUT / {k['FF']} FF / {k['DSP']} DSP; "
                     f"target {r['target_ns']:g} ns; setup/hold slack {r['WNS_ns']:+.3f}/{r['WHS_ns']:+.3f} ns.")
    lines += ['', '## Matched four-output trial', '',
              'Every engine receives the same up-to-four ordered raw membranes. Adaptive and fixed '
              'three-lane engines equally copy a fourth value in [0,10], where leakage is exactly '
              'the identity. Otherwise adaptive packing chooses four lanes when every membrane '
              'fits its signed six- or seven-bit range and uses the full-range three-lane format '
              'for fallback. Fixed four-lane and LUT four-lane engines consume four whenever available.', '',
              'All five cores use the same four-advancing-clock pipeline contract and 6 ns registered '
              'out-of-context timing fixture. Counts below exclude its 103 FF. The fixture supplies '
              'windows; a real memory reader/window builder is not implemented.', '']
    for r in sorted(quad, key=lambda x: q.ENGINES[x['top'].removeprefix('top_quad_')]):
        e = q.ENGINES[r['top'].removeprefix('top_quad_')]
        k = r['core']
        closes = r['WNS_ns'] >= 0 and r['WHS_ns'] >= 0
        lines.append(f"- {LABELS[e]}: {k['LUT']} LUT / {k['FF']} FF / {k['DSP']} DSP; "
                     f"{clocks[e]:,} saved-model service clocks; setup/hold "
                     f"{r['WNS_ns']:+.3f}/{r['WHS_ns']:+.3f} ns ({'passes' if closes else 'fails'} target).")
    lines += ['',
              f"Relative to matched fixed three-lane, adaptive six-bit reduces service clocks by "
              f"{100*(1-clocks[0]/clocks[2]):.3f}%; seven-bit by {100*(1-clocks[1]/clocks[2]):.3f}%. "
              f"Seven-bit still needs {100*(clocks[1]/clocks[3]-1):.3f}% more clocks than fixed four-lane. "
              'Request savings against three lanes alone do not establish superiority over the four-lane baselines.', '',
              '## Hardware diagnosis and next screen', '',
              'The four-output adaptive leakage implementation does not establish an overall hardware '
              'benefit. Six-bit uses 302 LUTs versus fixed three-lane 141 and LUT four-lane 129. Its '
              '201 FF versus LUT four-lane 224 is a register saving, but it adds 173 LUTs and one DSP '
              'and takes more service clocks. Seven-bit uses 304 LUTs/210 FF/one DSP and fails the '
              'matched 6 ns setup target by 0.180 ns. Therefore its cycle-count reduction is not a '
              'closed-timing latency result at that target.', '',
              'The seven-bit critical path runs from raw0_reg[16] to meta1_reg[19], outside the DSP. '
              'The routed report gives 6.188 ns data-path delay and nine logic levels, including four '
              'CARRY4 stages. This is the high-part constant multiplication/pre-subtraction and '
              'metadata selection stage. Sharing arithmetic reduced duplication but left a long '
              'serial fabric path. Constant leakage is also inexpensive in the LUT baseline; the '
              'DSP computes small residual products while full-membrane correction remains in fabric.', '',
              'A separate arithmetic-only screen returns to accumulation U+I: six eight-bit guarded '
              'fields for signed seven-bit operands, otherwise four twelve-bit guarded fields for '
              'signed eleven-bit operands. The result is signed twelve-bit, so this is a different '
              'operation/domain from the leakage RTL. A guard prevents interlane carry; one sign-parity '
              'XOR per lane recovers the exact sum. It passes 4,210,688 scalar pairs and 100,490 '
              'structured/random packed additions, with zero mismatches. No RTL, timing or SNN '
              'result is claimed for this new screen. A fixed six-output DSP-four-plus-LUT-two '
              'hybrid can already match its maximum throughput; that baseline must be priced before '
              'treating this as a promising controller.', '',
              '## Verification and limits', '',
              f"The four main/model RTL runs compare {comparisons:,} neuron outputs across five engines, "
              'with zero mismatches. Coverage includes every eleven-bit scalar in structured contexts, '
              'all 65,536 signed four-bit quadruples, boundary/residue cases, random lengths, tails, '
              'source/output backpressure and reset cancellation. It is not exhaustive over all '
              'eleven-bit quadruples.', '',
              'The saved-model replay checks 635,904 leakage outputs per engine/run. RTL outputs plus '
              'Python current addition, threshold and subtractive reset reproduce states, spikes, '
              'spike counts and classifications for 144 sampled images across three saved seeds. '
              'The reference leakage was changed to beta=231/256; this does not establish preservation '
              'of original trained-model accuracy. No retraining or download occurred.', '',
              'Registered fixture timing is not board Fmax. Raw-port hold audits remain separate '
              'and do not establish a complete external interface. No memory bandwidth, closed-loop '
              'SNN RTL, host cost, full burst latency or power is measured. Arithmetic issue and mode '
              'counts do not measure useful DSP utilization or power. Constant and programmable '
              'cohorts have different clock targets and must not be mixed.', '',
              'The local LUT implementations are reconstructed operation baselines, not FireFly RTL '
              'or reproduced FireFly hardware/accuracy results.', '']
    evidence = set()
    for n in q.SOURCES + c.SOURCES + ['publish_adaptive_followup.py', 'check_continuous.py',
                                    'check_continuous_models.py', 'tb_continuous_leak.sv',
                                    'screen_guarded_accumulation.py']:
        evidence.add(P / n)
    for n in ['quad_hardware.json', 'continuous_hardware.json', 'quad_snn_checks.json',
              'quad_main_0_checks.json', 'quad_main_1_checks.json', 'quad_models_0_checks.json',
              'quad_models_1_checks.json', 'continuous_main_25_0_checks.json',
              'continuous_main_-1_1_checks.json', 'continuous_models_checks.json',
              'continuous_stress_checks.json', 'guarded_accumulation_layout_screen.json']:
        evidence.add(R / n)
    for row in quad + continuous:
        for suffix in ['route', 'synth']:
            folder = R / f"{row['top']}_{suffix}"
            if folder.exists():
                evidence.update(p for p in folder.rglob('*') if p.is_file())
    report = O / 'membrane_adaptive_packing_followup.md'
    report.write_text('\n'.join(lines), encoding='utf-8')
    evidence.add(report)
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                    source_root=str(P), report=str(report),
                    artifact_hashes={str(p.relative_to(P)) if p.is_relative_to(P) else str(p):
                                     dict(bytes=p.stat().st_size, sha256=sha(p))
                                     for p in sorted(evidence)},
                    quad_comparisons=comparisons, quad_snn_reconstruction_rows=len(snn['rows']))
    (O / 'membrane_adaptive_packing_followup.manifest.json').write_text(json.dumps(manifest, indent=2))
    assert q.hashes() == qp and c.hashes() == cp
    print('FOLLOWUP PUBLISHED', report, len(evidence), 'hashed artifacts', flush=True)

if __name__ == '__main__':
    main()
