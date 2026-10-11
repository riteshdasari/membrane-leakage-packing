"""Close the public checkpoint stage after all original10000 tests finish."""
from pathlib import Path
import json,hashlib,time,sys,zipfile
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=ROOT/'outputs';STEM='membrane_public_model_check'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
while not(P/'full_test_results_v3.json').exists():time.sleep(3)
assert not(OUT/f'{STEM}.md').exists()
full=read(P/'full_test_results_v3.json');pilot=read(P/'original_pilot_results_v2.json')
interpret=read(P/'original_pilot_interpretation_v2.json');bounds=read(P/'static_range_screen_v3.json')
coefficient=read(P/'coefficient_scope_screen.json');data=read(P/'full_data_acceptance_v2.json')
rejected=read(P/'preview_pilot_rejection.json');framework=read(P/'framework_acquisition.json')
source=read(P/'source_acquisition.json');prior=read(OUT/'membrane_adaptive_extended_checks_v2.summary.json')
assert full['full_test']and full['samples']==10000 and full['first64_logits_bit_identical_to_observed_pilot']
assert full['minimum_sampled_free_RAM_GiB']>=1.2
assert pilot['samples']==64 and pilot['neuron_updates']==159383552 and pilot['neuron_layers']==17
assert pilot['observer_float_state_disagreements']==pilot['observer_spike_disagreements']==0
assert data['preview_pilot_rejected']and rejected['status']=='rejected_as_original_CIFAR10_benchmark'
assert interpret['membrane_only_metadata_saving_layer_unit_cases']==0 and bounds['pilot_operand_envelope_violations']==0
assert coefficient['covered_by_old_near_identity_full_width_regime']==0
assert sha(Path(framework['path']))==framework['sha256']
with zipfile.ZipFile(framework['path'])as z:
    for entry in z.infolist():
        if not entry.is_dir():assert (P/'deps'/entry.filename).read_bytes()==z.read(entry)
hardware={r['engine']:r['core']for r in prior['certified_hardware']['rows']}
summary=dict(status='complete_public_float_benchmark_with_explicit_integer_hardware_gaps',
    source=source,framework=framework,original_data=data,full_test=full,original_pilot=pilot,
    operand_screen=interpret,real_arithmetic_envelope_screen=bounds,coefficient_scope_screen=coefficient,
    rejected_preview_pilot=rejected,prior_hardware=hardware,prior_energy_comparisons=prior['energy_comparisons'],
    paper_readiness='Current adaptive addition core has no demonstrated advantage over the strongest exact fixed native hybrid. This broader public model stage does not reverse that result.',
    published_GLIF_readme_full_accuracy_percent=94.19,
    local_float_full_accuracy_difference_percentage_points=full['accuracy_percent']-94.19,
    matches_published_readme_correct_count=full['correct']==9419,
    integer_neuron_contract_declared=False,public_model_RTL_replayed=False,public_model_hardware_benefit_demonstrated=False,
    next_gate='Declare and validate an application-backed integer LIF leakage operation/coefficients, then test the existing and new exact mechanisms against strongest fixed DSP/LUT controls before another hardware trial.')
sp=OUT/f'{STEM}.summary.json';save(sp,summary)
lines=['# Public SNN model check and paper decision','',
    'The current adaptive addition core still does not establish a strong adaptive efficiency contribution. This stage adds a real public trained-model reference and numerical applicability checks; it does not claim public-model integer hardware or a FireFly accelerator reproduction.','',
    '## Executed public benchmark','',
    f"The official [GLIF repository](https://github.com/CAS-CLab/Gated-LIF) was pinned at commit `{source['commit']}`. The published ResNet18 CIFAR10 T2 channel-wise checkpoint was downloaded and verified against its Git blob, then loaded with Torch weights_only=True and strict model keys. Original model code and pinned SpikingJelly0.0.0.0.10 were used in the local Torch CPU runtime. GLIF is a learned gated LIF variant, not vanilla LIF or AdEx.",'',
    f"All10,000 original held-out CIFAR10 images were evaluated, in order, without training or changing neuron equations. Accuracy is **{full['accuracy_percent']:.2f}% ({full['correct']}/10000)**. The repository's T2 ResNet18 table reports94.19%; local difference is {summary['local_float_full_accuracy_difference_percentage_points']:+.4f} percentage points. This is floating-point reference accuracy, not packed-integer accuracy.",'',
    f"Runtime was {full['elapsed_seconds']/60:.2f} minutes using8 CPU threads and batch4. The minimum sampled free RAM was {full['minimum_sampled_free_RAM_GiB']:.2f}GiB. CPU inference speed is not a hardware-packing throughput result.",'',
    'The original test archive passed its provider-compatible SHA256 and MD5 checks. Only its test_batch member was read, using a restricted unpickler. A64-image slice was separately instrumented across17 neuron layers: **159,383,552 updates, zero observer state/spike disagreements**. The full unmodified run reproduced this original-pixel pilot\'s first64 logits bit for bit. This checks passive observation of floating arithmetic; no quantized or RTL state was fed back into this public model.','',
    '## Numerical compatibility','',
    'The pilot declared four illustrative integer-unit screens before inference. They independently round observed pre-add membrane contributions and effective currents to nearest even. They do not define an accuracy-preserving integer neuron model, safe hardware widths or full-test range statistics.','']
for row in interpret['rows']:
    lines.append(f"- {row['scale']} units per membrane unit: U8 eligibility {100*row['U8_fraction']:.6f}%; I8 eligibility {100*row['I8_fraction']:.6f}%; currents outside I8 {row['current_outside_i8']:,}/{row['updates']:,}.")
lines+=['',
    'At scale64 all observed membrane contributions fit int8, yet5,948 currents do not, across15 layers. At scale16 both operands fit in this pilot, which alone does not establish an adaptive packing benefit or a legal model-wide bound. In all68 observed layer/unit cases, U-only narrowing while retaining the globally required current width saves no high-base metadata under the current formula. A joint U/current or high-sum admission policy is a different implementation and needs its own proof and fair controls.','',
    'An independent real-arithmetic envelope screen covers all permitted image pixels and binary intermediate spikes. It indicates wider possible currents in12 of17 layers even at scale16, and all17 at finer scales. It is deliberately labeled a real-valued screen: floating rounding and a new integer neuron contract are not certified by these envelopes. No current was clipped to make the existing I8 RTL fit.','',
    'The checkpoint also has real learned leakage coefficients. None of7,808 channel/previous-spike coefficient contexts falls inside the old delta0..25 near-identity regime after illustrative nearest-Q8 mapping; none falls inside delta0..31. Coefficient231 and its old7–20% issue-slot estimate cannot be assigned to this model. No Q8 GLIF model or quantization-accuracy result is being claimed.','',
    '## Hardware conclusion preserved','',
    f"For the earlier certified integer addition domain, adaptive uses {hardware[0]['LUT']} LUT,{hardware[0]['FF']} FF,1 DSP and {hardware[0]['occupied_slices']} touched slices. The strongest fixed native FOUR12+four-LUT hybrid uses {hardware[2]['LUT']} LUT,{hardware[2]['FF']} FF,1 DSP and {hardware[2]['occupied_slices']} slices. All5 routes and6 native cohorts passed in that bounded trial; its newly specialized energy remains unmeasured.",'',
    f"For the separately measured original generic-U11 fixture, adaptive dynamic energy was {prior['energy_comparisons']['adaptive_vs_2_dynamic_percent']:.4f}% higher than the strongest fixed hybrid. That vendor fixture estimate is not public-model, newly specialized core or board energy. Fixed8's retained timed failure has no accepted energy; its later mapped-functional diagnostic passes92,186 complete trace rows and does not waive timing or energy.",'',
    'Fixed8 is already request-minimal for this eight-addition interface. New workloads can expose a resource/energy frontier or applicability gap, but cannot make an at-most8-operation controller require fewer requests than legal fixed8. Exact output preservation is required; it is not an accuracy improvement over an already exact fixed implementation.','',
    '## Data-source failure retained','',
    'The first quick pilot used dataset-viewer image URLs. They supplied lossy JPEG previews, despite local .png filenames. The original-pixel identity gate rejected183,349 of196,608 pixel entries, with maximum error95 and mean absolute error6.0583. Labels matched. All preview inference,81.25% pilot accuracy and its operand interpretation are excluded as original CIFAR10 benchmark evidence and remain retained. The original-pixel pilot and full run are separate files; no result was silently replaced.','',
    'A concurrent provider-range transport attempt reported TLS EOF and an initial recovery attempt found missing chunk23. Separate retries completed the missing data and accepted only the full original archive hashes. A first range-screen script used the wrong nested residual-module key; version3 checks the actual original-pixel pilot. The original failed sources and artifacts remain. Superseded owned wait/download jobs were stopped after verification; no user application or global Python environment was changed.','',
    '## What this work enables next','',
    'The exact decomposition, controllers, range certificates, replay harness and strong fixed controls remain reusable. This broader benchmark identifies numerical requirements for the next mechanism. It does not yet offset the current controller\'s hardware cost with a measured advantage.','',
    'The next bounded primitive trial must start from a declared integer LIF leakage operation with application-backed coefficients, independently checked float-to-integer accuracy, exact packing, actual stream statistics and strong zero-bypass/fixed-DSP/constant-LUT controls. The gates are saved in [next_operation_gate.md](../work/adaptive_snn_probe/public_model_trial/next_operation_gate.md). This can stay a small packing/controller paper; no full accelerator is required.','',
    'Vanilla directly trained LIF/event-network integer traces, public-model RTL replay, a complete AdEx integer reference, new-specialization timed energy and board measurements remain unexecuted. An inspected Lava integer MNIST tutorial uses dv=0 in its classifier layers, so it is not evidence for an intrinsic nontrivial leakage multiplication. Novelty remains qualified; no exhaustive first-ever claim or ISCAS acceptance prediction is made.']
rp=OUT/f'{STEM}.md';rp.write_text('\n'.join(lines)+'\n',encoding='utf-8')
files={}
def add(p):
    p=p.resolve();files[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
for p in P.rglob('*'):
    if p.is_file()and '__pycache__'not in p.parts:add(p)
for p in(sp,rp,OUT/'membrane_adaptive_extended_checks_v2.md',OUT/'membrane_adaptive_extended_checks_v2.summary.json',OUT/'membrane_adaptive_extended_checks_v2.manifest.json'):add(p)
save(OUT/f'{STEM}.manifest.json',dict(status='pass_public_stage_hash_closure',files=files,
    bytes=sum(x['bytes']for x in files.values()),report_sha256=sha(rp),summary_sha256=sha(sp),
    scope='All retained public-stage sources, assets, rejected previews, failures and accepted original reference results; prior bounded evidence manifest referenced separately. No live processes modify these files after complete full-test status.'))
print(json.dumps(dict(status=summary['status'],accuracy_percent=full['accuracy_percent'],files=len(files),
    current_exceptions_at_scale64=next(r['current_outside_i8']for r in interpret['rows']if r['scale']==64),
    public_integer_RTL_validated=False,paper_benefit_established=False),indent=2),flush=True)
