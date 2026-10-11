"""Machine-readable validated activity handoff; never changes captured evidence."""
from pathlib import Path
import hashlib,json,platform,sys
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;SELECTED=HERE/'random_stratified_v2'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
r=json.loads((SELECTED/'results.json').read_text());a=json.loads((SELECTED/'acceptance.json').read_text())
g=json.loads((SELECTED/'representativeness_acceptance.json').read_text())
assert r['status']==a['status']==g['status']=='pass'
files=[SELECTED/n for n in('plan.json','results.json','acceptance.json','representativeness_acceptance.json',
          'representative_actual_frames.txt','representative_stim.txt','activity_operands.npz','activity_histograms.npz')]
out=dict(status='pass_ready_for_native_and_SDF_activity_replay',selected_directory=str(SELECTED),
    selection='Predeclared random-stratified method, fixed seed417839; midpoint capture retained as aliasing diagnostic',
    expected_issue_counts_by_engine=r['sample_issues_by_engine'],scalar_operations=r['sample_operations'],
    windows=r['sample_windows'],all64_logits_equal_integer_reference=True,exact_post_sample_outputs_checked=True,
    distribution_gate_pass=True,full_feedback_updates=r['exact_neuron_feedback_updates'],
    native_driver_compatibility=dict(max_operands400000=262528<400000,max_cycles1000000=262528+5<1000000,
        first_accept3=True,expected_unstalled_min_max_latency2=True,expected_global_trace_rows=262528+5),
    scope='Bounded actual64-image GLIF arithmetic stream after common zero filter; not complete10000-energy, vanilla LIF, board measurement, or full neuron-update energy',
    versions=dict(python=sys.version,numpy=np.__version__,torch=torch.__version__,platform=platform.platform(),
                  executable=sys.executable,inference_threads=3,interop_threads=1),
    files_sha256={str(p):sha(p)for p in files},handoff_source_sha256=sha(Path(__file__)))
(HERE/'handoff.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k]for k in('status','selected_directory','expected_issue_counts_by_engine','scalar_operations','windows','native_driver_compatibility')}),flush=True)
