"""Freeze review documents and compact evidence; does not rerun experiments."""
from pathlib import Path
import hashlib,json,zipfile
P=Path(__file__).resolve().parent
W=P.parents[2]
O=W/'outputs'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((O/'membrane_leakage_final.summary.json').read_text())
assert summary['submission_ready'] is False
docs=[O/'membrane_leakage_final.md',O/'membrane_leakage_paper_draft.tex',
      O/'membrane_leakage_final.summary.json',P/'stage1_leakage_addendum.md',
      P/'stage4_lut_sdf_diagnosis.md',P/'stage4_final_integrity.json',
      P/'stage4_final_acceptance.json',P/'stage5_methods_agent.md',Path(__file__)]
files=set(docs)
for suffix in ('*.py','*.sv','*.tcl','*.md','*.json'):
    files.update(P.glob(suffix))
files.discard(P/'stage5_writeup_acceptance.json')
files.add(P/'stage3_actual_frames.txt')
files.add(P/'stage3_logits.npz')
for e in range(6):
    files.add(P/f'hardware/common9_e{e}_a0/hardware.json')
    files.add(P/f'hardware/native_actual_s0_a3/trace{e}.txt')
    files.add(P/f'hardware/golden9_e{e}_a0/golden_checks.json')
    for name in ('tool_0.log','tool_1.log','tool_2.log','tool_3.log','replay_checks.json'):
        x=P/f'hardware/replay9_e{e}_a0/{name}'
        if x.exists(): files.add(x)
    if e!=2: files.add(P/f'hardware/power9_e{e}_a0/power_audit.json')
files.update(P.glob('hardware/replay12_e2_a0/tool_*.log'))
files.add(P/'hardware/lut_functional_diagnostic_a0/diagnostic.json')
for name in ('native_actual_s0_a3','native_main_s0_a3','native_main_s1_a3'):
    files.add(P/f'hardware/{name}/acceptance.json')
record=dict(status='completed_bounded_five_stage_trial_with_retained_gap',
    stage_status={'1':'bounded novelty audit and leakage addendum saved',
                  '2':'10000-image scalar integer-neuron benchmark accepted',
                  '3':'exact algebra and64-image packed feedback accepted',
                  '4':'DSP comparison accepted; LUT timed replay failed and energy excluded',
                  '5':'report, mathematical methods, working manuscript and review bundle saved'},
    final_decision='Retain E5 for a focused adaptive leakage primitive paper; broader validation remains before a strong submission claim',
    manuscript_compile_status='success: see stage5_compile_diagnostics.json and its exact source hash',
    artifact_sha256={str(x):sha(x) for x in sorted(files)},
    bundle_scope='Compact review material only; original checkpoints, vendor runtime, full activity and public dataset remain at pinned original paths. Not a standalone reproduction image.')
manifest=O/'membrane_leakage_final.manifest.json'
manifest.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
files.add(manifest)
with zipfile.ZipFile(O/'membrane_leakage_review_bundle.zip','w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for x in sorted(files): z.write(x,x.relative_to(W).as_posix())
(P/'stage5_writeup_acceptance.json').write_text(json.dumps(dict(
    status=record['status'],documents=[str(x) for x in docs],
    submission_ready=False,reviewed_by='root and independent final_stage5_audit',
    manifest_sha256=sha(manifest),bundle_sha256=sha(O/'membrane_leakage_review_bundle.zip')),
    indent=2)+'\n')
print(json.dumps(dict(status=record['status'],files=len(files),
    bundle_bytes=(O/'membrane_leakage_review_bundle.zip').stat().st_size)),flush=True)
