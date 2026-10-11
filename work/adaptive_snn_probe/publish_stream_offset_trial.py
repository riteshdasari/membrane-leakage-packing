"""Publish exact streaming trial and its unsuccessful controller simplification."""
from pathlib import Path
import json,hashlib,zipfile
P=Path(__file__).resolve().parent;R=P/'results';O=P.parents[1]/'outputs'
def read(n):return json.loads((R/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={n:sha(P/n)for n in ['stream_offset_leak.sv','tb_stream_offset_leak.sv','stream_centered_leak.sv','tb_stream_centered_leak.sv']}
checks={}
for v in ['offset','centered']:
 stem='stream_offset_leak'if v=='offset'else'stream_centered_leak'
 for part in ['main_25_0','main_-1_1','models','stress']:
  key=f'stream_{v}_{part}';c=read(key+'_checks.json')
  assert c['source_hashes']=={n:hashes[n]for n in [stem+'.sv','tb_'+stem+'.sv']}
  assert len(c['rows'])==6 and all(r['mismatches']==0 for r in c['rows'])
  if part=='models':assert all(r['state_mismatches']==r['spike_mismatches']==0 for r in c['rows'])
  checks[key]=c
hardware=read('stream_offset_hardware.json');repair=read('stream_centered_hardware.json')
assert len(hardware)==10 and len(repair)==2
assert all(h['rtl_sha256']==hashes['stream_offset_leak.sv']for h in hardware)
assert all(h['rtl_sha256']==hashes['stream_centered_leak.sv']for h in repair)
tops={h['top']:h for h in hardware+repair}
schedule=read('stream_offset_schedule_audit.json');screen=read('stream_centered_screen.json');assert screen['arithmetic_failures']==0
models={v:{r['engine']:r for r in checks[f'stream_{v}_models']['rows']}for v in ['offset','centered']}
stress={v:{r['engine']:r for r in checks[f'stream_{v}_stress']['rows']}for v in ['offset','centered']}
metrics=dict(routed_cores=len(tops),rtl_engine_configuration_runs=sum(len(c['rows'])for c in checks.values()),
 neuron_output_comparisons=sum(r['neurons']for c in checks.values()for r in c['rows']),
 request_output_comparisons=sum(r['requests']for c in checks.values()for r in c['rows']),
 model_neurons_per_engine=schedule['model_neurons'],model_images=144,mismatches=0)
comparisons=[]
for v in ['offset','centered']:
 for coef in ['const','prog']:
  a=tops[f'top_stream_{"centered_"if v=="centered"else""}offset_{coef}']
  for baseline,e in [('fixed2',1),('fixed3',4),('lut3',3)]:
   f=tops[f'top_stream_{baseline}_{coef}'];ac=models[v][0]['clocks'];fc=models['offset'][e]['clocks']
   comparisons.append(dict(variant=v,coefficient=coef,baseline=baseline,
    cycle_saving=1-ac/fc,extra_LUT=a['LUT']-f['LUT'],extra_FF=a['FF']-f['FF'],extra_DSP=a['DSP']-f['DSP'],
    internal_timing_times_cycles_ratio=ac*a['internal_period_estimate_ns']/(fc*f['internal_period_estimate_ns']),
    boundary_timing_times_cycles_ratio=ac*a['boundary_period_estimate_ns']/(fc*f['boundary_period_estimate_ns']),
    note='OOC timing-times-cycle diagnostics, not measured FPGA latency or certified operating clocks. Programmable hardware uses the delta25 model schedule.'))
dominance=[]
for v in ['offset','centered']:
 for coef in ['const','prog']:
  a=tops[f'top_stream_{"centered_"if v=="centered"else""}offset_{coef}'];f=tops[f'top_stream_lut3_{coef}']
  keys=['LUT','FF','DSP','internal_period_estimate_ns','boundary_period_estimate_ns']
  dominated=all(f[k]<=a[k]for k in keys)and models['offset'][3]['clocks']<=models[v][0]['clocks']
  dominance.append(dict(variant=v,coefficient=coef,lut3_dominates_all_reported_resource_cycle_setup_metrics=dominated,
   note='Hold and external physical implementation remain unresolved; these are resource, schedule and setup diagnostics.'))
limits=['Leakage unit only. Current integration, threshold/reset and classification are reconstructed in Python',
 'Raw three-neuron ordered windows and up to three output values per clock; no state RAM, bank rotation, pointer update or lookahead cache is routed',
 'Shared delta0..31 per request, int11 membrane range. Per-neuron coefficient regrouping and larger coefficients are not implemented',
 'Input/output delays are applied after routing (1ns max,0.1ns min). OOC primary-port segments/clock-source assumptions are estimates; all boundary audits have negative hold slack',
 'Four-stage registered-input refinement and a complete state-memory wrapper were not built. No interface/board timing closure or power/energy measurement',
 'Beta231 changes the saved models. Equality is against the beta231 scalar reference, not against their original beta or retrained accuracy',
 'Replay covers first48 held-out images per saved seed; no full360-image streaming RTL run',
 'Frame-drain, identity-aware skipping and memory-bandwidth comparisons are analytic schedule screens, not extra routed implementations',
 'No FireFly implementation was reproduced. No claim of first-ever novelty or beating its accelerator results']
summary=dict(source_hashes=hashes,metrics=metrics,checks=checks,hardware=hardware,centered_hardware=repair,
 comparisons=comparisons,dominance=dominance,schedule_audit=schedule,centered_arithmetic_screen=screen,limitations=limits)
(O/'streaming_offset_summary.json').write_text(json.dumps(summary,indent=2))
def hwline(h):
 return f"- **{h['top']}:** {h['LUT']} LUTs, {h['FF']} fabric FFs, {h['DSP']} DSP, {h['RAMB18']} RAMB18, {h['RAMB36']} RAMB36; internal setup/hold slack {h['WNS_ns']:+.3f}/{h['WHS_ns']:+.3f} ns, internal period estimate {h['internal_period_estimate_ns']:.3f} ns; boundary setup/hold slack {h['boundary_WNS_ns']:+.3f}/{h['boundary_WHS_ns']:+.3f} ns."
def schedule_row(v,e):return next(r for r in schedule['rows']if r['variant']==v and r['engine']==e)
a=models['offset'][0];f=models['offset'][1];f3=models['offset'][4];c=models['centered'][0]
ad=schedule_row('offset',0);fd=schedule_row('offset',1);cd=schedule_row('centered',0)
model_lines=[]
for v in ['offset','centered']:
 for e,label in [(0,'adaptive'),(1,'fixed DSP pair'),(2,'LUT pair'),(3,'LUT triple'),(4,'fixed DSP triple'),(6,'absolute-only adaptive')]:
  r=models[v][e]
  model_lines.append(f"- **{v}, {label}:** {r['requests']:,} accepted windows, {r['clocks']:,} continuous clocks, {r['arithmetic_issues']:,} arithmetic requests; zero numerical/state/spike mismatches.")
comparisons_lines=[]
for d in comparisons:
 comparisons_lines.append(f"- **{d['variant']}, {d['coefficient']}, versus {d['baseline']}:** cycle saving {100*d['cycle_saving']:+.2f}%; LUT/FF/DSP differences {d['extra_LUT']:+d}/{d['extra_FF']:+d}/{d['extra_DSP']:+d}; internal timing-times-cycle ratio {d['internal_timing_times_cycles_ratio']:.3f}, boundary diagnostic ratio {d['boundary_timing_times_cycles_ratio']:.3f}. Ratios above1 mean the adaptive diagnostic is worse.")
mu=schedule_row('offset',4)
stress_lines=[]
for reset in [False,True]:
 rows={e:next(r for r in schedule['stress']if r['variant']=='offset'and r['engine']==e and r['hard_reset']==reset)for e in [0,1,4]}
 stress_lines.append(f"- **{'Hard'if reset else'Subtractive'} reset:** adaptive {rows[0]['requests']} requests, fixed pair {rows[1]['requests']}, fixed triple {rows[4]['requests']}. Adding a drain after each six-neuron timestep gives proxies of {rows[0]['frame_drained_clock_proxy']}, {rows[1]['frame_drained_clock_proxy']}, and {rows[4]['frame_drained_clock_proxy']} clocks respectively.")
report=f'''# Exact shared-offset streaming leakage trial

Completed 2026-10-09. **Streaming improves the packing opportunity, but neither tested adaptive implementation establishes a net hardware benefit over the strong fixed references.** The original shared-offset unit reduces sampled leakage-unit clocks by {100*(1-a['clocks']/f['clocks']):.2f}% versus an equally streaming fixed DSP pair. The fixed three-lane LUT implementation uses fewer clocks and dominates the original adaptive unit in the reported resource and setup-timing metrics, for both constant and programmable coefficients. The centered-bin repair does not produce a convincing win either; all its measurements are retained below.

## Scope and interface

The unit accepts a raw ordered window of one to three signed 11-bit membrane values, an availability count, and a shared delta in[0,31]. It returns a consume count immediately and later emits the corresponding one to three exact leakage results with a count. While reset is deasserted, the caller advances only on input valid/ready. Reset cancels queued work and the caller must stop presenting valid inputs during reset. No membrane sorting or packing is performed by the caller. The decoder, high corrections, format choice, count metadata, output registers and backpressure control are inside the measured unit.

Every implementation may accept one window each clock. A request produces valid results two clocks after its accept edge; with ready always high, the output handshake occurs three clocks after acceptance. For K uninterrupted windows, the measured span from the first acceptance through the last retirement is K+3 clocks. Output stalls freeze all data, format/coefficient metadata and DSP pipeline registers. Input bubbles do not change the ordering. Reset cancels unfinished requests. Input availability excludes padded neurons; unavailable payload bits are deliberately poisoned in the testbench and must have no effect.

The caller supplies three raw values as an ordered lookahead window. State storage, reading/bank rotation, pointer advancement, caching an unconsumed third value, and writing variable-size results are outside this primitive and have not been implemented or costed. Consequently this is not a complete SNN accelerator or a measured memory-to-memory update engine. Three-read/write bandwidth is required to sustain three real neuron updates per clock. A two-read/write state interface caps every design at two updates per clock, regardless of the DSP packing count.

## Integer update and original shared-offset policy

The contract is leak(U)=ceil((256-delta)*U/256)=U-floor(delta*U/256). Constant delta25 corresponds to beta231 in Q8 notation. This is leakage, rather than synaptic accumulation. No exponent representation or approximate mantissa shift is introduced.

The original adaptive engine consumes three neurons when the available triple either fits[-16,15] or has equal upper parts U//32. For the first case choose b=-16; otherwise choose b=32*(U0//32). Write U_i=b+r_i with unsigned five-bit residuals0<=r_i<32. A single DSP packs three products p_i=delta*r_i in ten-bit fields. Centering the top multiplicand and adding its constant bias keeps the signed 25-bit DSP input legal. The product fields do not overlap and their maximum is961.

For exact reconstruction, let z=delta*(b/16), q=floor(z/16), and s=z mod16. Then floor(delta*U_i/256)=q+(p_i>>8)+carry_i, where carry_i=(((p_i>>4)&15)+s)>>4. The returned value is (b-q)+(r_i-(p_i>>8)-carry_i). The low residual result remains in[0,31]. The floor operations are part of the declared integer neuron update; they do not discard information from an approximate membrane representation.

When the triple is ineligible, the engine consumes two full-range neurons. Split U=256*h+r with signed eight-bit r. A DSP packs two delta*r products in sixteen-bit fields, while two small fabric high corrections reconstruct U-delta*h-floor(delta*r/256). This does not promote state into a separate wide accumulator. Stored and returned membranes remain signed 11-bit values.

All engines consume three copies for a delta0 identity request or an all-zero window. The fixed pairs also consume three when the third available neuron is zero: the first two use arithmetic and the third is returned as zero. This avoids giving adaptation an advantage solely from zero tail lanes.

## Strong fixed references and a controller repair

The fixed DSP pair uses the same wide residual split, scheduling contract and backpressure support. The fixed DSP triple is fully implemented in this trial: U_i=32*h_i+r_i with signed five-bit r_i, three packed residue products, and three independent exact high corrections. It always consumes three available neurons, including values outside the adaptive eligibility interval. Thus two lanes is not a full-range capacity limit.

The LUT pair and LUT triple implement the same integer update with DSP use disabled. For constant delta25 they explicitly factor multiplication as16*U+8*U+U. Programmable LUT references support the same allowed five-bit delta range as the adaptive engine. They use the same output latency and stall protocol. This is a comparison of the same leakage operation, not an inflated general multiplier baseline.

The isolated repair replaces the absolute-range OR uncentered-bin monitor with one equality test on h_i=floor((U_i+16)/32). Equal high parts permit a shared correction for signed five-bit residuals. With z=delta*h, the common high result is32*h-floor(z/8); each residual needs its signed product floor and a three-bit fraction carry. The first high-correction multiplier is also reused for the wide pair. This changes the eligibility set: it is not a strict superset of the original policy. The centered arithmetic screen passes {screen['arithmetic_cases']:,} checks, and the complete RTL tests/replays below pass.

## Verification and reconstructed SNN outputs

Across both implementations, {metrics['rtl_engine_configuration_runs']} engine/configuration runs check **{metrics['neuron_output_comparisons']:,} individual neuron outputs** in {metrics['request_output_comparisons']:,} retired windows. These counts include repeated inputs across reference engines and implementations; they are not unique arithmetic tuples. There are zero detected mismatches against an independent scalar oracle. The range tests exercise every signed 11-bit scalar at every allowed delta, complementary wide inputs, equal-prefix triples near the range boundaries, every signed-int5 triple at delta25, random longer frames, coefficient transitions, one/two/three-neuron tails, zero/identity bypass, input gaps, output backpressure, and reset cancellation while the output is blocked. The acceptance count and three advancing-clock pipeline latency are also checked. An initial simulation startup error was traced to Xilinx glbl holding DSP primitives in reset during the first100ns; the final testbench begins after that reset and then explicitly exercises its own reset protocol. Oracle expectations were not changed to accommodate the failure.

Each model replay covers {schedule['model_neurons']:,} real-neuron leakage updates in {schedule['model_frames']:,} frames: first48 held-out images from each of three saved seeds,32 timesteps,128 hidden and10 output neurons. Padded lanes from the previous six-neuron experiment are removed. Python adds the saved current, performs threshold/subtractive reset, and reconstructs membrane states, spikes, output spike counts and classification. All engines match exactly. Sampled reference and reconstructed classification is93.75%,95.83%, and97.92% for seeds0,1,2 respectively.

Beta231 changes the saved models' original leakage. There was no retraining, and the equality claim is against the scalar beta231 reference, not unchanged accuracy versus the originally trained beta. Synaptic integration and threshold/reset are not executed in RTL here. The previous beta231 range certificate for these saved weights/thresholds is included; no range claim is made for arbitrary SNNs or other neuron models. This primitive tests linear integer leakage suitable for the declared LIF update, not complete Izhikevich or Hodgkin-Huxley neurons.

## Complete-unit clocks and useful arithmetic

{chr(10).join(model_lines)}

The original adaptive unit takes **{a['clocks']:,} clocks versus {f['clocks']:,}** for fixed DSP pairs, a {100*(1-a['clocks']/f['clocks']):.2f}% saving. Fixed DSP/LUT triples take **{f3['clocks']:,} clocks**, so the adaptive schedule takes {100*(a['clocks']/f3['clocks']-1):.2f}% more clocks than them. The centered policy takes {c['clocks']:,} clocks, saving {100*(1-c['clocks']/f['clocks']):.2f}% versus the fixed pair; it gives up some eligibility in exchange for a simpler intended controller.

These are measured cycles of a continuously supplied leakage unit. They are not whole-network latency. If each neuron-array frame instead waits for the pipeline to drain, adding three clocks per frame gives analytic proxies of {ad['frame_drained_clock_proxy']:,} adaptive, {fd['frame_drained_clock_proxy']:,} fixed pair and {cd['frame_drained_clock_proxy']:,} centered clocks. Synaptic work, threshold/reset, memory transfers and host costs are still excluded.

The sampled membranes contain {schedule['model_nonzero_membranes']:,} nonzero multiplier terms and {schedule['model_changed_membranes']:,} updates whose leaked value actually changes. Original adaptive packing performs {ad['nonzero_products_per_arithmetic_issue']:.3f} nonzero products per active DSP issue versus {fd['nonzero_products_per_arithmetic_issue']:.3f} for the fixed pair and {mu['nonzero_products_per_arithmetic_issue']:.3f} for the fixed triple. Counting only changes instead gives {ad['changed_membranes_per_arithmetic_issue']:.3f}, {fd['changed_membranes_per_arithmetic_issue']:.3f} and {mu['changed_membranes_per_arithmetic_issue']:.3f}. These are declared work-per-issue measures, not DSP power or energy measurements. The fixed triple remains the most productive of these DSP schedules.

For delta25, U in[0,10] is an exact integer leakage fixed point. A stronger pair schedule that copies three such values without arithmetic would take {schedule['identity_aware_fixed2_continuous_clock_proxy']:,} clocks in an optimistic schedule screen. The original adaptive saving versus that estimate falls to {100*(1-a['clocks']/schedule['identity_aware_fixed2_continuous_clock_proxy']):.2f}%. Its extra monitor has not been built or routed. This prevents treating all small nonzero membrane products as necessary computation, or calling the measured pair the strongest conceivable baseline.

## Bursts

{chr(10).join(stress_lines)}

On the concatenated synthetic sparse/burst stream, original adaptive clocks fall from {stress['offset'][1]['clocks']} to {stress['offset'][0]['clocks']}, saving {100*(1-stress['offset'][0]['clocks']/stress['offset'][1]['clocks']):.2f}% under continuous supply. A drain per timestep reduces that opportunity, as shown above. The early synthetic bursts have identical lanes and favor shared offsets. This is not evidence of natural-model burst acceleration or a worst-case latency guarantee. Divergent membrane high parts force pair mode; fixed three-lane arithmetic still needs fewer issue windows.

## Routed hardware and timing limitations

Vivado2025.2, xc7a100tcsg324-1, one tool thread, common4ns out-of-context clock. All twelve designs use the same core interface. Counts include the per-request correction/format/count registers, ready/valid handling and output registers; internal DSP registers are excluded from fabric FF counts. All routed checkpoints and reports are retained.

{chr(10).join(hwline(h)for h in hardware+repair)}

The first adaptive constant version uses195 LUTs and127 fabric FFs versus97/77 for a fixed DSP pair,215/158 for a fixed DSP triple, and137/108 for a LUT triple. The programmable adaptive version uses297/133 plus one DSP, versus272/108 with zero DSPs for programmable LUT triples. The isolated repair measurements appear above: simpler arithmetic block sharing in the source is not sufficient evidence of a smaller mapped design.

{chr(10).join(comparisons_lines)}

An internal period estimate is4ns minus internal setup slack. It is a diagnostic, not a certified operating period. Multiplying it by the measured cycles likewise gives a comparison diagnostic, not observed FPGA latency. The separate boundary audit applies1ns max and0.1ns min input/output delays after routing and includes raw membrane, availability, coefficient, consume-count and backpressure paths. Primary-port segments and the OOC clock source are not fully implemented. All boundary audits have negative hold slack; increasing the clock period alone does not repair that. No complete interface timing closure or board measurement is claimed.

The raw-input correction paths are material: the original constant adaptive audit reports12 logic levels and a10.079ns estimated data path from availability to correction metadata, while its register-to-register period estimate is4.727ns. Ignoring this input path would make the claimed speed too optimistic. A registered-input refinement could expose and pipeline those paths, at additional latency/register cost, but it was not implemented in this trial. The centered repair moves selection ahead of the reused high multiplier and has its own boundary path reports. No timing-times-cycle ratio here should be presented as an achieved accelerator speedup.

## What this establishes

Actual membrane values can safely select a three- or two-operation DSP layout, and shared offsets can preserve triple packing at larger membrane magnitudes. The RTL and model tests support the declared integer output preservation. Streaming removes much of the old six-neuron bank startup/drain overhead, which explains the larger average cycle opportunity.

The measurements still do not establish a publication-strength hardware win. For small five-bit leakage complements, constant and programmable LUT arithmetic is inexpensive. The adaptive datapath adds monitoring, multiple field layouts, high-correction selection and metadata; the full-range fixed triple avoids the adaptive issue fallback. The targeted centered repair does not eliminate those costs. This conclusion is about the two implemented datapaths, not a proof that all membrane-aware hardware is ineffective.

FireFly is related work, not a matched implementation baseline: its synaptic DSP crossbars and accelerator measurements are different from this leakage primitive. No accuracy, TOPS, latency, power or host comparison with FireFly is justified. No first-ever novelty claim is established by this hardware trial. Generic packing/correction is covered by [DSP-Packing](https://arxiv.org/html/2203.11028); runtime datatype switching is also established in work such as [XtraMAC](https://arxiv.org/html/2605.06052). The research claim would still need a useful, efficient actual-membrane-driven policy rather than packed arithmetic alone.

## Reproduction and evidence

The evidence archive includes both RTL versions and testbenches, independent checking scripts, exact stimuli and outputs, model inputs/ledger, prior range certificates, all twelve routed checkpoints/reports, tool logs, this report, the summary and a SHA256 manifest. Use the installed Python environment and Vivado2025.2. The verification scripts require the local Xilinx unisim libraries; no tool binaries are distributed. The finish scripts serialize heavy routes and check available RAM. No models, datasets or packages were downloaded, and the original external research folder was not changed.
'''
for before,after in [('delta25','delta = 25'),('beta231','beta = 231'),('Beta231','Beta = 231'),('delta0','delta = 0'),
 ('first48','first 48'),('three signed','three signed'),('residuals0','residuals 0'),('maximum is961','maximum is 961'),
 ('and s=z mod16','and s=z mod 16'),('first100ns','first 100 ns'),('seeds0,1,2','seeds 0, 1, 2'),
 ('is93.75%','is 93.75%'),('and97.92%','and 97.92%'),('32 timesteps','32 timesteps'),
 ('seeds,32','seeds, 32'),('timesteps,128','timesteps, 128'),('and10 output','and 10 output'),
 ('Vivado2025.2','Vivado 2025.2'),('common4ns','common 4 ns'),('uses195','uses 195'),('and127','and 127'),('uses297','uses 297'),
 ('is4ns','is 4 ns'),('applies1ns','applies 1 ns'),('and0.1ns','and 0.1 ns'),('reports12','reports 12'),
 ('a10.079ns','a 10.079 ns'),('is4.727ns','is 4.727 ns'),('above1','above 1')]:report=report.replace(before,after)
(O/'streaming_offset_trial.md').write_text(report,encoding='utf-8')
files=set()
names=['stream_offset_leak.sv','tb_stream_offset_leak.sv','stream_centered_leak.sv','tb_stream_centered_leak.sv',
 'check_stream_offset.py','check_stream_centered.py','check_stream_offset_models.py','make_stream_centered.py',
 'route_stream_offset.tcl','route_stream_centered.tcl','run_stream_offset_route.py','run_stream_centered_route.py',
 'finish_stream_offset_trial.py','finish_stream_centered_trial.py','analyze_stream_offset.py','screen_centered_offset.py',
 'publish_stream_offset_trial.py','screen_shared_offset_delta.py','audit_adaptive_delta_bounds.py']
files.update(P/n for n in names)
files.update(R.glob('stream_*checks.json'));files.update([R/'stream_offset_hardware.json',R/'stream_centered_hardware.json',
 R/'stream_offset_schedule_audit.json',R/'stream_centered_screen.json',R/'stream_offset_startup_debug.log',
 R/'adaptive_delta_model_input.json',R/'adaptive_delta_stress_input.json',R/'adaptive_delta_model_bounds.json',
 R/'shared_offset_delta_screen.json',R/'final_selected.json'])
files.update(R.glob('model_seed*.npz'));files.update([R/'adaptive_delta_model_25_1/expected.npz',R/'adaptive_delta_stress_25_1/expected.npz'])
for h in hardware+repair:
 for directory in [R/f"{h['top']}_synth",R/f"{h['top']}_route"]:files.update(p for p in directory.iterdir()if p.is_file())
 files.update(R.glob(h['top']+'*build.log'));files.update(R.glob(h['top']+'*vivado.log'));files.update(R.glob(h['top']+'*vivado.jou'))
for folder in R.iterdir():
 if folder.is_dir()and (folder.name.startswith('stream_offset_')or folder.name.startswith('stream_centered_'))and ('smoke'in folder.name or'main'in folder.name or'models'in folder.name or'stress'in folder.name):
  files.update(p for p in folder.iterdir()if p.is_file()and(p.suffix=='.txt'or p.name.startswith('tool_')))
files.update([O/'streaming_offset_trial.md',O/'streaming_offset_summary.json'])
entries=[]
for f in sorted(files):
 arc='outputs/'+f.name if f.parent==O else str(f.relative_to(P)).replace('\\','/')
 entries.append(dict(path=arc,bytes=f.stat().st_size,sha256=sha(f)))
manifest=dict(source_hashes=hashes,metrics=metrics,files=entries)
(O/'streaming_offset_manifest.json').write_text(json.dumps(manifest,indent=2))
archive=O/'streaming_offset_evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
 for f,e in zip(sorted(files),entries):z.write(f,e['path'])
 z.write(O/'streaming_offset_manifest.json','outputs/streaming_offset_manifest.json')
with zipfile.ZipFile(archive)as z:
 assert z.testzip()is None
 for e in entries:assert hashlib.sha256(z.read(e['path'])).hexdigest()==e['sha256']
print(json.dumps(dict(metrics=metrics,comparisons=comparisons,dominance=dominance,evidence_files=len(entries),zip_bytes=archive.stat().st_size),indent=2),flush=True)
