# Trained-model benchmark follow-up

The existing local models are three seeds of one64-128-10 converted digits
network. They are not MNIST, three independent architectures, directly trained
deep SNNs, or a reproduced FireFly workload. The original shift3/T32 control
and its full360-example accuracy must remain separate from changed coefficient
and horizon variants.

Published examples establish suitable coverage. [FireFly](https://arxiv.org/html/2301.01905v5)
evaluates SCNNs on MNIST,CIFAR10,CIFAR100,DVS-CIFAR10 and DVS-Gesture.
[FireFly-S](https://arxiv.org/html/2408.15578v1) pairs SCNN5,SCNN7,SCNN9 with
MNIST,DVS-Gesture,CIFAR10. [FireFly v2](https://arxiv.org/html/2309.16158)
includes CIFAR-Net and residual SNN benchmarks. These are whole accelerator
evaluations; their reported throughput cannot be assigned to our addition core.

For this small primitive paper, the proposed model coverage is one trained
LIF CNN on a static image task(CIFAR10), one trained LIF event network on
DVS-Gesture(or CIFAR10-DVS), and a simple MNIST LIF control if a compatible
checkpoint is available. This selection is a research recommendation, not an
ISCAS rule or a claim that any number of benchmarks guarantees acceptance.
AdEx single-neuron firing patterns are a separate component-applicability
experiment, not a classifier benchmark or substitute for trained SNNs.

The [official SpikingJelly DVS tutorial](https://spikingjelly.readthedocs.io/zh-cn/latest/tutorials/en/classify_dvsg.html)
provides a LIF network and training procedure. The
[original PLIF repository](https://github.com/fangwei123456/Parametric-Leaky-Integrate-and-Fire-Spiking-Neuron)
states that its trained checkpoints are not uploaded. Its code and logs are
not a downloaded trained-model benchmark. A
[CIFAR10 ANN-to-SNN example](https://github.com/fangwei123456/spikingjelly/blob/master/spikingjelly/activation_based/ann2snn/examples/resnet18_cifar10.py)
does publish an ANN checkpoint download; this would be a conversion/IF
experiment, not automatically the mentor's LIF model or FireFly's trained SNN.

Local inventory found no CIFAR/DVS/MNIST checkpoint or dataset in this
workspace. Torch and torchvision are available; SpikingJelly and Brian2 are
not installed. No large training job, dataset download, framework replacement
or external-model inference has been performed in this bounded follow-up.

## Admission gate before a new benchmark can validate hardware

Pin model code, trained checkpoint, dataset version, held-out split,
preprocessing, neuron equation, threshold/reset, leakage, bias and timestep.
Keep original sample/neuronal order. Declare integer units and rounding before
observing adaptive eligibility. If quantizing a floating-point model, report
the float-to-integer accuracy change separately from hardware preservation.

Derive each layer's legal input-current and membrane ranges from its actual
weights, bias and dynamics. Check both operands and the sum. Do not clip a
wider current to int8 to fit the current RTL. A convolutional layer may have a
larger fan-in and require more than eight current bits; that layer needs a
new exact declared operation and equally strengthened controls, or must be
reported as outside the present primitive. Splitting a wide current into
multiple additions changes issue counts and must not trigger threshold/reset
between the pieces.

Export a ledger containing model/sample/layer/timestep/neuron identifiers,
postleak membrane, current, reference sum, updated state and spike. Replay all
five implementations against the same ledger, then feed their actual retired
sums into the reference state update. Verify every sum,state,spike and class;
matching classification alone is insufficient. Report original-reference
accuracy and hardware disagreements separately. Exact packing is expected to
preserve outputs, not improve accuracy.

Report runtime eligible fraction, prefix length histogram, exception frequency,
ordered service clocks, useful updates/request, stalls and burst latency. Price
the detector, high-part metadata, output decoding and clocking. Keep fixed8
exact DSP,native SIMD hybrid,full LUT and same-policy adaptive LUT. Use the
same proven numerical contract, natural latency,device and clock; static
model-specific bounds must benefit all controls. Vendor fixture energy is
distinct from core-only/board/end-to-end energy.

Use all declared held-out inputs, including quiet and high-activity cases. A
burst subset can be a labeled stress test, but may not replace the full test
set or be selected solely because it favors adaptation. Artificially tiled
single-neuron traces do not become a trained network benchmark.

For this addition interface,fixed8 already attains the minimum requests per
ordered group. A new model can reveal a resource/energy tradeoff or numerical
applicability; it cannot make a controller accepting at most8 additions use
fewer requests than a legal fixed8 design. A claim of speedup needs a different
measured bottleneck or explicitly equal resource budget, with the unrestricted
fixed control still shown. Novelty alone does not establish that advantage.
