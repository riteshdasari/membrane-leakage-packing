# Predeclared public vanilla-LIF validation

This validation uses the authors' OTTT-SNN NeurIPS 2022 VGG11 weight-standardized
CIFAR-10 checkpoint, unmodified weights, the official test normalization, ordered
held-out test images, T=6, tau=2, threshold 1 with equality firing, and immediate
subtractive reset. The FP32 original remains the reference accuracy baseline.

Integer-neuron conversion alone uses membrane/current unit 1/256. Effective FP32
synaptic currents are rounded nearest-even to integer units; leakage is
ceil(128 U/256). Threshold is 256 and reset subtracts 256 in the same timestep.
Convolutions, weight standardization and readout remain FP32. No retuning,
retraining, clipping, replacement leak, altered timestep or range normalization
is allowed after observing packing rates.

The E5 executor selects adjacent equal-coefficient signed9 pairs when both actual
stored membranes fit [-256,255], and otherwise an exact signed12 singleton.
Zero operations are bypassed equally by every counted implementation. Original
neuron order is retained. Packed arithmetic must feed the state update before
threshold/reset, and every leakage result is checked against independent ceil
arithmetic. Integer-vs-packed logits, spikes and states must match exactly.

Values outside signed12 are kept exactly in a scalar software exception path and
counted; they are not represented as validated hardware support. The aggregate
state domain remains checked signed24, matching the earlier software contract.
This separates primitive applicability from state/accuracy preservation.

Tau=2 is a mandatory negative control: the declared leakage is ceil(U/2), so a
wire shift with a rounding bit is an exact baseline and does not need a DSP.
High DSP utilization does not establish an advantage over that shift circuit.

The first 64 test samples are a diagnostic, not a full accuracy result. Full
10,000-example testing is attempted after runtime and memory profiling. The
checkpoint's saved max accuracy is metadata, not our reproduced inference result.
