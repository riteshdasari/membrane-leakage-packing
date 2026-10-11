# Review of the saved SNN overpacking experiment

Reviewed 8 October 2026. This is an inspection of the saved code and reports, not a new simulation or Vivado run.

## What was packed

The Python model `snn_explore/packed_lif.py` accumulates one presynaptic input at a time. If input j spikes, it adds the vector of its signed weights to independent postsynaptic neuron states. These states are packed into fields of a single 48-bit addition datapath. The state persists across timesteps and undergoes integer leakage and soft reset. The multiplication datapath is disabled in the RTL.

The final Artix-7 RTL uses DSP48E1 ONE48 mode with seven 6-bit fields, 4-bit weight increments and 5-bit side counters. The full-neuron variant contains leakage, threshold comparison and soft reset. A second variant isolates accumulation and uses shared serial readout; it has no per-lane leakage or firing unit.

## How exact recovery worked

There are no guard bits between fields, so carry or borrow can affect the adjacent field. Two-bit expected-residue references detect these transfers and side counters retain the otherwise lost information. The Python version corrects transfers serially, charging stall cycles. The later RTL accounts for the cross-lane effects without recovery stalls and reconstructs each value from its field and counters. Exactness is limited by the supported counter range and operation assumptions; counters are not infinite.

## Saved evidence

The digits experiment uses a 64-128-10 ANN converted to an IF/LIF SNN, 32 timesteps and 360 test images. The code checks membrane states and spikes against an integer reference each timestep. Saved outputs report identical reference behavior. Seven 6-bit fields with int4 weights incur roughly 2.1–5.2% modeled stall overhead in the earlier Python design. Packing weight-width fields more densely incurs substantially larger overhead.

The RTL verification log records 36 configurations with zero mismatches; disabling carry detection produces 1,637 mismatches in its mutation run.

Routed Vivado reports, Artix-7 xc7a100tcsg324-1, 4 ns target:

- 84-lane accumulate-only packed design: 1,675 Slice LUTs, 1,100 registers, 12 DSPs, WNS -0.611 ns.
- 84-lane FOUR12 baseline: 253 Slice LUTs, 594 registers, 21 DSPs, WNS -0.573 ns.
- 84-lane LUT baseline: 1,156 Slice LUTs, 1,495 registers, zero DSPs, WNS +0.770 ns.
- 28-neuron full packed design: 3,063 Slice LUTs, 711 registers, four DSPs, WNS -5.824 ns.
- 28-neuron FOUR12 baseline: 592 Slice LUTs, 182 registers, seven DSPs, WNS -1.963 ns.
- 28-neuron LUT baseline: 547 Slice LUTs, 479 registers, zero DSPs, WNS -0.124 ns.

The accumulation-only wrappers have different readout port counts. These are local microarchitecture comparisons, not matched end-to-end accelerators. The approximate clocks in the README are inferred from the target and timing slack, not measured board clocks.

The `summary.txt` helper reports zero DSPs/registers because its primitive filters are incorrect. The resource figures above come from `util.rpt`, whose DSP48E1 counts agree with the RTL instances. Primitive LUT counts in summaries also differ from combined Slice LUT counts.

## Why the direction was stopped

Packing reduced DSP count, but per-lane residue prediction, carry detection, counters and reconstruction cost more LUTs than the small LUT accumulators they were meant to replace. Adding exact leakage and threshold handling worsened area and timing substantially. Correctness was not the main reason to stop.

A separate earlier experiment, `dsp_lane_snn.py`, evaluated shared-exponent overflow-triggered shifting. The notes report that calibrated static saturation generally performed better in this small workload. This is a different, approximate mechanism from lossless counter recovery. The README's claim that saturation wins every setting is stronger than its own table: the beta=0.5, 8-bit bidirectional result is an exception. Neither its saturation argument nor its membrane-range argument establishes a general guarantee for signed SNN workloads.

The evidence rejects this particular implementation as the lead direction. It does not prove that all membrane-aware adaptive DSP packing policies fail, and it does not cover deep SNNs or newer FPGA DSP architectures.

## Inspected source directory

`C:\Users\Ritesh\Desktop\DPS_MAC\snn_explore`

Key sources: `README.md`, `packed_lif.py`, `packed_experiment.py`, `packed_results.txt`, `rtl/pk_cluster.sv`, `rtl/acc_engines.sv`, `rtl/tops.sv`, `rtl/verify_log.txt`, `rtl/impl.tcl`, and the six routed `rtl/impl_*/util.rpt` and `summary.txt` reports.
