"""Package the completed fixed leakage study and clearly labelled next hypothesis."""
from pathlib import Path
import json,hashlib,re,zipfile
P=Path(__file__).resolve().parent;R=P/'results';O=P.parents[1]/'outputs';O.mkdir(exist_ok=True)
def read(n):return json.loads((R/n).read_text())
sources={n:hashlib.sha256((P/n).read_bytes()).hexdigest()for n in ['packed_leak.sv','split_leak.sv','fixed_lut_leak.sv','distributed_leak.sv']}
checksets=[read(n)for n in ['packed_leak_checks.json','split_leak_checks.json','fixed_lut_leak_checks.json','distributed_leak_checks.json']]
assert [len(c['rows'])for c in checksets]==[12,4,2,2]
assert all(x['mismatches']==0 for c in checksets for x in c['rows'])
assert checksets[0]['rtl_sha256']==sources['packed_leak.sv']
assert checksets[1]['source_hashes']=={n:sources[n]for n in ['split_leak.sv','packed_leak.sv']}
assert checksets[2]['rtl_sha256']==sources['fixed_lut_leak.sv']
assert checksets[3]['rtl_sha256']==sources['distributed_leak.sv']
hardware=[]
for filename,source in [('packed_leak_hardware.json','packed_leak.sv'),('split_leak_hardware.json','split_leak.sv'),('fixed_lut_leak_hardware.json','fixed_lut_leak.sv'),('distributed_leak_hardware.json','distributed_leak.sv')]:
 rows=read(filename)
 for row in rows:
  assert row['rtl_sha256']==sources[source],row['top']
  if source=='split_leak.sv':assert row['base_rtl_sha256']==sources['packed_leak.sv']
  util=(R/f"{row['top']}_route"/'util.rpt').read_text()
  def count(label):
   m=re.search(r'\|\s*'+re.escape(label)+r'\s*\|\s*([\d.]+)',util);assert m,label;return float(m[1])
  row['BRAM_tiles']=count('Block RAM Tile');row['RAMB18']=int(count('RAMB18'));row['RAMB36']=int(count('RAMB36/FIFO*'))
 hardware.extend(rows)
tops={h['top']:h for h in hardware};assert len(tops)==11
required=['top_leak_pack8_const','top_leak_lut8_const','top_leak_pack8_prog','top_leak_lut8_prog','top_leak_lut8_factored','top_leak_lut8_rom','top_leak_lut8_distributed','top_leak_split10_const','top_leak_lut10_pipe_const','top_leak_split10_prog','top_leak_lut10_pipe_prog']
assert all(t in tops for t in required)
assert tops['top_leak_lut8_rom']['RAMB18']==1
assert tops['top_leak_lut8_distributed']['RAMB18']==tops['top_leak_lut8_distributed']['RAMB36']==0
audits={n:read(n)for n in ['packed_leak_algebra.json','split_leak_algebra.json','delta_packing_algebra.json']}
assert all(a['failures']==0 for a in audits.values())
screen=read('leak_adaptation_screen.json');assert len(screen['rows'])==36
assert all(r['integer_leak_mismatches']==0 for r in screen['rows'])
opportunities=[r['delta25_three_vs_two_ideal_saving']for r in screen['rows']if r['beta']==231]
metrics=dict(rtl_engine_runs=sum(len(c['rows'])for c in checksets),rtl_pair_requests=sum(r['requests']for c in checksets for r in c['rows']),arithmetic_cases=sum(a['cases']for a in audits.values()),
 delta25_ideal_issue_saving_min=min(opportunities),delta25_ideal_issue_saving_max=max(opportunities),
 programmable8_lut_reduction=1-tops['top_leak_pack8_prog']['LUT']/tops['top_leak_lut8_prog']['LUT'],
 programmable10_lut_reduction=1-tops['top_leak_split10_prog']['LUT']/tops['top_leak_lut10_pipe_prog']['LUT'])
summary=dict(decision='Programmable leakage has a useful fixed packed DSP tradeoff against the tested LUT multipliers. Constant leakage has stronger factored and ROM alternatives. Adaptation is an arithmetic/range hypothesis only, with no adaptive RTL or measured total neuron-update benefit.',
 source_hashes=sources,checks=checksets,audits=audits,hardware=hardware,model_range_screen=screen,metrics=metrics,
 limitations=['Leakage-only cores; synaptic accumulation, threshold/reset and persistent neuron banks are excluded','Programmable coefficient is shared across packed lanes','Internal OOC timing only; input/output delays unconstrained','No adaptive controller hardware, power, board or FireFly reproduction','Beta231 screens modify dynamics of existing saved weights; no retraining','Several beta231 screens exceed signed int10; software correction is int64'])
(O/'leak_packing_summary.json').write_text(json.dumps(summary,indent=2))
labels={'top_leak_pack8_const':'Packed DSP, 8-bit, constant beta231','top_leak_lut8_const':'Initial LUT multiply, 8-bit, beta231','top_leak_pack8_prog':'Packed DSP, 8-bit, programmable beta',
 'top_leak_lut8_prog':'LUT multiply, 8-bit, programmable beta','top_leak_lut8_factored':'Factored LUT arithmetic, 8-bit, beta231','top_leak_lut8_rom':'Automatic ROM mapping, 8-bit, beta231',
 'top_leak_lut8_distributed':'Distributed ROM, 8-bit, beta231','top_leak_split10_const':'Fixed high/low split, 10-bit, beta231','top_leak_lut10_pipe_const':'Pipelined LUT multiply, 10-bit, beta231',
 'top_leak_split10_prog':'Fixed high/low split, 10-bit, programmable beta','top_leak_lut10_pipe_prog':'Pipelined LUT multiply, 10-bit, programmable beta'}
lines=[]
for t in required:
 h=tops[t]
 lines.append(f"- **{labels[t]}:** {h['LUT']} LUTs, {h['FF']} fabric FFs, {h['DSP']} DSP, {h['RAMB18']} RAMB18, {h['RAMB36']} RAMB36; setup slack {h['WNS_ns']:+.3f} ns; hold slack {h['WHS_ns']:+.3f} ns; internal period estimate {h['internal_period_estimate_ns']:.3f} ns.")
prog=tops['top_leak_pack8_prog'];plut=tops['top_leak_lut8_prog'];split=tops['top_leak_split10_prog'];slut=tops['top_leak_lut10_pipe_prog'];dist=tops['top_leak_lut8_distributed']
report=f'''# Exact leakage packing: fixed building block and next adaptive hypothesis

## Decision

The general leakage multiplication is a more useful DSP target than the previously tested binary-spike addition and shift leak. With a shared programmable coefficient, two 8-bit operations use **{prog['LUT']} LUTs and one DSP**, versus **{plut['LUT']} LUTs and no DSP** for the tested matched LUT multiplier. The complete 10-bit fixed high/low version uses **{split['LUT']} LUTs and one DSP**, versus **{slut['LUT']} LUTs** for its matched pipelined LUT multiplier. Both comparisons have equal accepted work and pipeline latency within their group. These are resource/timing tradeoffs for fixed primitives, not an adaptive novelty result.

Constant coefficients demand stronger comparisons. The initial constant LUT multiplication is reduced from 99 to 43 LUTs by factoring it, and the factored core has better internal timing than the packed DSP core. A table implementation maps to one RAMB18 and six LUTs, with faster internal timing. A forced distributed table uses **{dist['LUT']} LUTs, zero DSP and zero BRAM**, with an internal period estimate of **{dist['internal_period_estimate_ns']:.3f} ns**. The DSP implementation cannot be presented as uniformly superior to these fixed-coefficient alternatives.

The next adaptive mechanism worth a bounded RTL test is packing **three narrow membrane leakage operations versus two full-range operations**, using a small decay coefficient. The arithmetic is checked, and coefficient-231 trace scenarios offer an ideal **{min(opportunities)*100:.1f}–{max(opportunities)*100:.1f}% reduction in leakage issue slots** after removing zero groups. No adaptive RTL, controller area, burst latency, total neuron-update speedup or publication-strength gain has been established. The fixed two-lane full-range baseline must be retained; comparing only with one un-packed wide multiplication would overstate adaptation.

This is explicitly a change from packing synaptic accumulation alone. The implemented cores compute **membrane leakage**, while input spikes can remain binary in a surrounding neuron. Accumulation, threshold/reset, the complete neuron state bank and an accelerator are not implemented in these new cores.

## Fixed two-lane arithmetic

Declare the reference as U_next=ceil(beta*U/256), with shared beta in [0,256]. For signed int8 membrane U, store q=U+128. Let K=128*(256-beta)+255. A=(q0+q1*2^16) fits the positive input range of the DSP48E1's 25-bit multiplier; B=beta and C=K*(1+2^16). P=A*B+C contains two independent 16-bit results. Each field R=beta*q+K lies in [0,65535]. Extract each field's upper eight bits and subtract the bias by toggling its sign bit. There is no cross-field carry and no exponent quantization.

The RTL uses registered raw inputs and the DSP P register. The LUT version has the same accepted-input/result schedule, one pair per clock, with DSP inference disabled. The coefficient is either constant 231/256 or programmable for each request. The fixed coefficient was a representative general coefficient; this is not a survey of all constant-coefficient synthesis outcomes. Packable lanes require equal coefficients. Per-neuron coefficient grouping and its storage/routing costs are unmeasured.

## Strong full-range packing baseline

A 10-bit membrane does not force one complete operation per DSP. Write U=256*h+r, with r the signed low int8 value. Then

    ceil(beta*U/256) = beta*h + ceil(beta*r/256)

The small high term h ranges from -2 to +2 for signed int10. The fixed baseline always packs both low residues in one DSP and computes the small high correction in LUTs. It therefore handles **two complete int10 neurons per DSP**, without an adaptive monitor or overflow fallback. It adds a second registered compute stage for the correction. The matched LUT reference registers its full product, then rounding/extraction in a second stage. Both accept one pair per clock and have the same valid latency, including bubbles.

This baseline prevents an artificial twofold adaptive gain from treating every wider membrane as necessarily an un-packed DSP operation. The implemented split is int10 only. Wider states need a larger high correction and separate validation/costs; software int64 correction is not evidence that those wider hardware implementations have been tested.

## Strong constant-coefficient alternatives

For beta=231, leakage is also U-floor(25*U/256). The factored LUT version forms 25U=16U+8U+U, then performs the correction. It matches the exact integer oracle on every int8 input pair, and the same accepted-input/result schedule. An explicit constant truth table was also tested. Vivado automatically mapped the first table to a dual-port RAMB18; it is a BRAM alternative, not a LUT-only implementation. A separate source forces distributed ROM and consumes zero BRAM. Both table outputs are checked against the independent reference. ROM width, depth and bandwidth become material costs for wider states or many coefficients.

For programmable beta, the tested LUT baselines use general multiplication. A layer-programmable table with reloading/caching is not implemented here. If beta changes only between layers, that alternative must be assessed with its table, setup and coefficient-storage costs before claiming a deployment advantage. A per-request programmable multiplier comparison does not justify a workload whose coefficients can be hardwired cheaply.

## Routed cores

Vivado 2025.2, Artix-7 xc7a100tcsg324-1, out-of-context, one thread, common 4 ns constraint. Every listed design completed placement and routing. All rows contain two neuron outputs. The int8 group has one registered compute stage after the input registers; the full int10 group has two. Compare within a width/latency group.

{chr(10).join(lines)}

Internal period estimates equal 4 ns minus setup slack. They are not achieved board frequencies or measured throughput. External input/output delays are unspecified and OOC ports have partial-route warnings. BRAM/DSP internal registers are excluded from fabric FF counts. The initial 4 ns constraint is missed by several cores; positive internal slack does not certify interface timing. No power, energy, host time, memory subsystem, board or FireFly system result is reproduced.

The programmable packed and split DSP builds each initially hit Vivado's blank Synth 20-411 at opt_design. Each was retried once by opening its unchanged synthesis checkpoint and completed. Failed and retry logs are retained. The simulator also needed unsandboxed access for its generated-code compiler. Neither issue was repaired by changing the arithmetic. Early declaration errors were corrected before the passing source hashes and hardware builds.

## Correctness evidence

- Int8 algebra: 65,792 scalar input/coefficient combinations and 100,000 packed pairs, zero failures.
- Full int10 decomposition: 263,168 exhaustive scalar/coefficient combinations, zero failures.
- RTL: {metrics['rtl_engine_runs']} engine/configuration runs and {metrics['rtl_pair_requests']:,} checked pair requests in total across engines, zero differences. The int8 constant test includes every input pair. The programmable int8 test covers every individual int8 value/coefficient combination and additional random/boundary pairs. Full int10 programmable tests cover every individual value/coefficient combination, plus random pairs and bubbles. Both fixed LUT alternatives and their distributed source are independently compared against the integer oracle.
- The possible three-lane format described below adds 1,048,576 exhaustive arithmetic combinations, zero failures. It has no RTL implementation in this study. Total arithmetic audit cases: {metrics['arithmetic_cases']:,}.
- Saved-model numerical screen: all three existing seed weight sets, nine saved IF/LIF/threshold reference configurations, hard and subtractive reset, original beta and beta231 scenarios, 360 held-out digits images, 32 timesteps. All 36 runs have zero integer leakage differences under the checked low-residue plus int64 high-correction transformation. This is Python inference, not FPGA inference or full-network RTL validation. Beta231 scenarios change the dynamics of the existing weights; no retraining was performed and their classification accuracy is not proof that a floating-point trained model is preserved. Raw accuracy and range values are in the JSON.

Several beta231 scenarios reach membrane values outside signed int10. They need a wider exact path before whole-model hardware deployment. The three saved reference beta values 128,224,256 are especially cheap shift/identity cases; the programmable multiplication benefit does not apply automatically to those models' original leakage. Beta256 needs no leakage multiplication, and strong baselines should bypass it.

## The next adaptive arithmetic layout

Use delta=256-beta. For delta<=31 and actual U in [-16,15], the exact update is

    U_next = U - floor(delta*U/256)

Three signed five-bit inputs fit in one DSP multiply with ten-bit product spacing. Bias the lower two inputs by 16 and leave the upper input signed:

    A = (U0+16) + (U1+16)*2^10 + U2*2^20
    C = (512-16*delta)*(1+2^10)
    P = A*delta + C

A lies within the DSP48E1's signed 25-bit range. The lower two product fields are delta*U+512, nonnegative and below 1024. The upper field is a signed ten-bit product. Each floor quotient uses two extracted bits; the lower two have a bias of two to remove. Subtract the quotient from the original U. The original U must remain available/aligned for that correction, which has a hardware and scheduling cost. Exhaustively checking every delta and every input triple gives the count above. Beta256 and all-zero groups should be handled directly by both baselines.

A causal controller could examine actual membrane values, choose this three-lane format only when their range fits, and otherwise use the fixed two-lane full-range split. That is genuinely membrane-potential-aware representation selection. It is currently an arithmetic hypothesis, not a tested controller. Native signed packing, multiplication correction and mixed-width packing already have extensive prior art; the small packing formula alone is not claimed as novel.

## Numerical opportunity and its limits

The screen examines naturally ordered groups of six stored membranes before leakage. Full groups only are counted: the final two hidden neurons and final four output neurons are omitted from this grouping profile. A three-lane format needs two issues per group, versus three for a fixed two-lane format. Both candidates may skip groups whose six membranes are all zero. Among the coefficient-231 scenarios, the resulting ideal issue saving ranges from {min(opportunities)*100:.2f}% to {max(opportunities)*100:.2f}%. The upper end comes from a changed-dynamics scenario with hard reset, not a cherry-picked claim about the original model's exact dynamics.

These fractions omit range-check cycles, packet preparation, retained operands, mode tags, conversion, memory bandwidth/ports, stalls, pipeline drain, accumulation, firing and reset. They are a screen for whether to build a controller, not measured latency. Three reads/results per narrow issue may require more instantaneous state bandwidth than the fixed two-lane unit. A gain in leakage issue slots can be much smaller when expressed over a complete timestep with many synaptic events.

The older direct-beta three-bit packing opportunity is generally much smaller once zero groups are removed. Factoring into the small decay coefficient widens the eligible input range from signed int3 to signed int5 for beta231, explaining why this new numerical screen is more promising. That observation still requires a matched hardware test.

## What to test next, while keeping the paper small

Build one small arithmetic unit with an actual-U monitor, the three-lane narrow format and a validated wider fixed split. Compare against the same wider fixed split, optimized LUT arithmetic, and constant/programmed-table alternatives appropriate to the model. Include state storage, operand delivery and every control/convert/drain cycle. Try sparse steps and bursts using the same event stream and integer neuron contract. Report the incremental effect of adaptation separately from ordinary DSP packing. If controller cost consumes the numerical opportunity, retain the fixed primitive result and reject that adaptive implementation.

The scope remains a packing unit plus its minimal controller; no full accelerator is required to test that claim. The unresolved scientific requirement is demonstrating an adaptive benefit at a useful resource/clock tradeoff on a real model needing general leakage. This experiment supplies a more plausible arithmetic target and an exact next layout; it does not establish an ISCAS contribution yet.

## Prior-art position

[Fang et al., ICCV 2021](https://arxiv.org/abs/2007.05785) motivate learnable membrane time constants. That does not imply shared coefficients across arbitrary neurons or validate our integer rounding contract against their trained models. [DSP-Packing](https://arxiv.org/html/2203.11028) already generalizes packed low-precision multiplication and discusses packed SNN additions. The [official UDP FPGA 2026 repository](https://github.com/wintermelon008/UDP) supplies configurable packed multiplication templates; the publisher paper's full text was inaccessible in this audit, so no detailed superiority or novelty claim against UDP is made. [HAPQ, Sensors 2026](https://doi.org/10.3390/s26092910) overlaps in membrane quantization, SIMD alignment and shift-friendly FPGA recurrence; only the publisher abstract/search-visible material was available here, so its hardware is not reproduced. FireFly's neuron updates and existing mixed-precision packing must remain part of a broader novelty audit. No keyword-search absence is used as evidence that no one has done the adaptive idea.

## Reproduction and evidence

The ZIP contains the four RTL sources, testbenches, independent checks, generated stimuli/outputs, numerical screen, all three existing model files, saved reference configurations, build scripts, raw route reports and failure/retry logs. Checkpoints and generated simulator binaries are omitted. Source hashes and a verified ZIP manifest accompany the files. Use the already installed Python environment with NumPy and local Vivado named in the scripts; no model, dataset or package was downloaded.

Run check_packed_leak.py, check_split_leak.py, check_fixed_lut_leak.py, check_distributed_leak.py, check_delta_packing.py and screen_leak_adaptation.py. Build the listed tops with their corresponding run_*_route.py scripts; --resume opens an existing synthesis checkpoint after a tool failure. The route scripts require more than 2.3 GiB free RAM and launch serial builds; small two-lane simulations check a lower 1.0 GiB gate. The RAM shortage early in this run cleared before the hardware queue began.
'''
(O/'leak_packing_study.md').write_text(report,encoding='utf-8')
files=[P/n for n in ['packed_leak.sv','split_leak.sv','fixed_lut_leak.sv','distributed_leak.sv','tb_packed_leak.sv','tb_split_leak.sv','check_packed_leak.py','check_split_leak.py','check_fixed_lut_leak.py','check_distributed_leak.py','check_delta_packing.py','screen_leak_adaptation.py','check_ram.py','publish_leak_study.py','run_packed_leak_route.py','run_split_leak_route.py','run_fixed_lut_leak_route.py','run_distributed_leak_route.py','route_packed_leak.tcl','route_split_leak.tcl','route_fixed_lut_leak.tcl','route_distributed_leak.tcl','route_neuron_alu_resume.tcl']]
files += [R/n for n in ['packed_leak_checks.json','split_leak_checks.json','fixed_lut_leak_checks.json','distributed_leak_checks.json','packed_leak_hardware.json','split_leak_hardware.json','fixed_lut_leak_hardware.json','distributed_leak_hardware.json','packed_leak_algebra.json','split_leak_algebra.json','delta_packing_algebra.json','leak_adaptation_screen.json','model_seed0.npz','model_seed1.npz','model_seed2.npz','final_selected.json']]
for t in required:
 files+=list((R/f'{t}_route').glob('*.rpt'))+[R/f'{t}_route'/'slack.txt']+list(R.glob(f'{t}*.log'))+list(R.glob(f'{t}*.jou'))
for folder in list(R.glob('packed_leak_*'))+list(R.glob('split_leak_*'))+[R/'fixed_lut_leak',R/'distributed_leak']:
 if folder.is_dir():files+=[f for f in folder.iterdir()if f.is_file()and f.suffix in ['.txt','.sv','.log']]
files+=list(R.glob('packed_leak_initial*'))
files=sorted(set(files));assert all(f.exists()for f in files)
manifest={str(f.relative_to(P)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest()for f in files}
z=O/'leak_packing_evidence.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED)as archive:
 for f in files:archive.write(f,str(f.relative_to(P)))
 archive.writestr('manifest.json',json.dumps(manifest,indent=2))
 archive.write(O/'leak_packing_study.md','leak_packing_study.md');archive.write(O/'leak_packing_summary.json','leak_packing_summary.json')
with zipfile.ZipFile(z)as archive:
 assert archive.testzip()is None
 for n,digest in manifest.items():assert hashlib.sha256(archive.read(n)).hexdigest()==digest
(O/'leak_packing_manifest.json').write_text(json.dumps(dict(zip_sha256=hashlib.sha256(z.read_bytes()).hexdigest(),files=manifest),indent=2))
print(json.dumps(dict(metrics=metrics,zip_bytes=z.stat().st_size,files=len(files),checks='PASS'),indent=2))
