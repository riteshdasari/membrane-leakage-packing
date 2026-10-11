# Matched I8 fixed baseline specialization

This isolated trial measures fixed baselines for the same declared operation as
the frozen six-residue fixed datapath: signed11 U plus statically signed8 I,
producing the exact signed12 sum. The existing 66-bit input buses remain; each
active current is required to be sign-extended signed8. This is a domain
contract, not a runtime detector or lossless conversion of an arbitrary I11
current. The saved integer models have a separate all-binary-spikes I8 proof.

`guard_add_i8_fixed.sv` retains the retimed baseline control and four preceding
advances from acceptance to output handshake. It accepts six lanes each issue,
with masked zero output tails, global output backpressure, and synchronous
reset of all pipeline and output state. E2 uses the original unchanged FOUR12
DSP wrapper for four lanes and fabric addition for the final two; E3 performs
all six additions in fabric. Both capture fabric sums at acceptance.

The hybrid physically captures 32 current bits for its first four lanes,
instead of 44, and sign-extends each signed8 current to the DSP's 12-bit field.
Every fabric addition uses a 12-bit sign extension of the low eight current
bits and a 12-bit sign extension of U11. The output still needs 12 bits: the
full declared sum range is [-1152,1150]. No dynamic widths or correction
selection are added.

The timing file is a mechanical rename of the retimed cohort fixture: 138
preserved launch FFs and 81 preserved capture FFs, totaling 219 fixture FFs.
These are explicitly excluded from core counts. The same Artix7 part,
registered OOC clock-source placement, 6 ns target, single Vivado thread,
and separate raw-port timing audit are retained. Slice occupancy is recorded
as overlapping core and fixture sets, not subtracted as an additive resource.

Only the two new tops are routed. The verification cohort simultaneously
compares them with the unchanged fixed residue V2 and unchanged full-current
retimed hybrid E2. Reusing an old fixed-residue route is justified only after
pinning its frozen source and identical registered fixture/timing contract;
it is not a newly routed measurement. The full-current baseline is a
verification/reference check, not the matched-domain hardware competitor.

The route runner imports without launching tools. It requires completed
source-pinned RTL/stall/SNN evidence before Vivado, checks source and evidence
hashes again afterwards, and routes sequentially under a free-RAM gate.
Hardware comparison does not establish power, memory bandwidth, board Fmax,
full neuron-update latency, or preservation of accuracy for the original
trained floating/integer model after changed leakage coefficients.

No simulation or route jobs were launched by the hardware implementation
agent. Results will be produced serially by the coordinating root agent.
