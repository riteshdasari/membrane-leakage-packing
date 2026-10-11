# Shared contract: common-layout exact membrane addition

This is one coordinated arithmetic study, not separate accelerator projects.
Keep original, layout_trial and baseline_retime_trial evidence immutable.
All agents work toward the mechanism below; propose a change to root before
changing the operation, packing algebra, interface, workload or baseline.

## Required operation and common representation

- Six ordered signed11 membrane operands U and signed11 currents I.
- Each output is exact signed12 U+I, with unused output lanes zero.
- Decompose U=128*hU+rU, I=128*hI+rI, where r is unsigned7 and h is signed4.
- ONE48 DSP always receives six isolated eight-bit fields {0,r}.
- Field result s=rU+rI is unsigned8. c=s[7], low=s[6:0].
- Exact signed5 high result is H=hU+hI+c. Output is {H[4:0],low[6:0]}.
- This layout never shifts lane positions and never discards significant bits.

## Two reinforcing tasks

The hardware task builds a strong fixed common-layout reference. It explores
small alternative placements of the exact high-part addition/carry correction
and measures the whole kernel. The adaptation task uses the same algebra to
determine whether actual U/I can safely reduce correction work, issue slots,
or resource requirements. Both use the exact same full integer domain.

A constant six-lane DSP layout is NOT variable DSP lane-count packing. If the
adaptation changes only high-part correction, name it adaptive exact correction
for packed DSP addition. Do not claim that unchanged lane packing became adaptive.
An advantage may be a measured resource/latency/exactness tradeoff; novelty or
more DSP work alone is not an advantage. Do not hide the strong fixed hybrid.

## Baselines and common evidence

- Native fixed4: 25 LUT /240 FF /1 DSP, saved model159540 service clocks.
- Retimed hybrid6: 66 LUT /248 FF /1 DSP, model110596 clocks.
- Retimed LUT6: 79 LUT /304 FF /0 DSP, model110596 clocks.
- Prior adaptive V1:130 LUT /247 FF /1 DSP, model115758 clocks.
- These are local kernels, not reproduced FireFly results.
- Reuse original check_guard_add.py frames/model_frames and saved references.
- Required: full signed range, order, tails, reset, stalls, integer exactness.
- Fixed variants retain original ports and four-advance latency. Proposed
  multi-cycle adaptive correction must declare its latency/throughput contract
  explicitly; root must approve its interface before RTL implementation.
- Vivado2025.2, xc7a100tcsg324-1, same6ns/219FF registered fixture.
- Root alone runs heavy jobs, serially, with RAM gates (simulation1.2GiB,
  routing2.3GiB). Agents do not download, launch HDL tools or alter user apps.

## Ownership and integration

- Root owns this contract, verification integration, job queue and publication.
- Hardware agent owns guard_add_common.sv and hardware notes only.
- Adaptation agent owns screen_common_adaptation.py and policy results/notes only.
- Audit agent is read-only unless root grants specific verifier-file ownership.
- Send findings to root and the counterpart; agree on one candidate before
  changing scope. Every result must distinguish proof, simulation, synthesis,
  route, ideal service modeling and actual measurements.
