# Coordinated residue-frontier validation

Root owns orchestration, hardware/power jobs and final decision. Agents own only
their assigned new files. Frozen earlier RTL, traces, reports, SAIF and checkpoints
are immutable. No downloads, installs, closed user apps or parallel heavy jobs.

All engines implement ordered signed11 U plus sign-extended signed8 current I,
with exact signed12 output. Raw windows contain up to eight consecutive neurons
from one existing layer/timestep. Do not merge across layer/timestep dependencies,
modify operands, pad membrane values or claim original trained accuracy. Models
remain the saved beta231 integer reference. Both domain and work are unchanged.

Interface: clk,rst,in_valid,out_ready; u_in,i_in each88bits; available4bits in0..8;
in_ready,take4bits; out_valid,out_count4bits,out_data96bits,narrow_mode. Every
engine accepts when in_valid && in_ready && available!=0, consumes exactly take
ordered operands, and retires exact ordered sums with zero unavailable output
tails. Four advancing clocks, same global output-backpressure freeze and reset
cancellation. Out_data/out_count hold when out_valid && !out_ready. Source data
holds until accepted; take may depend on raw inputs, independent of in_valid.

Engine IDs:
0 frozen fixed six-lane V2 via a new8-wide adapter: take=min(available,6).
1 fixed eight-lane radix32 with late high recovery (retained U/I highs).
2 fixed eight-lane radix32 with precomputed high base at acceptance and DSP carry
  merge after DSP, independently measured to avoid a weak fixed8 baseline.
3 fixed eight-output hybrid: four native FOUR12 DSP lanes plus four LUT sums.
4 fixed eight-output LUT-only signed11+signed8 sums.
5 adaptive prefix capacity, common radix32/8fields, precomputed high base:
  first6 lanes support full U11; lanes6/7 use only U8 (I is staticallyI8).
  take=min(available,6), extended to7 if valid lane6 U fits signed8, extended
  to8 if lane6 AND lane7 fit signed8. No consumed wide tail is narrowed.
  Invalid tail values may be arbitrary. Extended lanes compute exact signed9
  sums sign-extended to12 via four-bit high recovery. First6 compute signed12.
  No layout switching/shared corrector/busy controller; lane count adapts to
  actual membrane tail eligibility. narrow_mode=(take>6) is descriptive only.

Both radix32 schemes use eight6-bit fields with five-bit unsigned residues.
U=32hU+rU; I=32hI+rI; DSP s=rU+rI<=62; H=hU+hI+s[5]; result={H,s[4:0]}.
Full high sum H is signed7; precomputed hU+hI is signed7. Narrow U8/I8 high
sum H is signed4 and results require signed9 extension to12. Precomputed high
base uses signed4 in narrow tail lanes, signed7 in all full lanes. use_dsp=no
for fabric arithmetic. Original guard_add_dsp wrapper reused unchanged.

Fixture for EVERY engine exposes same88+88 input and96 output buses, preserved
unconditional launch/capture FFs with original KEEP/DONT_TOUCH/SHREG_EXTRACT
attributes and unchanged preserved core boundary. Expected183launch+107capture
=290fixtureFF. Input rst/valid/ready3 +payload176 +available4; output ready/valid2
+take/count8 +payload96 +mode1. Core counts exclude290FF; slice sets nonadditive.
Artix7 xc7a100tcsg324-1,6ns OOC clk HD.CLK_SRC BUFGCTRL_X0Y0,1Vivadothread.
Same implementation flow, no candidate-only retiming/clock relaxation. Report
registered setup/hold and separate raw-port1nsmax/.1nsmin budgets. Preserve
failed routes. Only timing-pass DCPs may enter slow-SDF replay/power.

Native tests must compare to independent plain integer U+I at retirement,
preserve order/tails, check reset/busy-output cancellation and stalls, record
accepted/retired physical clocks and cycle traces. Cover full524288scalar pairs,
radix/range boundaries and mixed packed lanes plus saved635904modelupdates.
Both no-backpressure and output-stall modes. Model grouping128hidden/10output
per image/timestep, confirmed against source metadata before use. Never flatten
alloffline image identities into one hardware state bank. Record supply and
storage costs: fixture/raw-window supply is an upper-bound bandwidth condition;
also count minimal clocks for a fixed physical two-neuron supply under the same
dependent groups. Do not call issue savings arrival-burst or fullnetworklatency.

Energy: replay native pin trace through exact routed DCP+slowSDF at6ns, no timing
waivers. Capture all useful work and equal fixture settling cycles using actual
SAIF interval. Name-only normalization, full physical annotation/net/pin/constant
audit, nominalrails typicalprocess25C userTj; static separate. Report whole290FF
fixture estimate, not core-only/board energy. Compare equal scalar work. No
energy ordering without audit. Root RAM gates native1.2GiB and route/power2.3GiB.

Decision: measure the fixed width/capacity frontier first. AdaptiveE5 only earns
a contribution claim through measured area/resource or energy tradeoff versus
strong fixed8E1/E2/hybrid/LUT and fixed6, with delivery/range/latency costs visible.
Prior-art novelty and generality remain independent checks; no first-ever claim
from a unique configuration or keyword-search absence. Complete all scheduled
checks and label unavailable/failed ones explicitly before final paper verdict.
