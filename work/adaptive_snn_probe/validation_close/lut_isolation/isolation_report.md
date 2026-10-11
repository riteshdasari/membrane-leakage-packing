# LUT replay discrepancy: bounded isolation conclusion

The original signed12 E2 LUT implementation still fails its delayed SDF replay. This audit localizes the wrong stable value to the timing-annotated CARRY4 output; it does **not** establish the exact simulator scheduling cause or turn that failed run into accepted hardware evidence.

## Confirmed evidence

`lut_diag_a2/tool_3.log` explicitly compiles `work.CARRY4`, proving selection of the copied installed vendor source. Its SHA-256 equals `C:/AMDDesignTools/2025.2/Vivado/data/verilog/src/unisims/CARRY4.v`; the source was not modified. Full routed SDF backannotation succeeds. Both the saved a2 replay and `internal_a0` use max delay, transport interconnect delay, the original zero pulse-reject/error options, and enabled timing checks.

The routed cell `fixture/core/lut.lane[0].r_reg[11]_i_4` ties CYINIT and every DI bit to zero. The unchanged vendor implementation is:

```verilog
assign CO_fb = {CO[2:0], CI_in || CYINIT_in};
assign O = S_in ^ CO_fb;
assign CO = (S_in & CO_fb) | (~S_in & DI_in);
```

At 11099.240 ns the internal probe shows S_in=7, CI_in=0, CYINIT_in=0, DI_in=0, CO_fb=0, CO=0. The output briefly reaches the correct O=7 at 11099.489 ns, then returns to O=0 at 11099.672 ns. At the 11106.000 ns capture edge, the same inputs and feedback remain settled: the independent `S_in ^ CO_fb` expression equals 7 while the actual output O equals 0. The destination register D and Q are both 0. The run subsequently reports:

```
Fatal: REPLAY mismatch E2 row914 got6c0843fa expected6c085ffa
Time: 11126 ns
```

The longest annotated input-to-output path in that isolated cell is 579 ps, substantially shorter than the 6.6 ns settled interval before capture. This is not explained by the ordinary propagation delay of this cell alone. The saved monitor also records a same-timestamp CI pulse and multiple CO delta transitions at 11099.374 ns. The internal strobe collapses those delta states to their final value; it does not recover their event-region order.

## Isolation result and uncertainty

`run_a1` really annotates the exact original cell paths and uses the unchanged vendor model. All ten settled checks pass: stable setup, CI pulse widths 0, 1, 5, 25, 50, 100, 300, and 1000 ps, and 85 deduplicated printed input transitions from original rows910–914. A separately compiled functional control also passes all ten checks. This small isolated bench therefore **does not reproduce** the full-netlist error.

The original trace has only printed 1 ps timestamps and aggregate vector observations. It does not retain every interconnect bit's event order, continuous-assignment delta cycle, or module-path scheduling context. Consequently, the precise cause remains unresolved between full-netlist event ordering and annotated primitive/path behavior. Claiming that a simulator bug was fully reproduced or fixed would overstate the evidence.

`run_a0` is invalid as an annotated test: its runtime conditional around `$sdf_annotate` caused XSIM warning43-3371 and ignored annotation. Those outputs are functional diagnostics only. The corrected `run_a1` adds a mandatory assertion for successful annotation and absence of the ignored-annotation warning. All attempts are retained.

## Exact alternative for a fair LUT control

For every integer product p,

```
ceil(p/256) = floor(p/256) + (p mod 256 != 0)
```

Arithmetic signed right shift implements the floor, including negative p; reduction-OR of the low byte identifies a nonzero remainder. `check_ceil_identity.py` exhaustively checks all **16,842,752** signed16 U and beta0..256 cases, with zero discrepancies. The actual LUT multiplier's beta256 bypass is included. This changes only the exact arithmetic decomposition, not the numerical contract.

A signed B+1 quotient/increment sum avoids accidental unsigned expression promotion; truncation to B output bits is safe for the declared beta domain. This alternative still needs its own RTL, route, original-strength SDF replay, and representative power evidence. Its arithmetic proof does not authorize dropping timing checks, accepting original E2, or assigning energy to a failing replay.

## Scope and reproducibility

Old signed12 route results remain historical. The root experiment's common full-width domain is now signed16. `preparation.json`, `run_a1/provenance.json`, `run_a1/diagnostic.json`, `internal_a0/provenance.json`, `internal_a0/diagnostic.json`, and `ceil_identity.json` retain source hashes, artifact hashes, tool settings, and status. Vendor jobs were serialized with RAM gates; no further vendor jobs are launched by this subagent after releasing the window to root.
