# Public SNN model check and paper decision

The current adaptive addition core still does not establish a strong adaptive efficiency contribution. This stage adds a real public trained-model reference and numerical applicability checks; it does not claim public-model integer hardware or a FireFly accelerator reproduction.

## Executed public benchmark

The official [GLIF repository](https://github.com/CAS-CLab/Gated-LIF) was pinned at commit `60638b28ff8b688b51867e7dd44f1e065d4892b0`. The published ResNet18 CIFAR10 T2 channel-wise checkpoint was downloaded and verified against its Git blob, then loaded with Torch weights_only=True and strict model keys. Original model code and pinned SpikingJelly0.0.0.0.10 were used in the local Torch CPU runtime. GLIF is a learned gated LIF variant, not vanilla LIF or AdEx.

All10,000 original held-out CIFAR10 images were evaluated, in order, without training or changing neuron equations. Accuracy is **94.03% (9403/10000)**. The repository's T2 ResNet18 table reports94.19%; local difference is -0.1600 percentage points. This is floating-point reference accuracy, not packed-integer accuracy.

Runtime was 13.80 minutes using8 CPU threads and batch4. The minimum sampled free RAM was 4.00GiB. CPU inference speed is not a hardware-packing throughput result.

The original test archive passed its provider-compatible SHA256 and MD5 checks. Only its test_batch member was read, using a restricted unpickler. A64-image slice was separately instrumented across17 neuron layers: **159,383,552 updates, zero observer state/spike disagreements**. The full unmodified run reproduced this original-pixel pilot's first64 logits bit for bit. This checks passive observation of floating arithmetic; no quantized or RTL state was fed back into this public model.

## Numerical compatibility

The pilot declared four illustrative integer-unit screens before inference. They independently round observed pre-add membrane contributions and effective currents to nearest even. They do not define an accuracy-preserving integer neuron model, safe hardware widths or full-test range statistics.

- 16 units per membrane unit: U8 eligibility 100.000000%; I8 eligibility 100.000000%; currents outside I8 0/159,383,552.
- 64 units per membrane unit: U8 eligibility 100.000000%; I8 eligibility 99.996268%; currents outside I8 5,948/159,383,552.
- 256 units per membrane unit: U8 eligibility 99.231884%; I8 eligibility 89.616686%; currents outside I8 16,549,294/159,383,552.
- 1024 units per membrane unit: U8 eligibility 76.258761%; I8 eligibility 36.920590%; currents outside I8 100,538,205/159,383,552.

At scale64 all observed membrane contributions fit int8, yet5,948 currents do not, across15 layers. At scale16 both operands fit in this pilot, which alone does not establish an adaptive packing benefit or a legal model-wide bound. In all68 observed layer/unit cases, U-only narrowing while retaining the globally required current width saves no high-base metadata under the current formula. A joint U/current or high-sum admission policy is a different implementation and needs its own proof and fair controls.

An independent real-arithmetic envelope screen covers all permitted image pixels and binary intermediate spikes. It indicates wider possible currents in12 of17 layers even at scale16, and all17 at finer scales. It is deliberately labeled a real-valued screen: floating rounding and a new integer neuron contract are not certified by these envelopes. No current was clipped to make the existing I8 RTL fit.

The checkpoint also has real learned leakage coefficients. None of7,808 channel/previous-spike coefficient contexts falls inside the old delta0..25 near-identity regime after illustrative nearest-Q8 mapping; none falls inside delta0..31. Coefficient231 and its old7–20% issue-slot estimate cannot be assigned to this model. No Q8 GLIF model or quantization-accuracy result is being claimed.

## Hardware conclusion preserved

For the earlier certified integer addition domain, adaptive uses 121 LUT,47 FF,1 DSP and 49 touched slices. The strongest fixed native FOUR12+four-LUT hybrid uses 87 LUT,49 FF,1 DSP and 30 slices. All5 routes and6 native cohorts passed in that bounded trial; its newly specialized energy remains unmeasured.

For the separately measured original generic-U11 fixture, adaptive dynamic energy was 9.3411% higher than the strongest fixed hybrid. That vendor fixture estimate is not public-model, newly specialized core or board energy. Fixed8's retained timed failure has no accepted energy; its later mapped-functional diagnostic passes92,186 complete trace rows and does not waive timing or energy.

Fixed8 is already request-minimal for this eight-addition interface. New workloads can expose a resource/energy frontier or applicability gap, but cannot make an at-most8-operation controller require fewer requests than legal fixed8. Exact output preservation is required; it is not an accuracy improvement over an already exact fixed implementation.

## Data-source failure retained

The first quick pilot used dataset-viewer image URLs. They supplied lossy JPEG previews, despite local .png filenames. The original-pixel identity gate rejected183,349 of196,608 pixel entries, with maximum error95 and mean absolute error6.0583. Labels matched. All preview inference,81.25% pilot accuracy and its operand interpretation are excluded as original CIFAR10 benchmark evidence and remain retained. The original-pixel pilot and full run are separate files; no result was silently replaced.

A concurrent provider-range transport attempt reported TLS EOF and an initial recovery attempt found missing chunk23. Separate retries completed the missing data and accepted only the full original archive hashes. A first range-screen script used the wrong nested residual-module key; version3 checks the actual original-pixel pilot. The original failed sources and artifacts remain. Superseded owned wait/download jobs were stopped after verification; no user application or global Python environment was changed.

## What this work enables next

The exact decomposition, controllers, range certificates, replay harness and strong fixed controls remain reusable. This broader benchmark identifies numerical requirements for the next mechanism. It does not yet offset the current controller's hardware cost with a measured advantage.

The next bounded primitive trial must start from a declared integer LIF leakage operation with application-backed coefficients, independently checked float-to-integer accuracy, exact packing, actual stream statistics and strong zero-bypass/fixed-DSP/constant-LUT controls. The gates are saved in [next_operation_gate.md](../work/adaptive_snn_probe/public_model_trial/next_operation_gate.md). This can stay a small packing/controller paper; no full accelerator is required.

Vanilla directly trained LIF/event-network integer traces, public-model RTL replay, a complete AdEx integer reference, new-specialization timed energy and board measurements remain unexecuted. An inspected Lava integer MNIST tutorial uses dv=0 in its classifier layers, so it is not evidence for an intrinsic nontrivial leakage multiplication. Novelty remains qualified; no exhaustive first-ever claim or ISCAS acceptance prediction is made.
