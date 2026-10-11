# Exact U13/I8 ordered membrane-admission trial

This is a bounded extension of the frozen U11 frontier, not a full accelerator.
All six candidates receive the same eight-position source window of signed
13-bit post-leak membrane U and sign-extended signed 8-bit current I. Each
consumed lane returns the exact signed 14-bit integer U+I. No rounding,
saturation, scale changes or overflow waivers are permitted.

E0 consumes up to six full-range lanes using six radix-128 residue fields.
E1 consumes up to eight full-range lanes with late high-part recovery.
E2 consumes up to eight full-range lanes with precomputed high metadata.
E3 consumes up to eight lanes using native TWO24 DSP addition for two lanes
and LUT additions for six. E4 consumes up to eight LUT-only additions.
E5 consumes up to five full-range lanes, then an ordered prefix of at most
three extra lanes whose actual U is in [-128,127]. A rejected lane remains
at the source and is offered again in a full-range position. No reordering
or cross-neuron carry is allowed. Physical DSP residue layout is invariant.

All candidates use one ready/valid interface, four advancing-edge latency,
global pipeline freeze under output backpressure, reset cancellation,
and zero unused output lanes. The source holds the complete window when
blocked. Values in unused source positions are deliberately poisoned.

Validation includes 2,097,152 signed13/signed8 scalar pairs, simultaneous
packed boundaries, all three tail admission failure positions, reset and
stalled/unstalled runs. Original IF traces use unchanged saved weights,
thresholds, input-event generation and first 48 images per each of three
seeds. Retired RTL sums drive independent software state/spike/count feedback.
The 32-step binary-input interval certificate requires U13; it does not
certify unbounded integration. Full 360-image accuracy restoration is a
separate software check. These are three seeds of one converted ANN design,
not three independently trained SNN architectures.

Service counts include conservative group drains but generous eight-value
operand availability. A supply-two floor is reported separately; SRAM,
gather/scatter logic, threshold/reset and leakage hardware are not included.
Routed candidates share one registered OOC fixture at 6 ns on
xc7a100tcsg324-1. Its 338 FFs are excluded from core FF counts. Raw external
port timing is separate from registered fixture timing. Native exactness,
STA and routed functional replay are distinct acceptance requirements.
An incomplete or failed timing replay supplies no accepted energy result.

Existing frozen U11/F5 evidence must remain byte-for-byte unchanged.
Attempts use fresh directories; failures and tool logs are retained.
Vivado routes/exports/power are serialized and gated at 2.3 GiB free RAM.
Native simulations are gated at 1.2 GiB. No installation, download or
training is authorized by this trial.
