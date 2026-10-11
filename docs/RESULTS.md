# Current results and scope

These values come from accepted matched 12 ns routes and distribution-gated representative energy captures. Energy means common-fixture dynamic pJ per scalar operand at 25 C. The94 fixture FFs are excluded from core area and included in energy. The core excludes source memory and full neuron integration.

## Core resources and representative GLIF energy

- E1 fixed split: 202 LUTs, 79 FFs, 1 DSPs. GLIF energy: 55.3083846 pJ/scalar.
- E3 scalar pair: 35 LUTs, 56 FFs, 2 DSPs. GLIF energy: 21.3710653 pJ/scalar.
- E4 scalar: 13 LUTs, 29 FFs, 1 DSPs. GLIF energy: 24.6483755 pJ/scalar.
- E5 adaptive: 62 LUTs, 44 FFs, 1 DSPs. GLIF energy: 21.5994968 pJ/scalar.
- E7 general LUT: 330 LUTs, 88 FFs, 0 DSPs. GLIF energy: 124.1983064 pJ/scalar.
- E9 shared GLIF constants: 375 LUTs, 82 FFs, 0 DSPs. GLIF energy: 96.75809861043393 pJ/scalar.

E6 beta 128 half-shift uses 35 LUTs,70 FFs andzero DSPs. OTTT representative energies: E5 adaptive26.5796283, E1 fixed36.8075674, exact E6 shift13.6576240 pJ/scalar. BNTT beta 253 constant hardware/energy remains unmeasured. E8 narrow-only47 LUTs/36 FFs/one DSP cannot replace the full domain.

## Benchmark and claim scope

GLIF ResNet18/CIFAR10/T2: full 10,000-image integer conversion accuracy94.05% versus floating94.03%, with 371 changed predictions. Packed feedback covers 64 images and 159,383,552 updates with exact integer states/spikes/logits.

OTTT VGG11/CIFAR10/T6: full 10,000-image packed feedback covers 24,576,000,000 leakage updates with zero differences. Integer/packed accuracy93.45% versus floating93.49%, with 104 conversion-changed predictions. Exact half-shifting beats adaptive energy13.6576 versus 26.5796 pJ/scalar.

BNTT-style VGG11/TinyImageNet/T30: predeclared64-image subset covers 1,171,783,680 exact packed updates. Floating/integer counts are42/64 and 41/64. This is not full-test accuracy. The coefficient253 shift/add identity is exact, but its hardware remains unmeasured.

The model conversions are not lossless against FP32. Packing introduces no additional differences from the declared integer reference. Source memory, zero-filter hardware and variable-consumption source integration remain outside measured core costs. Energy is estimated common-fixture dynamic energy, not board/static/full-neuron energy. No universal burst-latency, accuracy or whole-accelerator claim follows.

Original LUT E2 remains excluded after delayed replay failed. Independently accepted E7 preserves the general LUT comparison. Three original full methods remain unavailable, delimiting first-ever claims rather than forbidding a scoped manuscript. Same-admission full-product-decoder ablation and optimal constant synthesis remain unmeasured.

