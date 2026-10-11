# Common-layout hardware reference

This core is a fixed six-lane exact arithmetic reference for the coordinated
study in CONTRACT.md. Its DSP operand layout never changes at runtime.
Adaptive work must use this same representation and establish a separate
benefit from actual membrane/current values.

## Algebra and full-domain bounds

For every signed11 value X, the input bit split satisfies
X = 128*hX + rX, where hX is signed4 in [-8,7] and rX is unsigned7
in [0,127]. Each immutable eight-bit DSP field receives {0,rU} and {0,rI}.
Its sum s is in [0,254]; therefore a field never spills into its neighbor.
With c=s[7] and low=s[6:0], U+I=128*(hU+hI+c)+low.
The corrected high value is in [-16,15] and fits signed5 exactly. The final
concatenation {corrected_high[4:0],low[6:0]} is signed12 in [-2048,2046].

The signed4 high values are explicitly extended to signed5 before adding.
The residue carry is also explicitly typed signed5 with value 0 or 1.
No halving, truncation, stochastic rounding, saturation, or exponent is used.

## Two placements, one operation

- V0 computes signed5 hU+hI from the current inputs at acceptance. It carries
  this 30-bit metadata through high0/high1/high2, then increments by the DSP
  residue carry at output. This minimizes high metadata width but needs two
  arithmetic placements, before capture and after the DSP.
- V1 captures both signed4 highs, carries the 48-bit metadata through three
  stages, and computes hU+hI+c at output. It gives synthesis a combined
  three-operand high addition. A lower LUT count or better timing is a
  hypothesis; its wider metadata has a clear register cost.

Nominal external register count before synthesis: V0 262 and V1 316.
The accounting is 84 residue capture bits + (90 or 144) high metadata bits
+ 72 output bits + 12 count bits + four valid bits. DSP-internal registers
are excluded from this count, as in the matched baseline accounting.
These are source-level counts, not synthesis or route results.

## Pipeline and interface

At the acceptance edge, residue and high stage0 capture current U/I. One
advancing edge later, DSP A:B/C and high stage1 capture. At the next edge,
DSP P and high stage2 capture. At the following edge, the output register
captures the exact reconstructed sums; the output handshake can occur on
the fourth advancing edge after acceptance. This matches the original
guard_add fixed E2/E3 contract.

The advance condition is !out_valid || out_ready. All external stages and
the reused guard_add_dsp wrapper freeze together under backpressure. Reset
clears every stage and valid bit. take=available, narrow_mode=0; accepted
requests consume all available ordered lanes. Binary poisoned unavailable
input lanes cannot influence valid lanes because the DSP fields are isolated.
The output count masks unused output lanes to zero.

## What this trial can establish

The strong matched references are retimed fixed hybrid six-lane and retimed
LUT-only six-lane addition. Those already need the minimum number of service
requests for this interface. This common layout cannot save service clocks
relative to them because it also consumes up to six lanes per request.
Its possible benefits are exact packed-DSP coverage of all six full-range
lanes and a measured resource/timing tradeoff. Moving every lane into a DSP
does not by itself establish efficiency or an application advantage.

The fixed common-layout core must pass the full signed domain, tail masking,
stalls, reset, saved workload replay, and matched 6 ns route before reporting
hardware results. The adaptation screen may identify a way to reduce high
correction work or hardware on actual-U workloads. An unchanged six-lane
DSP layout should be called adaptive exact correction if only correction
changes; it is not variable lane-count DSP packing.

This agent created only guard_add_common.sv and this note. No HDL tools,
heavy jobs, models, downloads, or prior evidence were modified or launched.
