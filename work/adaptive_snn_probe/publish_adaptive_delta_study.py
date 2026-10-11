"""Publish reproducible unit-level evidence, with no accelerator/novelty inflation."""
from pathlib import Path
import json,hashlib,zipfile,math
P=Path(__file__).resolve().parent;R=P/'results';O=P.parents[1]/'outputs'
def read(n):return json.loads((R/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={n:sha(P/n)for n in ['adaptive_delta_leak.sv','tb_adaptive_delta_leak.sv','adaptive_delta_compact.sv','tb_adaptive_delta_compact.sv']}
checks={}
for variant in ['adaptive_delta','adaptive_delta_compact']:
 for kind in ['main','model','stress']:
  c=read(f'{variant}_{kind}_checks.json')
  src='adaptive_delta_leak'if variant=='adaptive_delta'else'adaptive_delta_compact'
  assert c['source_hashes']=={n:hashes[n]for n in [src+'.sv','tb_'+src+'.sv']}
  assert len(c['rows'])==(18 if kind=='main'else 5)
  assert all(r['mismatches']==0 for r in c['rows'])
  if kind=='model':assert all(r['state_mismatches']==r['spike_mismatches']==0 for r in c['rows'])
  checks[f'{variant}_{kind}']=c
hardware=read('adaptive_delta_hardware.json');compact=read('adaptive_delta_compact_hardware.json')
assert len(hardware)==9 and len(compact)==4
assert all(h['rtl_sha256']==hashes['adaptive_delta_leak.sv']for h in hardware)
assert all(h['rtl_sha256']==hashes['adaptive_delta_compact.sv']for h in compact)
tops={h['top']:h for h in hardware+compact}
boundary=read('adaptive_delta_boundary.json');assert len(boundary['rows'])==len(tops)
bound={r['top']:r for r in boundary['rows']};assert set(bound)==set(tops)
profile=read('adaptive_delta_profile.json');assert len(profile['rows'])==18
bounds=read('adaptive_delta_model_bounds.json');assert bounds['failures']==0 and len(bounds['rows'])==18
bandwidth=read('adaptive_delta_bandwidth.json');fixed3=read('fixed_three_delta_algebra.json');assert fixed3['failures']==0
offset=read('shared_offset_delta_screen.json');assert offset['arithmetic_failures']==0
zero_pairs=read('adaptive_delta_zero_pair_audit.json');assert len(zero_pairs['rows'])==18
models=checks['adaptive_delta_compact_model']['rows'];ad=next(r for r in models if r['engine']==0);fx=next(r for r in models if r['engine']==1);lu6=next(r for r in models if r['engine']==3)
sample_saving=1-ad['cycles']/fx['cycles']
assert zero_pairs['sample']['tested_fixed_cycles']==fx['cycles'] and zero_pairs['sample']['tested_adaptive_cycles']==ad['cycles']
comparisons=[]
for version,pre in [('initial','top_delta_'),('compact','top_delta_compact_')]:
 for coef in ['const','prog']:
  a=tops[pre+'adapt_'+coef];f=tops[pre+'fixed_'+coef]
  comparisons.append(dict(version=version,coefficient=coef,extra_LUT=a['LUT']-f['LUT'],extra_FF=a['FF']-f['FF'],
   internal_period_ratio=a['internal_period_estimate_ns']/f['internal_period_estimate_ns'],
   internal_timing_times_sample_cycles_ratio=ad['cycles']*a['internal_period_estimate_ns']/(fx['cycles']*f['internal_period_estimate_ns']),
   boundary_period_ratio=bound[a['top']]['period_estimate_with_boundary_budget_ns']/bound[f['top']]['period_estimate_with_boundary_budget_ns'],
   caveat='Timing-times-cycle ratios are OOC diagnostics, not measured latency. Programmable comparison uses delta25 model cycles.'))
best_comparisons=[]
for coef in ['const','prog']:
 f=min([tops['top_delta_fixed_'+coef],tops['top_delta_compact_fixed_'+coef]],key=lambda h:h['internal_period_estimate_ns'])
 a=tops['top_delta_compact_adapt_'+coef]
 best_comparisons.append(dict(coefficient=coef,best_fixed_top_by_internal_period=f['top'],compact_adaptive_top=a['top'],
  internal_timing_times_sample_cycles_ratio=ad['cycles']*a['internal_period_estimate_ns']/(fx['cycles']*f['internal_period_estimate_ns'])))
counts=dict(rtl_engine_configuration_runs=sum(len(c['rows'])for c in checks.values()),
 rtl_six_neuron_group_checks=sum(r['groups']for c in checks.values()for r in c['rows']),
 model_trace_groups_per_implementation=ad['groups'],model_replayed_images=144,
 routed_cores=len(tops),mismatches=0,sample_leakage_group_cycle_saving=sample_saving,
 complete_group_cycle_saving_range=[min(r['complete_group_cycle_saving']for r in profile['rows']),max(r['complete_group_cycle_saving']for r in profile['rows'])],
 whole_update_proxy_saving_range=[min(r['total_update_proxy_saving']for r in profile['rows']),max(r['total_update_proxy_saving']for r in profile['rows'])])
limitations=['Leakage-only unit; synaptic accumulation and threshold/reset are software in model replay',
 'Six int11 values transferred atomically to/from a register bank; no implemented BRAM/DRAM operand interface',
 'No intergroup overlap; interface/scheduler/pipeline/state costs included for this unit',
 'Individual zero pairs and padded tail pairs are not skipped by the tested RTL; a stronger zero-pair baseline is screened analytically only',
 'Shared delta in [0,31]; per-neuron coefficient regrouping is not implemented',
 'Beta231 changes saved model dynamics; no retraining, and no equivalence claim to the models at their original beta',
 'Actual RTL model replay covers first48 held-out images per seed; whole360-image profiles are numerical',
 'Boundary timing assumes 1ns max and0.1ns min external delays; OOC port segments remain partially unrouted, so boundary paths are estimates, not timing closure',
 'Fabric FF counts exclude DSP/BRAM internal registers; no power, host-speed or FireFly implementation comparison',
 'Fixed three-wide residue packing is arithmetic-only, not routed; two lanes is not an absolute full-range packing bound']
summary=dict(source_hashes=hashes,metrics=counts,comparisons=comparisons,best_fixed_comparisons=best_comparisons,hardware=hardware,compact_hardware=compact,
 boundary_timing=boundary,checks=checks,model_profile=profile,range_certificates=bounds,bandwidth_scenarios=bandwidth,
 fixed_three_algebra=fixed3,next_shared_offset_screen=offset,zero_pair_schedule_audit=zero_pairs,limitations=limitations)
(O/'adaptive_leakage_summary.json').write_text(json.dumps(summary,indent=2))
def item(h):
 b=bound[h['top']]
 return f"- **{h['top']}:** {h['LUT']} LUTs, {h['FF']} fabric FFs, {h['DSP']} DSP, {h['RAMB18']} RAMB18, {h['RAMB36']} RAMB36; internal setup slack {h['WNS_ns']:+.3f} ns, hold {h['WHS_ns']:+.3f} ns; internal period estimate {h['internal_period_estimate_ns']:.3f} ns. With the declared external-delay budget: setup {b['WNS_ns']:+.3f} ns, hold {b['WHS_ns']:+.3f} ns."
hwlines='\n'.join(item(h)for h in hardware+compact)
comp_lines='\n'.join(f"- **{c['version']}, {c['coefficient']}:** adaptation adds {c['extra_LUT']} LUTs and {c['extra_FF']} fabric FFs; internal period is {c['internal_period_ratio']:.3f} times the matched fixed DSP period. Internal timing multiplied by sampled trace cycles is {c['internal_timing_times_sample_cycles_ratio']:.3f} times fixed (diagnostic, not board latency)."for c in comparisons)
best_lines='\n'.join(f"- **{c['coefficient']}, compact adaptive versus {c['best_fixed_top_by_internal_period']}:** internal timing multiplied by sampled trace cycles is {c['internal_timing_times_sample_cycles_ratio']:.3f} times fixed. This selects the faster of both tested fixed DSP versions, rather than requiring the reference to use an unfavorable repair."for c in best_comparisons)
model_lines=[]
for a,f in zip(ad['model_rows'],fx['model_rows']):
 assert a['seed']==f['seed']
 model_lines.append(f"- Seed {a['seed']}, first48 images: adaptive {a['trace_group_cycles']:,} clocks versus fixed {f['trace_group_cycles']:,}; leakage-unit saving {100*(1-a['trace_group_cycles']/f['trace_group_cycles']):.2f}%; reference and reconstructed classification {100*a['accuracy']:.2f}%; exact spike counts matched.")
stress=checks['adaptive_delta_compact_stress']['rows'];sa=next(r for r in stress if r['engine']==0);sf=next(r for r in stress if r['engine']==1)
stress_lines='\n'.join(f"- {'Hard'if a['hard_reset']else'Subtractive'} reset, 320 sparse/burst steps: adaptive {a['cycles']} leakage clocks, fixed {f['cycles']}; saving {100*(1-a['cycles']/f['cycles']):.2f}%."for a,f in zip(sa['stress_rows'],sf['stress_rows']))
report=f'''# Membrane-aware adaptive leakage packing: completed RTL trial

The exact three-versus-two mechanism and a targeted retiming repair are implemented and tested. The best tested constant adaptive version uses 278 LUTs versus 176 for the retimed fixed DSP version, with a longer internal critical path. Its {100*sample_saving:.2f}% sampled complete-unit cycle saving does not offset the timing penalty. This trial therefore demonstrates exactness, but **does not demonstrate a hardware benefit over the tested fixed DSP and LUT alternatives**.

## What was tested

The implemented unit reads six signed11-bit membranes, computes exact integer leakage, and returns all six results. It chooses two three-neuron DSP issues when all six actual membranes fit [-16,15], otherwise three two-neuron full-range issues. Selection is causal and computed from the supplied membrane values, rather than a spike-rate estimate. Both adaptive and fixed units bypass all-zero groups and delta0 identity leakage.

The contract is U_leak=ceil((256-delta)*U/256)=U-floor(delta*U/256), shared delta in [0,31]. Constant delta25 means beta231. Programmable delta may change between accepted groups. The unit contains the raw membrane bank, range monitor, operand multiplexers, DSP encoding, exact corrections, metadata pipeline, output bank and ready/valid scheduler. No packing is delegated to a host. This remains a leakage primitive, not a full SNN accelerator.

## Exactness and safety

There are {counts['rtl_engine_configuration_runs']} engine/configuration runs and {counts['rtl_six_neuron_group_checks']:,} checked six-neuron group outputs across the original and retimed implementations, including repeated requests across reference engines. All match the independent scalar integer oracle. Tests cover every signed11-bit scalar value at every allowed delta, all int5 triples at delta25, random wider groups, format transitions, zero/identity bypass, input bubbles, and cancellation by reset. Both pipeline options are simulated. The previously completed arithmetic audit covers all1,048,576 int5-triple/delta combinations; it is not confused with an exhaustive whole-controller proof.

The model replay covers {ad['groups']:,} groups, every neuron including padded tails, first48 held-out images from each of three saved seeds and32 timesteps. Leakage runs in RTL; current integration, threshold/reset and classification are reconstructed in Python. Reconstructed states, output spikes and spike counts match exactly. This establishes the tested integer trajectory equality, not full-network FPGA execution.

Beta231 modifies the dynamics of the saved models, whose original beta was a shift/identity case. We do not claim unchanged accuracy relative to those original models, and we did not retrain. Accuracy equality here is between scalar beta231 and the RTL-assisted beta231 replay.

For all nine saved threshold/weight configurations, an inductive bound was checked at beta231. If N is the sum of negative-weight magnitudes and P the sum of positive weights for a neuron, choose L=-ceil(256*N/25) and H=max(theta-1,ceil(256*max(P-theta,0)/25)). Monotonic leakage gives leak(L)-N>=L and max(theta-1,leak(H)+P-theta)<=H. Initialization lies in the interval. Every allowed binary input prefix stays in the checked11-bit range, including hard or one subtractive reset per timestep. This is an arithmetic range certificate for these coefficients and weights, not formal RTL verification or a bound for arbitrary SNNs.

## Measured cycles, rather than issue counts alone

With the registered multiplier enabled, the unit needs five clocks of service per nonzero narrow group and six per nonzero wider group, including accepting the group and producing its result. It uses four clocks for six parallel LUT lanes. A zero or identity group needs one clock. From the input-accept edge, corresponding result latencies are four, five, three and zero clocks. No intergroup overlap is implemented.

Across the sampled three-model replay, adaptive leakage takes **{ad['cycles']:,} clocks versus {fx['cycles']:,}** for fixed DSP packing: **{100*sample_saving:.2f}% fewer complete-unit clocks**. The six-parallel LUT core takes {lu6['cycles']:,} clocks on exactly the same groups.

{chr(10).join(model_lines)}

The complete360-image numerical profiles, all nine saved configurations and both reset policies, count every neuron and give {100*counts['complete_group_cycle_saving_range'][0]:.2f}-{100*counts['complete_group_cycle_saving_range'][1]:.2f}% complete-group clock savings. These profiles apply the RTL-validated service equation; they are not360-image RTL runs. Adding a common paired-event addition and threshold/reset schedule reduces the opportunity to {100*counts['whole_update_proxy_saving_range'][0]:.2f}-{100*counts['whole_update_proxy_saving_range'][1]:.2f}% in that declared total-update proxy. The rest of the neuron datapath has not been routed, so this is not measured full-neuron latency.

The six-lane interface includes zero padding: 128 hidden neurons leave four padded lanes in the final group, and 10 output neurons leave two. Both tested cores bypass only completely zero groups. An additional optimistic fixed schedule that skips individual zero pairs reduces sampled fixed service from {fx['cycles']:,} to {zero_pairs['sample']['zero_pair_fixed_cycles']:,} clocks; the tested adaptive core's remaining saving would be {100*zero_pairs['sample']['tested_adaptive_saving_vs_optimistic_zero_pair_fixed']:.2f}%. Across the 18 full numerical profiles, that comparison ranges from {100*min(r['tested_adaptive_saving_vs_optimistic_zero_pair_fixed']for r in zero_pairs['rows']):.2f}% to {100*max(r['tested_adaptive_saving_vs_optimistic_zero_pair_fixed']for r in zero_pairs['rows']):.2f}% (negative means the current adaptive schedule takes more clocks). Pair-skipping control, output bypass and timing are not implemented, so these are analytic schedule estimates rather than measured stronger RTL results. An optimistic adaptive schedule that also skips zero triples and chooses the cheaper eligible format would save {100*zero_pairs['sample']['optimistic_zero_skip_adaptive_saving']:.2f}% versus that sparse fixed schedule. This audit makes explicit why padded-group savings are not sufficient evidence against every strong fixed implementation.

{stress_lines}

Bursts generally make the membranes wide. The adaptive unit then performs the same three issues as fixed packing, so this mechanism does not provide an inherent worst-case burst-latency reduction. Average leakage issue savings should not be advertised as burst acceleration.

## Hardware and the targeted repair

Vivado2025.2, Artix-7 xc7a100tcsg324-1, single-thread out-of-context placement/routing, common4ns target. Initial and compact sources and all report files are preserved. The compact variant moves the exact high correction into the stage before final result extraction, narrows the residue-floor and int5 arithmetic, retains only required third-lane bits, and expresses the output selection as fixed cases. No additional service cycle is added. Full oracle, model and burst tests pass after the change.

{comp_lines}

{best_lines}

{hwlines}

LUT and FF counts include state and control for this six-neuron unit. The prototype retains separate input and output banks; in-place bank reuse was not tested. Therefore these costs are for the measured architecture, not a lower bound on adaptive packing hardware. Fabric FF excludes DSP/BRAM internal registers. One RAMB36 is not interchangeable with zero memory resources. The six-parallel LUT baseline spends more parallel arithmetic/registers to reduce service clocks; its resource and latency tradeoff is included rather than comparing only identical issue counts.

Internal period estimates are4ns minus setup slack, not achieved operating frequencies. The separate boundary audit applies1ns maximum and0.1ns minimum input/output delays to the same routed netlists, including the raw-U range monitor input path. OOC port segments remain partially unrouted: these boundary results estimate the logical path under a declared interface budget and do not certify monitor/interface timing closure or board timing. Any negative hold slack in those audits must be fixed independently of changing clock period. No power, energy or host-speed results were measured.

## Memory bandwidth and another fixed-format possibility

The implemented interface transfers66 bits atomically each way using registers. The bandwidth screen separately adds serialized state transfers and also evaluates an ideal overlapped issue pipeline. With only two state reads and writes per clock, both three-lane and two-lane issue pipelines require at least three memory clocks per six-neuron group. Additional buffering/ports would be needed to realize the issue-only lane advantage. These scenarios are analytic, not synthesized RAM wrappers; total memory bandwidth is not a measured accelerator result.

We also checked a stronger fixed-format possibility: U=32*h+r with signed int5 residue r. Three residue products fit the same DSP layout even for full int11 U, and exact leakage is U-floor((32*delta*h+delta*r)/256). All {fixed3['cases']:,} arithmetic checks pass. Its wider high correction is not simulated/routed in this trial. Consequently, two full-range lanes is our measured fixed baseline, **not an absolute three-wide packing impossibility**. Any eventual positive adaptive claim must also assess this fixed three-wide resource tradeoff.

## Interpretation and scope

The adaptation is legitimately membrane-aware and its integer output preservation is supported by these tests. A small issue saving alone does not establish a useful hardware improvement. Assess the compact results against the matched fixed DSP, factored LUT and table alternatives, using both complete service clocks and the timing/resource costs above. This study supplies a tested mechanism and a targeted repair; it does not establish a publication-strength win or a first-ever novelty claim.

A specific remaining architectural hypothesis is an ordered input-window interface that accepts the next two or three membranes and continues issuing across groups, instead of copying and draining a six-neuron output bank each time. That could amortize startup/drain and reduce result selection. It would require sufficient state-read/write bandwidth and aligned per-request format/coefficient metadata. It is not implemented here and should be tested against an equally streaming fixed reference; these results do not prove that all membrane-aware packing implementations are poor.

## A checked next arithmetic hypothesis: exact shared offsets

Absolute magnitude need not determine eligibility. A triple such as [-300,-292,-289] can share base -320 and unsigned5-bit residues [20,28,31]. No bits are discarded. For a triple that either fits the original signed int5 interval or has equal upper bits U//32, choose base b=-16 in the first case, otherwise b=32*(U0//32). Write U=b+r, 0<=r<32. The same one DSP can pack three delta*r products. A shared exact high correction reconstructs floor(delta*U/256).

Because b is a multiple of16, let z=delta*(b/16), q=floor(z/16), s=z mod16. For packed product p_i=delta*r_i, the floor is q+(p_i>>8)+carry, where carry=(((p_i>>4)&15)+s)>>4. Only a4-bit carry calculation is required per lane beyond the shared high term. All {offset['arithmetic_cases']:,} arithmetic checks pass; this new controller and decoder have **not** been built, simulated or routed.

The combined eligibility screen increases the ideal issue-saving range on the same18 numerical model profiles from {100*min(r['original_ideal_issue_saving']for r in offset['rows']):.2f}-{100*max(r['original_ideal_issue_saving']for r in offset['rows']):.2f}% to {100*min(r['combined_ideal_issue_saving']for r in offset['rows']):.2f}-{100*max(r['combined_ideal_issue_saving']for r in offset['rows']):.2f}%. In the two synthetic burst streams, ideal issue savings rise from {100*min(r['original_ideal_issue_saving']for r in offset['stress']):.2f}-{100*max(r['original_ideal_issue_saving']for r in offset['stress']):.2f}% to {100*min(r['combined_ideal_issue_saving']for r in offset['stress']):.2f}-{100*max(r['combined_ideal_issue_saving']for r in offset['stress']):.2f}%. The early synthetic bursts have identical lanes and therefore favor shared offsets. These numbers are numerical opportunities, not hardware speedups or evidence of natural-model burst acceleration.

This is a concrete next test for retaining packing when membrane values grow together. Its shared correction/monitor costs, equally streaming fixed baselines, and fixed three-full-range correction alternative must be included before claiming a gain. No novelty claim is established for shared-offset arithmetic.

FireFly is related work, not a reproduced baseline here. It uses DSP48E2 synaptic crossbars on different hardware; our unit uses DSP48E1 leakage multiplication. No claim of beating its accuracy, latency, TOPS, host costs or accelerator utilization follows from these results. [DSP-Packing](https://arxiv.org/html/2203.11028) already covers SNN addition packing and generic corrections, while [XtraMAC](https://arxiv.org/html/2605.06052) includes runtime datatype switching. The potential distinction remains an efficient actual-membrane-driven policy with demonstrated benefits, rather than packed arithmetic by itself.

## Evidence

The paired summary, source hashes, simulation stimuli/outputs, scalar checks, saved-model files, range certificates, route checkpoints/reports, initial tool-failure logs where retained, and boundary checks are packaged alongside this report. The original external research folder was not modified. No datasets, models or packages were downloaded.
'''
for old,new in [('signed11-bit','signed 11-bit'),('checked11-bit','checked 11-bit'),
                ('delta0','delta = 0'),('delta25','delta = 25'),('beta231','beta = 231'),
                ('Beta231','Beta = 231'),('all1,048,576','all 1,048,576'),
                ('first48','first 48'),('and32 timesteps','and 32 timesteps'),
                ('complete360-image','complete 360-image'),('not360-image','not 360-image'),
                ('Vivado2025.2','Vivado 2025.2'),('common4ns','common 4 ns'),
                ('are4ns','are 4 ns'),('applies1ns','applies 1 ns'),
                ('and0.1ns','and 0.1 ns'),('transfers66 bits','transfers 66 bits'),
                ('unsigned5-bit','unsigned 5-bit'),('a4-bit','a 4-bit'),
                ('same18','same 18'),('multiple of16','multiple of 16')]:
 report=report.replace(old,new)
(O/'adaptive_leakage_trial.md').write_text(report,encoding='utf-8')
# Include reproducibility inputs/results, omitting generated simulator object trees.
files=set()
names=['adaptive_delta_leak.sv','tb_adaptive_delta_leak.sv','adaptive_delta_compact.sv','tb_adaptive_delta_compact.sv',
 'check_adaptive_delta_leak.py','check_adaptive_delta_compact.py','check_adaptive_delta_trace.py','check_adaptive_delta_compact_trace.py',
 'route_adaptive_delta_leak.tcl','route_adaptive_delta_compact.tcl','route_neuron_alu_resume.tcl',
 'run_adaptive_delta_route.py','run_adaptive_delta_compact_route.py','make_adaptive_delta_compact.py',
 'prepare_adaptive_delta_model.py','audit_adaptive_delta_bounds.py','audit_fixed_three_delta.py','analyze_delta_bandwidth.py','screen_shared_offset_delta.py',
 'audit_delta_boundary.py','audit_delta_boundary.tcl','audit_delta_zero_pairs.py','finish_adaptive_delta_routes.py','publish_adaptive_delta_study.py','check_delta_packing.py']
files.update(P/n for n in names if (P/n).exists())
files.update(R.glob('adaptive_delta*.json'));files.update([R/'fixed_three_delta_algebra.json',R/'delta_packing_algebra.json',R/'final_selected.json',R/'shared_offset_delta_screen.json'])
files.update(R.glob('model_seed*.npz'));files.update(R.glob('delta_boundary*.*'))
for h in hardware+compact:
 for folder in [R/f"{h['top']}_route",R/f"{h['top']}_synth"]:files.update(p for p in folder.iterdir()if p.is_file())
 files.update(R.glob(h['top']+'_*build.log'));files.update(R.glob(h['top']+'_*vivado.log'));files.update(R.glob(h['top']+'_*vivado.jou'))
for folder in R.glob('adaptive_delta*'):
 if folder.is_dir()and ('_main_'in folder.name or '_model_'in folder.name or '_stress_'in folder.name):
  files.update(p for p in folder.iterdir()if p.is_file()and (p.suffix in ['.txt','.npz']or p.name.startswith('tool_')))
files.update([O/'adaptive_leakage_trial.md',O/'adaptive_leakage_summary.json'])
entries=[]
for f in sorted(files):
 arc='outputs/'+f.name if f.parent==O else str(f.relative_to(P)).replace('\\','/')
 entries.append(dict(path=arc,bytes=f.stat().st_size,sha256=sha(f)))
manifest=dict(source_hashes=hashes,files=entries,metrics=counts)
(O/'adaptive_leakage_manifest.json').write_text(json.dumps(manifest,indent=2))
archive=O/'adaptive_leakage_evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
 for f,e in zip(sorted(files),entries):z.write(f,e['path'])
 z.write(O/'adaptive_leakage_manifest.json','outputs/adaptive_leakage_manifest.json')
with zipfile.ZipFile(archive)as z:
 assert z.testzip()is None
 for e in entries:assert hashlib.sha256(z.read(e['path'])).hexdigest()==e['sha256']
print(json.dumps(dict(metrics=counts,comparisons=comparisons,evidence_files=len(entries),zip_bytes=archive.stat().st_size),indent=2),flush=True)
