"""Bind current manuscript/handoff to accepted numerical evidence, after new trial ends."""
from pathlib import Path
import datetime,hashlib,json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'outputs/mentor_handoff/repository'
W=ROOT/'work/adaptive_snn_probe/validation_close/width16';C=W/'constant_glif_readiness'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
 return h.hexdigest()
progress=read(C/'energy_recovery_a0_power_progress.json')
assert progress['status'] in ('pass_power_only_recovery_original_strict_audit','retained_power_only_recovery_failure'),progress['status']
hw=read(C/'hardware/route12_a0/hardware.json');assert hw['status']=='pass'
assert hw['core']['LUT']==375 and hw['core']['FF']==82 and hw['core']['DSP']==0
power=C/'hardware/power12_glif_mcm_energy_recovery_a0/power_audit.json'
accepted=power.exists() and read(power)['status']=='pass'
independent=C/'independent_readiness_full_a0.json'
proof=read(independent)
assert proof['status']=='pass' and proof['route_audit']['status']=='pass'
assert proof['route_audit']['sha256']==sha(C/'hardware/route12_a0/hardware.json')
if accepted:
 assert proof['energy_audit']==read(power) and proof['energy_audit']['status']=='pass'
else:
 assert progress['status']=='retained_power_only_recovery_failure' and progress['failure']
e9=read(power)['estimated_dynamic_energy_pJ_per_scalar_update'] if accepted else None
energytext=f'{e9:.3f}' if accepted else '--'
paper=ROOT/'outputs/membrane_leakage_paper_draft.tex';tex=paper.read_text()
old='E8 retains narrow packing on the same ports'
assert tex.count(old)==1
intro='E9 is a shared zero-DSP add/sub pair restricted to all 33 trained GLIF coefficient codes (74--88 and 153--170), rather than one hardwired channel. All 2,162,688 signed16/code cases and the complete captured workload pass native RTL with and without stalls. '+old
tex=tex.replace(old,intro)
old='E8 narrow only&47&36&1&--&--\\\\\\bottomrule'
assert tex.count(old)==1
tex=tex.replace(old,f'E8 narrow only&47&36&1&--&--\\\\\nE9 GLIF constants&375&82&0&{energytext}&--\\\\\\bottomrule')
old="GLIF's two fixed coefficients per channel also motivate a specialized shared constant/CSD control; its hardware/energy is currently unmeasured, so general-coefficient results do not establish checkpoint-specialized superiority."
assert tex.count(old)==1
if accepted:
 new=f"The shared 33-code GLIF constant control E9 uses 375~LUT/82~FF/zero DSP and {e9:.3f}~pJ/scalar on the same capture. This measured add/sub construction is one checkpoint-restricted alternative, not an optimality bound for specialized constants."
else:
 new="The shared 33-code GLIF constant control E9 uses 375~LUT/82~FF/zero DSP. Its delayed-replay/energy attempt failed the acceptance gate and contributes no energy. This construction is one checkpoint-restricted alternative, not an optimality bound for specialized constants."
tex=tex.replace(old,new)
old='Observation localizes its signed16 error to an inconsistent settled timed CARRY4 output captured into a register; exact event scheduling remains unresolved. '
assert tex.count(old)==1
tex=tex.replace(old,'Its timed CARRY4 discrepancy remains diagnostic, not accepted energy. ')
tex=tex.replace('External source integration, model-specialized constants and three uninspected methods delimit the result','External source integration, further constant optimization and three uninspected methods delimit the result')
paper.write_text(tex,encoding='utf-8')
sources=[paper,C/'hardware/route12_a0/hardware.json',C/'independent_readiness_native_only_a0.json',C/'energy_energy_a0_golden_export_replay_power_progress.json',ROOT/'work/adaptive_snn_probe/validation_close/manuscript_scope_audit_v4.json']
sources.append(C/'energy_recovery_a0_power_progress.json')
sources.append(independent)
if accepted:sources.append(power)
numbers=dict(GLIF=dict(adaptive_energy_pJ=21.5994968,fixed_split_energy_pJ=55.3083846,LUT_general_energy_pJ=124.1983064,scalar1_energy_pJ=24.6483755,scalar2_energy_pJ=21.3710653,
 fixed_stream_issues=42327032,adaptive_stream_issues=42785698,scalar_stream_issues=79246135),
 OTTT=dict(adaptive_energy_pJ=26.5796283,fixed_energy_pJ=36.8075674,shift_energy_pJ=13.6576240),
 E9=dict(core=hw['core'],WNS_ns=hw['WNS_ns'],WHS_ns=hw['WHS_ns'],estimated_energy_pJ=e9,accepted_energy=accepted))
assert abs((1-numbers['GLIF']['adaptive_energy_pJ']/numbers['GLIF']['fixed_split_energy_pJ'])*100-60.9472)<.0001
assert abs((1-numbers['GLIF']['adaptive_stream_issues']/numbers['GLIF']['scalar_stream_issues'])*100-46.0091)<.0001
report=f'''# Submission recommendation and mentor handoff

11 October 2026. **Proceed with a focused ISCAS leakage-primitive submission.** A specific new integrated circuit mechanism can contribute without inventing every ingredient. The retained contribution is the overlapping exact rounded-leakage decoder, actual-membrane pair/singleton admission and measured fullsigned16 trade-offs.

The evidence establishes exactness against the declared integer contract, native stalled/unstalled RTL behavior, public model feedback, matched routes and conditional estimated-energy benefits. It does not establish publication acceptance or a worldwide first-ever claim.

## Verified benefit

E5 uses62 LUT,44 FF,one DSP versus E1 fixed split202 LUT,79 FF,one DSP. GLIF64-image leakage issues fall46.0091% against one-DSP scalar and rise1.0836% against fixed split. The representative GLIF energy estimate is21.5995 pJ/scalar:12.3695% below one-DSP scalar and60.9472% below fixed split. Two-DSP scalar is near energy parity at21.3711 pJ/scalar, so E5 exchanges a small energy increase for half the DSPs.

The added shared GLIF coefficient control covers all33 trained codes and all signed16 values. Four native checks and the matched12ns route pass. Its core is375 LUT,82 FF,zero DSP; setup/hold slack is3.096/0.122 ns. {'Its complete delayed replay and independent physical activity audit pass; estimated fixture dynamic energy is '+str(e9)+' pJ/scalar.' if accepted else 'Its energy attempt remains rejected and supplies no accepted value.'} The original annotation attempt checked the Vivado design object NAME instead of its HDL TOP; an additive power-only retry preserves the original failure and unchanged replay. This is a measured construction, not proof that all specialized constant designs are inferior.

## Benchmark and claim scope

GLIF ResNet18/CIFAR10/T2: full10000-image integer conversion accuracy94.05% versus floating94.03%, with371 changed predictions. Packed feedback covers64images and159,383,552 updates with exact integer states/spikes/logits.

OTTT VGG11/CIFAR10/T6: full10000-image packed feedback covers24,576,000,000 leakage updates with zero differences. Integer/packed accuracy93.45% versus floating93.49%, with104 conversion-changed predictions. Exact half-shifting beats adaptive energy13.6576 versus26.5796 pJ/scalar.

BNTT-style VGG11/TinyImageNet/T30: predeclared64-image subset covers1,171,783,680 exact packed updates. Floating/integer counts are42/64 and41/64. This is not full-test accuracy. The coefficient253 shift/add identity is exact, but its hardware remains unmeasured.

The model conversions are not lossless against FP32. Packing introduces no additional differences from the declared integer reference. Source memory, zero-filter hardware and variable-consumption source integration remain outside measured core costs. Energy is estimated common-fixture dynamic energy, not board/static/full-neuron energy. No universal burst-latency, accuracy or whole-accelerator claim follows.

Original LUT E2 remains excluded after delayed replay failed. Independently accepted E7 preserves the general LUT comparison. Three original full methods remain unavailable, delimiting first-ever claims rather than forbidding a scoped manuscript. Same-admission full-product-decoder ablation and optimal constant synthesis remain unmeasured.

## Submission preparation

The existing manuscript uses IEEEtran conference formatting, exact contracts, circuit diagram, matched controls, honest negative cases and an AI-use acknowledgment. Its built-in compilation must be rerun after the final E9 edit. The source guards four technical/five total pages. X is the authorized author placeholder. Final submission still needs real author details and the exported PDF font/file-size/visual upload checks.

The public repository and22-slide explanatory deck provide the mentor handoff. Portable arithmetic and stalled behavioral-DSP RTL examples pass. The root-conversation export includes user-facing messages and excludes hidden reasoning/tool/system/subagent internals. Historical source hashes and absolute paths remain provenance, while the release manifest checks portable shipped files.
'''
out=ROOT/'outputs/membrane_leakage_submission_recommendation_20261011.md';out.write_text(report)
receipt=ROOT/'outputs/membrane_leakage_submission_recommendation_20261011.json'
receipt.write_text(json.dumps(dict(status='technical_scope_review_pass_submission_preparation_supported',current_draft_sha256=sha(paper),current_draft_changed=True,historical_audit_snapshot_only=True,
  author_placeholder='X',numbers=numbers,evidence_sha256={str(p):sha(p)for p in sources},missing_submission_checks=['real author metadata','exported PDF font embedding/file size/visual check'],
  acceptance_established=False,worldwide_first_ever_established=False),indent=2))
shutil.copyfile(paper,D/'paper/membrane_leakage_paper_draft.tex')
shutil.copyfile(out,D/'docs/READINESS.md');shutil.copyfile(receipt,D/'docs/readiness_receipt.json')
results='''# Current results and scope

These values come from accepted matched12ns routes and distribution-gated representative energy captures. Energy means common-fixture dynamic pJ per scalar operand at25C. The94 fixture FFs are excluded from core area and included in energy. The core excludes source memory and full neuron integration.

## Core resources and representative GLIF energy

'''
for name,lut,ff,dsp,energy in [('E1 fixed split',202,79,1,55.3083846),('E3 scalar pair',35,56,2,21.3710653),('E4 scalar',13,29,1,24.6483755),('E5 adaptive',62,44,1,21.5994968),('E7 general LUT',330,88,0,124.1983064),('E9 shared GLIF constants',375,82,0,e9)]:
 results+=f'- {name}: {lut} LUTs, {ff} FFs, {dsp} DSPs. GLIF energy: {energy if energy is not None else "unaccepted/unmeasured"} pJ/scalar.\n'
results+='\nE6 beta128 half-shift uses35 LUTs,70 FFs andzero DSPs. OTTT representative energies: E5 adaptive26.5796283, E1 fixed36.8075674, exact E6 shift13.6576240 pJ/scalar. BNTT beta253 constant hardware/energy remains unmeasured. E8 narrow-only47 LUTs/36 FFs/one DSP cannot replace the full domain.\n\n'+report[report.index('## Benchmark and claim scope'):report.index('## Submission preparation')]
(D/'docs/RESULTS.md').write_text(results)
(D/'docs/GLOSSARY.md').write_text('''# Terms used in this study

**Membrane U:** the neuron's stored numerical state. **Leakage:** decay of that state before/within the next update. **LIF:** leaky integrate-and-fire neuron. **GLIF:** a gated LIF model with learned channelwise coefficient selection.

**DSP:** a dedicated FPGA arithmetic block. **LUT:** configurable fabric logic used for comparisons, muxes and arithmetic. **FF:** a flip-flop register. These are distinct resources, so fewer DSPs alone does not prove lower total cost.

**Packing:** use one wide arithmetic operation to compute several smaller operations. **Admission:** check whether the current values legally fit that layout. **Singleton:** compute one operand using its full legal range.

**Signed9/signed16:** two's-complement integers with9/16 stored bits. **Q8 coefficient:** beta/256, with integer codebeta0..256. **Ceiling:** round toward positive infinity. **Borrow:** the -1 spill caused by a negative lower field in an overlapping representation.

**Issue:** one accepted arithmetic request. **Advancing edge:** a pipeline clock edge on which a stage advances. **Stall:** the valid/ready interface retains a result while the receiver cannot accept it. Issue counts are not complete-neuron or whole-network cycles.

**SDF:** routed timing-delay data for gate-level simulation. **SAIF:** switching-activity data used by the FPGA power estimator. **Estimated dynamic energy:** switching energy in the declared fixture. It excludes static chip consumption and unmeasured system components.
''')
print(json.dumps(dict(status='paper_and_results_updated',accepted_MCM_energy=e9,current_draft_sha256=sha(paper)),indent=2))
