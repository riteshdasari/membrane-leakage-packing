"""Publish completed RTL repairs, exact tests, baselines and routed evidence."""
from pathlib import Path
import json,hashlib,zipfile,re
P=Path(__file__).resolve().parent;R=P/'results';O=P.parents[1]/'outputs'
def read(n):return json.loads((R/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
variants=['compact','unsigned','fold','fold_shared'];checks={};sources={};hardware=[]
for v in variants:
 names=[f'stream_{v}_leak.sv',f'tb_stream_{v}_leak.sv'];stamp={n:sha(P/n)for n in names};sources.update(stamp)
 for part in ['main_25_0','main_-1_1','models','stress']:
  key=f'stream_{v}_{part}';c=read(key+'_checks.json');assert c['source_hashes']==stamp
  assert len(c['rows'])==7 and all(r['mismatches']==0 for r in c['rows'])
  if part=='models':assert all(r['state_mismatches']==r['spike_mismatches']==0 for r in c['rows'])
  checks[key]=c
 rows=read(f'stream_{v}_hardware.json');assert len(rows)=={'compact':5,'unsigned':6,'fold':5,'fold_shared':2}[v]
 assert all(h['rtl_sha256']==stamp[names[0]]for h in rows);hardware+=rows
old=read('stream_offset_hardware.json');old_sha=sha(P/'stream_offset_leak.sv')
assert all(h['rtl_sha256']==old_sha for h in old)
refs=[h for h in old if h['top']in ['top_stream_fixed2_const','top_stream_fixed3_const','top_stream_lut3_const',
 'top_stream_fixed2_prog','top_stream_fixed3_prog','top_stream_lut3_prog','top_stream_absolute_const','top_stream_offset_const']]
for h in hardware+refs:
 util=(R/f"{h['top']}_route"/'util.rpt').read_text()
 m=re.search(r'\|\s*Slice\s*\|\s*(\d+)',util);assert m
 h['occupied_slices']=int(m[1])
tops={h['top']:h for h in hardware+refs};models={v:{r['engine']:r for r in checks[f'stream_{v}_models']['rows']}for v in variants}
labels={0:'adaptive7/6 or shared-offset',1:'fixed DSP pair',2:'LUT pair',3:'LUT triple',4:'fixed DSP triple',5:'fixed DSP/LUT hybrid',6:'adaptive narrow only'}
counts=dict(routed_new_cores=len(hardware),rtl_engine_configuration_runs=sum(len(c['rows'])for c in checks.values()),
 neuron_output_comparisons=sum(r['neurons']for c in checks.values()for r in c['rows']),
 request_output_comparisons=sum(r['requests']for c in checks.values()for r in c['rows']),model_images=144,
 model_neurons_per_engine=models['fold'][0]['neurons'],mismatches=0)
screens={n:read(n+'.json')for n in ['stream_compact_arithmetic_screen','stream_unsigned_arithmetic_screen','fraction_fold_screen','fold_shared_screen']}
comparisons=[]
adaptives=[('compact',6,'absolute'),('unsigned',6,'absolute'),('fold',0,'offset'),('fold',6,'absolute'),('fold_shared',0,'offset'),('fold_shared',6,'absolute')]
for v,e,name in adaptives:
 for coef in ['const','prog']:
  top=f'top_stream_{v}_{name}_{coef}'
  if top not in tops:continue
  a=tops[top];ac=models[v][e]['clocks']
  bnames=[('old_fixed2',f'top_stream_fixed2_{coef}',1),('unsigned_fixed2',f'top_stream_unsigned_fixed2_{coef}',1),
   ('unsigned_hybrid',f'top_stream_unsigned_hybrid_{coef}',5),('centered_hybrid',f'top_stream_compact_hybrid_{coef}',5),('LUT3',f'top_stream_lut3_{coef}',3),
   ('fixed_DSP3',('top_stream_fold_fixed3_const'if coef=='const'else'top_stream_fixed3_prog'),4)]
  for label,bt,be in bnames:
   b=tops[bt];bc=models['fold'][be]['clocks']
   comparisons.append(dict(adaptive=top,baseline=bt,baseline_label=label,
    adaptive_clocks=ac,baseline_clocks=bc,cycle_saving=1-ac/bc,LUT_difference=a['LUT']-b['LUT'],
    FF_difference=a['FF']-b['FF'],DSP_difference=a['DSP']-b['DSP'],slice_difference=a['occupied_slices']-b['occupied_slices'],
    slice_clock_product_ratio=a['occupied_slices']*ac/(b['occupied_slices']*bc),
    LUT_clock_product_ratio=a['LUT']*ac/(b['LUT']*bc),
    internal_timing_times_clocks_ratio=a['internal_period_estimate_ns']*ac/(b['internal_period_estimate_ns']*bc),
    boundary_timing_times_clocks_ratio=a['boundary_period_estimate_ns']*ac/(b['boundary_period_estimate_ns']*bc),
    note='LUT-clock product is a declared LUT-only proxy at a common clock, not total area, energy or measured latency. Timing-times-clock quantities are OOC diagnostics, not certified Fmax.'))
limits=['Leakage primitive only; synaptic current, threshold, subtractive reset and classification reconstructed in Python',
 'No memory-to-memory engine: source lookahead, pointer advance, bank rotation, state RAM and variable-count writeback are not routed',
 'Three-read/write bandwidth is needed for three neurons per clock. Two-read/write state ports cap all variants at two updates per clock',
 'Shared Q8 coefficient, delta0..31; per-neuron coefficient regrouping and larger coefficients excluded',
 'Beta231 reference changes the saved trained model coefficients; output preservation is against that declared scalar reference',
 'Only first48 held-out images of each of three saved seeds, not a full360-image RTL or newly trained/model-download run',
 'Internal setup excludes raw input arithmetic. Boundary constraints1ns max/0.1ns min are applied after routing; port/clock-source assumptions are estimates',
 'All boundary hold results are negative. No registered launch/capture timing fixture, system timing closure, board, power, energy or host measurement',
 'Programmable hardware uses the same delta25 model replay for schedule comparison, not a different variable-coefficient SNN',
 'Occupied slices are from one placement per design; they can vary with placement and constraints. Slice counts do not include a DSP-to-fabric area conversion',
 'No FireFly reproduction or accelerator-level comparison; novelty absence has not been proved']
summary=dict(source_hashes=sources,metrics=counts,checks=checks,hardware=hardware,reference_hardware=refs,
 comparisons=comparisons,arithmetic_screens=screens,limitations=limits)
(O/'adaptive_leakage_repairs_summary.json').write_text(json.dumps(summary,indent=2))
def hwline(h):
 return f"- **{h['top']}:** {h['LUT']} LUT, {h['FF']} fabric FF, {h['occupied_slices']} occupied slices, {h['DSP']} DSP; internal setup/hold {h['WNS_ns']:+.3f}/{h['WHS_ns']:+.3f} ns, internal period diagnostic {h['internal_period_estimate_ns']:.3f} ns; boundary setup/hold {h['boundary_WNS_ns']:+.3f}/{h['boundary_WHS_ns']:+.3f} ns."
def model_line(v,e):
 r=models[v][e];return f"- **{v}, E{e} ({labels[e]}):** {r['requests']:,} requests, {r['clocks']:,} continuous clocks, {r['narrow_requests']:,} narrow requests, {r['arithmetic_issues']:,} arithmetic issues."
a=models['fold'][0];a6=models['fold'][6];a5=models['unsigned'][6];pair=models['fold'][1];triple=models['fold'][3]
oldabs=tops['top_stream_absolute_const'];newabs=tops['top_stream_compact_absolute_const']
comparison_lines=[]
for c in comparisons:
 comparison_lines.append(f"- **{c['adaptive']} vs {c['baseline']}:** cycle saving {100*c['cycle_saving']:+.2f}%; LUT/FF/DSP change {c['LUT_difference']:+d}/{c['FF_difference']:+d}/{c['DSP_difference']:+d}; occupied-slice change {c['slice_difference']:+d}; LUT-clock/slice-clock proxy ratios {c['LUT_clock_product_ratio']:.3f}/{c['slice_clock_product_ratio']:.3f}, internal timing-clock diagnostic {c['internal_timing_times_clocks_ratio']:.3f}, boundary timing-clock diagnostic {c['boundary_timing_times_clocks_ratio']:.3f}.")
prog6=min([tops['top_stream_fold_absolute_prog'],tops['top_stream_fold_shared_absolute_prog']],key=lambda h:h['LUT'])
prog7=min([tops['top_stream_fold_offset_prog'],tops['top_stream_fold_shared_offset_prog']],key=lambda h:h['LUT'])
progh=tops['top_stream_unsigned_hybrid_prog'];const7=tops['top_stream_fold_offset_const'];lut=tops['top_stream_lut3_const']
consth=min([tops['top_stream_unsigned_hybrid_const'],tops['top_stream_compact_hybrid_const']],key=lambda h:h['occupied_slices'])
const_stmt=(f"The seven-bit constant-coefficient adaptive unit uses {const7['LUT']} LUT and {const7['FF']} FF plus one DSP, versus {lut['LUT']} LUT and {lut['FF']} FF with no DSP for the LUT triple. It needs {100*(a['clocks']/triple['clocks']-1):.2f}% more sampled model clocks.")
prog_stmt=(f"The six-bit programmable adaptive unit uses {prog6['LUT']} LUT, {prog6['FF']} FF and one DSP. The strongest tested programmable fixed hybrid uses {progh['LUT']} LUT, {progh['FF']} FF and one DSP, and needs {triple['clocks']:,} clocks versus the adaptive unit's {a6['clocks']:,}. Thus the adaptive LUT difference is {prog6['LUT']-progh['LUT']:+d}, with {100*(a6['clocks']/triple['clocks']-1):.2f}% more issue clocks.")
report=f'''# Membrane-aware leakage packing: structural repairs and fractional-C trial

Completed 2026-10-09. The experiment removes unnecessary correction logic, adds a strong fixed DSP/LUT hybrid, and implements a larger exact adaptive packing range. All tested integer outputs, reconstructed membranes, spikes and classifications match the declared beta231 reference. **Correctness and fewer issue clocks are established; a general hardware advantage is not established by these primitive measurements.**

The clearest first implementation improvement is the direct signed-five-bit branch: {oldabs['LUT']} to {newabs['LUT']} routed LUTs for the same adaptive schedule, a {100*(1-newabs['LUT']/oldabs['LUT']):.2f}% reduction. Its internal period diagnostic changes from {oldabs['internal_period_estimate_ns']:.3f} to {newabs['internal_period_estimate_ns']:.3f} ns. The strongest new algebra folds a fractional high-part correction into the DSP's existing C add input and expands the narrow operation to six or seven bits.

{const_stmt}

The constant seven-bit adaptive core occupies {const7['occupied_slices']} slices versus {consth['occupied_slices']} for the smallest-slice fixed DSP/LUT hybrid ({consth['top']}), a {100*(1-const7['occupied_slices']/consth['occupied_slices']):.2f}% reduction at the same one-DSP count, while using3.18% more sampled issue clocks. That fixed hybrid uses {consth['LUT']} LUT and {consth['FF']} FF; the alternative unsigned hybrid uses149 LUT but52 slices. Both are reported rather than combining the best numbers from different implementations. This is a measured fabric/schedule tradeoff from one placement; it is not a total-area or validated latency win. The constant LUT triple occupies {lut['occupied_slices']} slices and zero DSP.

{prog_stmt}

The shared coefficient table changes the mixed seven/six-bit programmable unit from {tops['top_stream_fold_offset_prog']['LUT']} to {tops['top_stream_fold_shared_offset_prog']['LUT']} LUTs, and the six-bit-only programmable unit from {tops['top_stream_fold_absolute_prog']['LUT']} to {tops['top_stream_fold_shared_absolute_prog']['LUT']} LUTs. The lowest-LUT mixed programmable candidate is {prog7['top']} with {prog7['LUT']} LUT, {prog7['FF']} FF and one DSP, at {a['clocks']:,} sampled model clocks. This selection is by LUT count, not a claim of fastest timing or smallest total physical area.

## Exact operation and interface

Every core implements leak(U)=ceil((256-delta)*U/256)=U-floor(delta*U/256), for signed11-bit membranes and a shared delta in[0,31]. Delta25 means beta231 in Q8. This is the leakage portion of a LIF neuron update, rather than synaptic accumulation. No rounding approximation, exponent adjustment, threshold approximation or state reordering is introduced.

The source supplies an ordered window of one to three actual membranes and an availability count. The core returns how many neurons to consume, then emits that count and full signed11-bit results. With continuous traffic and ready always asserted, K accepted windows occupy K+3 clocks through the final output handshake. Input bubbles, coefficient changes, poisoned unavailable tail payloads, output stalls and reset cancellation are checked. All stages freeze while the output is stalled. Callers deassert input valid during reset; ready is deliberately not reset-gated.

The controller, format muxes, exact correction/decoder, pipeline metadata, count and output registers are included in the measured core. The ordered lookahead source, variable address advance, bank rotation, state memory and variable-count writeback are not included. No external preformatting of membrane values is required, but the core assumes the raw three-value window is already available.

## What changed and why

- **Common upper-bit addition:** split each shared-offset reconstruction into a five-bit low sum and a shared upper increment. This increased the constant coherent-offset core to {tops['top_stream_compact_offset_const']['LUT']} LUTs from195. It is rejected as a hardware repair.
- **Direct signed-five-bit result:** for actual U in[-16,15], leak(U) is also signed5-bit. Pack the three signed low products and decode directly to five-bit results, then sign-extend. No arbitrary shared offset or full-width reconstruction is required in this branch. This is the compact E6 engine.
- **Unsigned wide residual:** write U=256*h+r with r in[0,255]. The two-lane DSP then needs no centering adder for h and no C bias in wide mode. Metadata stores U-delta*h, and the output subtracts floor(delta*r/256). Apply this equally to adaptive, fixed pair and fixed DSP/LUT hybrid. It is useful in the programmable case but does not uniformly lower mapped LUTs in the constant case.
- **Fractional-C folding:** write U=32*h+r,0<=r<32. Set q=floor(delta*h/8), f=(delta*h)mod8, and pre=U-q. Put the fractional term32*f into the DSP C field. Each packed field becomes p=delta*r+32*f, so the exact result is pre-floor(p/256). The output decoder subtracts an unsigned two-bit quotient and does not compute a separate fractional carry.
- **Strong fixed hybrid:** use the exact two-lane DSP pair plus one independent LUT leakage lane, consuming three full-range neurons every request. It shares coefficient, pipeline, count/tail behavior and backpressure with the adaptive core. A pure LUT triple and the fixed DSP triple remain comparisons too.
- **Shared coefficient table:** q/f for h=-2,-1,0,1 can be computed once per coefficient: q(-2)=-ceil(delta/4), q(-1)=-ceil(delta/8), q(0)=0, q(1)=floor(delta/8), with f=(delta*h)mod8. Each actual membrane selects its table entry. This removes the generic small high-part multiplier from each adaptive lane. The six-bit version uses only h=-1/0. All128 coefficient/high-part combinations and full RTL suites are checked.

## Safety conditions for the new adaptive range

For signed6-bit membranes, h is only-1 or0. For all delta0..31 the biased product p fits a ten-bit field. With h=-1 and nonzero delta=8*m+k, k in[0,7], its maximum is31*delta+32*((-delta)mod8). For k=0 this is248*m<=744; for k>0 it is248*m+256-k<=999. The h=0 maximum is961. These bounds prevent carries between the packed product fields.

For delta<=25, any high part h is safe because31*delta+32*f<=31*25+224=999<1024. The adaptive E0 core therefore consumes three when actual membranes fit[-64,63] and delta<=25, or fit[-32,31] for any supported delta. Otherwise it uses the exact full-range pair. The simpler adaptive E6 consumes three only for[-32,31], with all supported deltas.

The condition must be enforced: U63,delta31 gives p1185 and would overlap a ten-bit field. It therefore uses the wide fallback. This is an exact range policy, not lossy overpacking with a later recovery circuit.

The same algebra applies to a fixed full-range triple at delta25. That fixed engine stores three independent11-bit pre-corrections instead of the older57-bit metadata. It is implemented and routed as E4 at DC25. The programmable E4 retains the earlier general method; the new folded full-range triple is not claimed safe for every delta0..31.

## Functional evidence

- The direct five-bit arithmetic checks all1,048,576 triples/coefficient combinations and3,145,728 scalar outputs.
- The common-upper split checks all65,536 high/low bit-pattern pairs; its arithmetic is correct despite the area regression.
- Unsigned wide packing checks all2,097,152 residual pairs/coefficient combinations and65,536 full int11 scalar corrections.
- Fractional-C folding checks all8,388,608 signed6-bit triples across all32 coefficients, plus all2,097,152 signed7-bit triples at delta25. All31,457,280 scalar comparisons pass. Another53,248 full-range scalar checks cover the fixed folded condition delta<=25.
- The full RTL suites across four structural variants pass **{counts['neuron_output_comparisons']:,} neuron-output comparisons** and{counts['request_output_comparisons']:,} ordered request outputs, across{counts['rtl_engine_configuration_runs']} engine/configuration runs. Repeated cases across engines and configurations are included in these totals; they are not that many unique input tuples.
- Each main stimulus has166,840 frames and544,431 actual neurons, covering every int11 scalar/coefficient combination, complementary wide pairs, bin boundaries, all signed-int5 triples at delta25, random longer frames, coefficient changes, source bubbles and multi-cycle output stalls.
- Per engine, model replay covers635,904 actual neuron updates in9,216 unpadded frames: three saved seeds,48 held-out images each,32 time steps,128 hidden and10 output neurons. Python current integration, threshold and subtractive reset reconstruct all reference states and spikes exactly. Reference sampled classification accuracies remain93.75%,95.8333%,97.9167%. These are exact beta231-reference matches, not retrained or original-beta accuracy claims.
- Synthetic burst leakage is checked separately for640 six-neuron frames, including traces generated with subtractive and hard reset. This is a raw leakage replay, not a complete burst-latency or hard-reset-neuron RTL result.

## Measured model schedules

{'\n'.join(model_line(v,e)for v in variants for e in ([0,6]if v not in ['fold','fold_shared']else[0,1,3,4,5,6]))}

Five-bit adaptive to seven-bit fractional-C adaptive saves {100*(1-a['clocks']/a5['clocks']):.2f}% of sampled leakage-unit clocks. The new seven-bit schedule saves {100*(1-a['clocks']/pair['clocks']):.2f}% versus fixed pair and uses {100*(a['clocks']/triple['clocks']-1):.2f}% more than a fixed triple. The six-bit schedule saves {100*(1-a6['clocks']/pair['clocks']):.2f}% versus fixed pair and uses {100*(a6['clocks']/triple['clocks']-1):.2f}% more than a fixed triple. Programmable core schedule comparisons use this same delta25 replay; they do not establish performance across a variable-coefficient SNN.

These are continuous primitive-stream clocks. Draining after every neuron-array frame adds three clocks per frame, which reduces relative savings. A pair can also recognize the exact no-change interval U0..10 at delta25 and return three copies; the earlier analytical identity-aware fixed-pair schedule is289,627 continuous clock proxies. That monitor has not been implemented or routed here. A sudden burst can push every group out of the narrow range; no inherent worst-case burst guarantee follows from these averages.

## Routed hardware

All new builds use Vivado2025.2, Artix-7 xc7a100tcsg324-1, single-thread out-of-context synthesis/place/route, target4ns. Every listed core uses zero BRAM. Fabric FF counts exclude internal DSP registers. Occupied slices come directly from each routed utilization report, with one placement per design; they can vary with placement and constraints, and are not total chip area. Source hashes tie simulations to builds.

{'\n'.join(hwline(h)for h in hardware)}

Existing matched scalar/fixed references retained for comparison:

{'\n'.join(hwline(h)for h in refs)}

**Timing interpretation:** internal period4-WNS is a diagnostic that excludes raw input arithmetic; the LUT multiplication and parts of adaptive monitoring/high correction are before their first fabric registers. The after-route boundary audit includes those paths with input/output delays1ns max and0.1ns min, but primary-port routing and clock-source assumptions remain estimated. All boundary hold slacks are negative. Neither period diagnostic is a certified operating frequency or board measurement. A common registered launch/capture audit and matched pipelining are required before a latency or area-delay publication claim.

## Matched comparisons

Cycle saving is1-adaptive_clocks/fixed_clocks. Differences are adaptive minus baseline. Ratios above1 are worse for adaptive. LUT-clock and occupied-slice-clock products are declared fabric-only proxies at the same operating clock; they do not price DSP resources and are not total physical area, power or energy. Comparing them at equal DSP count is more meaningful than comparing a DSP core to a zero-DSP LUT core. Timing-clock ratios are diagnostics with the limitations above.

{'\n'.join(comparison_lines)}

## Practical result

The useful new mechanism is the exact fractional correction in DSP C. It expands the runtime packing range and removes a carry decoder without requiring an accelerator redesign. Its arithmetic, policy and sampled SNN output preservation are established. The constant-coefficient LUT triple remains a necessary benchmark, and the programmable fixed DSP/LUT hybrid prevents attributing every issue saving over a pair to adaptive packing.

Keep the fractional-C candidate for a focused pipeline study, rather than the failed common-upper-add repair. A programmable design that saves LUTs spends one DSP, and fewer LUTs alone is not a general hardware win. A three-lane fixed design executes fewer requests; adaptive must compensate through lower cost or a valid timing advantage. Do not claim beating FireFly, whole-neuron latency, memory bandwidth, energy, host speed or first-ever novelty from these results.

The next concrete study is a matched four-stage primitive pipeline: register the raw membrane/coefficient and format decision, align the DSP A/B registers with its C correction, and pipeline the full-width correction before output. Give the fixed pair and hybrid equivalent latency, and split the strong LUT baseline's product and subtraction across its stages instead of leaving two copy stages. Use registered launch/capture boundaries so all monitored input arithmetic enters the timing check. Reuse the exact same integer oracle, streams and reset/stall checks. This is an arithmetic-unit trial, not a new accelerator, and has not been executed in this evidence set.

## Reproduction and evidence

Run the make_stream_compact.py, make_stream_unsigned.py, make_stream_fold.py and make_stream_fold_shared.py generators in that order, then the corresponding check_stream_*.py and model scripts. The generator source originals are included. Numerical screens and all raw stimuli/output logs, simulation tool logs, routed timing/utilization reports and checkpoints are packaged. Heavy jobs check free RAM before launching. No downloads or original Desktop research-folder edits were made.

See adaptive_leakage_repairs_summary.json for machine-readable data and source hashes, adaptive_leakage_repairs_manifest.json for evidence hashes, and adaptive_leakage_repairs_evidence.zip for the saved reproduction files.
'''
(O/'adaptive_leakage_repairs.md').write_text(report,encoding='utf-8')
files=set()
def add(p):
 if p.is_file():files.add(p)
for v in variants:
 for n in [f'make_stream_{v}.py',f'stream_{v}_leak.sv',f'tb_stream_{v}_leak.sv',f'check_stream_{v}.py',
  f'check_stream_{v}_models.py',f'route_stream_{v}.tcl',f'run_stream_{v}_route.py']:add(P/n)
 for part in ['main_25_0','main_-1_1','models','stress']:
  tag=f'stream_{v}_{part}';add(R/(tag+'_checks.json'))
  for f in(R/tag).iterdir():
   if f.name=='stream_stim.txt'or f.name.startswith('stream_out')or f.name.startswith('tool_'):add(f)
 add(R/f'stream_{v}_hardware.json')
for n in ['stream_offset_leak.sv','tb_stream_offset_leak.sv','check_stream_offset.py','route_stream_offset.tcl',
 'run_stream_offset_route.py','screen_stream_compact.py','screen_stream_unsigned.py','screen_fraction_fold.py',
 'screen_fold_shared.py','finish_stream_compact_repairs.py','finish_stream_fold_trial.py','finish_stream_fold_shared.py','publish_stream_repairs.py']:add(P/n)
for n in ['adaptive_delta_model_input.json','stream_offset_hardware.json','stream_offset_schedule_audit.json',
 'stream_compact_arithmetic_screen.json','stream_unsigned_arithmetic_screen.json','fraction_fold_screen.json','fold_shared_screen.json']:add(R/n)
for tag in ['adaptive_delta_model_25_1','adaptive_delta_stress_25_1']:add(R/tag/'expected.npz')
for h in hardware+refs:
 top=h['top']
 for phase in ['synth','route']:
  for f in(R/f'{top}_{phase}').rglob('*'):add(f)
 for f in R.glob(top+'*'):
  if f.is_file():add(f)
for n in ['adaptive_leakage_repairs.md','adaptive_leakage_repairs_summary.json']:add(O/n)
items=[]
for f in sorted(files):
 relative=f.relative_to(P)if f.is_relative_to(P)else Path('outputs')/f.name
 items.append(dict(path=str(relative).replace('\\','/'),bytes=f.stat().st_size,sha256=sha(f)))
manifest=dict(files=items,source_hashes=sources,archive='adaptive_leakage_repairs_evidence.zip')
(O/'adaptive_leakage_repairs_manifest.json').write_text(json.dumps(manifest,indent=2))
archive=O/'adaptive_leakage_repairs_evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
 for f,item in zip(sorted(files),items):z.write(f,item['path'])
 z.write(O/'adaptive_leakage_repairs_manifest.json','outputs/adaptive_leakage_repairs_manifest.json')
with zipfile.ZipFile(archive)as z:
 assert z.testzip()is None
 for item in items:assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
print(json.dumps(dict(metrics=counts,archive_bytes=archive.stat().st_size,files=len(items)+1,
 compact_narrow=newabs,fold_programmable_narrow=prog6,fold_constant_adaptive=const7),indent=2),flush=True)
