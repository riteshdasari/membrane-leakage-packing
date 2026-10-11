# Isolated F5 exact membrane-prefix follow-up

This sibling trial changes only adaptive engine E5 from six full-range lanes
plus two signed8 membrane tails to five full-range lanes plus three signed8
membrane tails. The original six-engine sources, native outputs, routes, SAIF,
power evidence and publication files remain immutable. Root executes all heavy
jobs serially after finishing the original six-engine measurement queue.

Every engine retains the common signed11 U plus statically sign-extended signed8
I to exact signed12 result contract. Input buses U/I are88bits, available/take
are4bits, out_data is96bits, out_count4bits. Available is0..8; source holds raw
data until accepted. Accepted requests consume exactly take ordered operands.
Results have zero unavailable tails. Four advancing edges, global output stall,
stable blocked output and reset cancellation are unchanged. No approximation,
overflow loss, rounding, layout switch, shared correction or busy scheduler.

E0..E4 retain the original datapaths and take policies. E0 wraps frozen
guard_add_selective.V2 and consumes min(available,6). E1/E2 are full-range
fixed8 late/precomputed high recovery. E3 is FOUR12 plus four fabric sums; E4
is eight fabric sums. The new native checker additionally requires their
retirement files to be byte-identical to the corresponding passed original
native cohort, including ordered outputs and physical clocks. These engines
are simulated for regression, but are not rerouted or repowered in this folder.

E5 keeps eight6bit DSP fields of unsigned5bit residues and a fixed lane map.
For U=32hU+rU and I=32hI+rI, residue sum<=62, carry=bit5 and low=bits4:0.
Lanes0..4 precompute a signed7 high base hU+hI; lanes5..7 precompute a signed4
base only for admitted U8/I8. The DSP carry is added later. Full outputs are
{signed7 high,low5}; admitted narrow outputs are exact signed9 sign-extended
to12. Full-domain high lies[-36,35], narrow high[-8,7]; no significant bit is
discarded. Invalid tail computations are hidden by output count masking.

E5 takes min(available,5), extending consecutively through lanes5,6,7 only while
the corresponding actual U fits[-128,127]. It stops at the first inadmissible
tail. No consumed full-width membrane is narrowed. This supports the full
ordered U11/I8 stream by consuming smaller prefixes as needed. narrow_mode is
the current combinational (E5 && take>5), independent of in_valid/out_ready;
other engines report0. This is exact actual-membrane-aware lane admission.

The registered timing fixture is identical to the original:183 preserved
launchFFs plus107 captureFFs=290. Same attributes, core boundary, 6ns clock,
Artix7 xc7a100tcsg324-1, HD.CLK_SRC BUFGCTRL_X0Y0, one Vivado thread, same flow.
Only E5 physical jobs are allowed by this runner. Report core resource vectors,
registered setup/hold and separate raw-port timing. Only passing timing DCPs
may enter slow-SDF activity/power. No candidate-only retiming or clock relaxation.

The route replay clock delays its first rising edge from3ns to9ns, retaining
the same3mod6ns rising phase, falling-edge phase and6ns period thereafter.
This phase-preserving startup settling delay is applied before GSR ends and
before the126ns first replay drive. It changes no ROI or useful clock count.
No timing-check waiver or suppressed timing warning is permitted. The original
failed startup replay remains separate evidence; root uses the same replay
startup conditions for the corresponding original engine measurements.

Run all four native cohorts: saved models/stress with ready output and stalls.
Stress includes all524288 scalar U11/I8 pairs plus existing mixed boundaries,
prefix transitions, poisoned unavailable tails and reset cancellation. Saved
work retains635904 updates/9216 dependent groups/144 images/three seeds under
the unchanged beta231 integer reference, including threshold/reset state,
spike/count/class checks. Original trained-model accuracy is not claimed.

The F5 screen predicts83006 requests/119870 saved service clocks, equal to F6,
but104097 requests/115049 stress clocks versus F6 at87964/98916. These predicted
counts need the new RTL check. Show the unfavorable case. The potential extra
12 logical register-bit reduction compared with F6 is not a synthesis or energy
prediction: F5 adds one actual-U predicate and prefix selection complexity.

Supply2 analytically limits every engine to min(available,2), giving317952
requests plus36864 group-drain clocks=354816 saved service clocks. The original
six-engine supply2 RTL control is separately measured. This folder includes an
optional same-core F5 supply2 native control for root if needed; no physical
memory/window buffer is modeled and eight-wide delivery costs remain visible.

Energy uses exact routed DCP+slowSDF, recorded complete useful interval plus two
fixture settling cycles, exact naming-only SAIF normalization, full physical
alias/constant/clock audit, typical process/nominal rails/userTj25C. Static is
separate. Whole290FF-fixture vendor estimates are not core/board/fullSNN energy.
Root compares against immutable original fixed8/hybrid/LUT/F6 evidence under
matched conditions and equal scalar work. All failed/negative results remain.

Novelty of this prefix admission rule, generality and a strong ISCAS contribution
remain separate checks. No publication-strength conclusion follows merely from
the residue identity, exactness, a unique lane split or the favorable saved trace.
