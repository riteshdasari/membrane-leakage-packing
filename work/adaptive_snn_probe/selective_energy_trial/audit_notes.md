# Measurement audit of the selective-correction energy pilot

Status: the frozen V2/V3 pilot has passed native, routed timing, interval,
annotation and estimated-power audits. The root reviewed and executed a separate
read-only audit program. Delegated agents reached usage limits before completing
an independent energy review; no such completed review is claimed. Architecture
sources, checkpoints and prior publications remain unchanged. All heavy jobs ran
serially.

## Completed result

Both variants complete the same 110,592 requests and 635,904 scalar updates.
Fixed dynamic power is 17.300 mW over 663.588 us, or 18.05315 pJ/update.
Adaptive dynamic power is 20.100 mW over 664.272 us, or 20.99667 pJ/update.
The adaptive whole-fixture dynamic estimate is 16.30473% higher. No adaptive
energy benefit is established on this saved workload. This is a vendor model,
not a board measurement or a core-only estimate. Device static power remains
separate. The decimal/export rounding checks do not bound model accuracy.

The actual replay includes two identical fixture settling cycles on top of
native service. Native service remains 110,596 versus 110,710 clocks, with
1,008 adaptive corrections and 114 freezes. Native and routed outputs match.
No timing-check suppression or SDF timing diagnostics are accepted.

Name-only SAIF repairs retain numeric activity and hierarchy. All 726 fixed
and 856 adaptive physical design nets match. Every reported simulation alias
is cross-checked against its SAIF record with zero unknown time. Clock aliases
use the identical 6 ns constraint; default aliases are audited constants.
Original SAIF unknown records remain retained and explained by their absence
from verified physical switching records. DSP enables and adaptive controller
signals are covered. The expected ignored-clock-annotation warning and medium
power advisories remain in the evidence; no activity overrides are used.

Fixed user junction temperature is 25 C for both. Vivado derives ambient values
24.539091 and 24.526316 C, respectively. Other primary operating settings match.
The existing negative raw-port hold budgets remain a board-interface limitation.

Mapped corrected_high[1]/[2] rates are 153.269/149.692 million transitions/s,
while correction_step is 3.01985 million transitions/s. Source inspection shows
no fallback operand isolation and a lane-zero default selection. These specific
net rates support an isolation experiment; they do not attribute block energy
or quantify conditional idle switching. The next implementation trial is still
unmeasured.

The remaining text records the original audit requirements and claim boundary.

## Frozen scope

The comparison is unchanged fixed residue V2 versus unchanged adaptive exact
correction V3, both signed11 U plus statically signed8 I to exact signed12 sum.
Both use the same six unsigned7 residue additions in a fixed ONE48 DSP layout;
fabric reconstructs the high part. V3 adapts correction work, not physical
DSP field width or lane count. The core source SHA256 is
`b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48`.

The frozen routed V2 DCP SHA256 is
`43edfc647d9d2b1e1bfb9a84bd8eb044f9406fab036ed5824e838904a6a252f1`;
V3 is `4dbafa3f4e40c469f39d73e2c587a96c3c1719880052f2b01cc2f1afc2655b1f`.
The same Artix7 part, 6ns target and preserved 219-FF registered fixture apply.
Both pass registered OOC timing, but the negative raw-port boundary hold
budgets remain a limitation. A replay is not a production interface validation.

## Native trace and cycle alignment

Each native row is sampled at its falling edge plus0.020ns, after the frozen
driver sets controls and before the following rising edge. The18 columns are:
idx, running, done, rst, iv, out_ready, available, Uhex17, Ihex17, in_ready,
take, out_valid, out_count, out_datahex18, mode, correction, advance and busy.
Inputs must be fed from the verified trace, regardless of delayed fixture ready.
Valid active currents obey I8; poisoned unavailable tails need not obey it.

Let E_n denote the rising edge following native trace row n. Native row n
outputs describe the state after E_(n-1). Replay launch FFs capture row n at
E_n; its core computes that row at E_(n+1); capture FFs observe the old core
output on the same rising edge. Therefore the replay fixture output sampled
while driving row n corresponds to native row n-2, after mapped delays settle.
The offset is two sampled rows, not a new native latency or adapter handshake.

The full reset/GSR prelude must be replayed at6ns, including stalled-output
reset and adaptive busy reset. Primitive GSR remains active during the initial
100ns. Useful comparisons begin only after the declared initialization gate;
no unknown, result/control mismatch or SDF violation during useful work may
be waived. Pre-initialization unknowns and timing diagnostics must be retained
and explained rather than silently removed. Drain rows must be explicit.

The useful native audit must count110,592 accepted and retired requests and
635,904 scalar updates for each core. Fixed service is110,596 clocks; adaptive
service110,710 with1,008 correction steps and114 freezes. Actual trace indices
must identify first acceptance, last retirement and the measured service span;
all correction and stall cycles must remain inside the activity interval.

## Activity and estimated power gates

Only validated mapped-netlist replay activity may support comparative energy.
For each design, preserve its exact routed DCP, exported netlist/SDF, native
trace, replay sources, simulator log, SAIF, annotation report and power settings
with hashes. Netlist/SDF export must not overwrite the archived checkpoints.
The SAIF hierarchy must map the replay DUT onto the matching DCP top, including
fixture/core. Record mapped and unmatched objects, fallback/default activity,
unknown time, critical controller/DSP clock/CE coverage and relevant warnings.
A high overall match percentage alone does not prove those important nets
are covered. A logical correction bypass does not automatically gate switching.

SAIF start, stop, time unit and duration must be independently audited against
the replay trace and the common fixture settling/drain convention. Do not infer
duration from useful native clocks or compare average powers over unequal work
without multiplying by each actual duration. Collection must close before
simulator termination; truncation, omitted exceptional clocks or significant
unknown time invalidate the comparison.

Process, voltages, temperature assumptions, clock frequency, environmental
settings and report options must be equal and recorded. Static device power
must remain separate from dynamic estimates. Estimated dynamic joules per
scalar update are dynamic watts times audited SAIF seconds divided by635,904.
Both total joules and joules/update should be reported with sufficient numeric
precision to resolve a small difference; report rounding may limit conclusions.

Whole-fixture dynamic estimates include all219 preserved fixture FFs. A core
hierarchy breakdown is a separate estimate only when hierarchy attribution is
trustworthy. Do not subtract fixture power using FF/resource fractions or
call a whole-fixture result core-only energy. Clock/OOC and vendor power-model
limitations remain explicit; this is not board power measurement.

## Claim boundary

No adaptive energy benefit is presumed. A V3/V2 benefit would still require
unfavorable/backpressure cases and matched I8 hybrid/LUT comparators before a
broad superiority claim. A negative result is evidence. Saved beta231 replay
equivalence is not preservation of original trained-model accuracy. Neither
energy estimation nor absence of an identical configuration establishes novel
arithmetic or first-ever adaptive packing.
