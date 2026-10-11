# Declared application-backed integer neuron contract

Source: the pinned official channelwise GLIF ResNet18 CIFAR10, two time steps, commit 60638b28ff8b688b51867e7dd44f1e065d4892b0. GLIF is a gated LIF-family model, not vanilla LIF or AdEx. The convolution, batch normalization and readout remain in original FP32; only neuron arithmetic and stored membrane are quantized. No retraining or weight conversion is performed.

One membrane unit is 1/256 of the source model's voltage unit. Learned FP32 parameters define a0=1-alpha*(1-tau), a1=a0*(1-gamma), bias=(1-alpha)*leak, reset=(1-gamma)*reVth and the original threshold. beta0 and beta1 are nearest-even rounded Q8 versions of a0/a1. Bias, reset and threshold are nearest-even rounded into membrane units. Effective input current is computed by the original FP32 gating expression and then rounded nearest-even into these units.

For previous spike p in {0,1}:

    L = ceil(beta_p * U / 256)
    U_next = L + I - B - R*p
    spike = (U_next > Theta)

There is no additional immediate membrane reset. The original model subtracts its previous-spike reset term on the following update. U and p start at zero for each inference, as in the original code. The two previous-spike coefficient contexts are quantized separately; their exact values come from the trained model, not an invented common coefficient.

The declared software interface accepts signed24 U and current. Python/Torch int64 intermediates prevent arithmetic wrap. Every executed current, old membrane and next membrane is checked against signed24; no clipping, saturation, stochastic rounding, mantissa/exponent conversion or rescaling is used. Full-test observed maxima are workload evidence, not legal-width proofs for every possible image.

The selected rounding rule deliberately defines a new integer reference. Its difference from the original floating-point model must be reported. Later packed leakage must equal L for every accepted integer input; that requirement does not imply identical spikes or accuracy to the floating-point model.

Tests: exhaustive beta=0..256 with U=-4096..4095 against independent signed integer division; full first-batch neuron states/spikes against NumPy arithmetic; all 10,000 original test images against the saved floating reference predictions. The same unit and Q8 coefficients are retained regardless of accuracy. These tests are not hardware execution.
