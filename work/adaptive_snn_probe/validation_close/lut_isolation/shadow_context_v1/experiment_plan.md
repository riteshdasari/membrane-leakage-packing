# One remaining causal experiment: live shadow of the failing CARRY4

Prepared but **not executed**. No vendor tool was launched by this preparation. The existing delayed E2 failure remains unresolved and unaccepted.

## Why this experiment

The retained full-netlist diagnostic proves a wrong settled output: at11106ns, input S_in7, CI_in0, DI_in0 and feedback0 imply O7, yet O0 is captured. The largest annotated path of this cell is579ps, while the inputs/feedback have settled for approximately6.6ns. The isolated a1 bench passes the recorded aggregate transitions and synthetic CI pulses, so it does not reproduce the full error. Its85 deduplicated input observations do not preserve the original same-time region/delta ordering. The WDB files are retained, but no source-only inspection can decode an exact simulator event-region transcript from them here.

The next bounded probe places **one shadow instance of the unchanged installed CARRY4** in the same testbench, connected directly to the live original cell's input ports. It annotates that shadow with the exact12 original IOPATH entries. This makes the existing full-netlist event source drive the diagnostic cell; it avoids inventing an order of `#0` assignments from collapsed `$strobe` data.

The original routed netlist, complete original SDF, original replay controls and row comparison remain unchanged. No signal is forced and no timing check is waived. The shadow observes the already delayed input ports, so it copies only the original cell's IOPATH delays; upstream interconnect is not reapplied a second time.

## Positive gates and samples

- Both original full SDF and diagnostic shadow/canary SDF must report successful annotation, without ignored-annotation, elaboration warning or error diagnostics.
- Library binding must explicitly compile `work.CARRY4`; its copied SHA must equal the installed vendor source and retained original copy.
- A second, independent timing canary uses the same cell paths. For a clean S0 transition, O0 must remain unchanged at200ps and change by240ps, testing the original228ps maximum S0→O0 path. This rejects accidentally functional/unannotated shadow experiments.
- Max delay, transport interconnect delays and the original zero pulse-reject/error settings remain enabled. Forbidden timing waiver/suppression flags are rejected.
- Snapshot times11100.500ns,11101.000ns,11105.999ns and11106.001ns compare independent carry truth, original/shadow outputs and feedback, time since the last internal-input/feedback event, and the destination D/Q. Capture-edge+1ps snapshots are also retained. A meaningful “settled” classification requires known matching observed input values and both stability intervals greater than579ps.
- The original row914 mismatch must reproduce before interpreting the probe as the same failure. Per-bit pin/internal event prints supply observer sequence and timestamps; that sequence is explicitly **not** an exact event-region/delta index.

## Possible outcomes

If both original and shadow remain wrong under matching known settled inputs, the annotated primitive can reproduce the Boolean discrepancy while driven by the live original event context. The exact path/feedback scheduling mechanism still needs explanation; this is stronger localization, not a hardware fix.

If only the original remains wrong, context, port-path treatment or delta propagation becomes the leading remaining distinction. A shadow port connection can change aliasing/elaboration and delta context, so this does not itself prove that the simulator is defective.

If the original failure disappears after adding the observer, retain the run as a nonreproduction. Observer/elaboration sensitivity may be relevant, but it cannot turn the old failed design into accepted evidence.

If annotation/canary/completion gates fail, reject the causal test. Do not infer a numerical result from it. Exact standalone reproduction remains unavailable unless a genuine ordered event source, or an independently sufficient precise stimulus, is later established.

## Launch when root's serial vendor window is free

`python run_shadow_context.py --run --attempt a0`

Use the existing RNvenv Python and run the script from its absolute workspace path. The runner checks all prepared/frozen sources, records imported helper and installed glbl provenance, gates each job on1.2GiB available RAM and retains every attempt. It performs one compile/elaboration/replay sequence, without synthesis, route or power. Choose a new attempt name if an earlier directory exists. A target row914 replay fatal is recorded as diagnostic evidence, never as hardware acceptance.

Prepared source, exact diagnostic SDF, hashes and source-only Python syntax checks are available. SystemVerilog elaboration remains an unexecuted gate.
