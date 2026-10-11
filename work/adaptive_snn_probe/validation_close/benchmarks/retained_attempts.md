# Retained integration diagnostics

The first adapter attempt individually reconstructed every packed leak exactly,
but integer reference and packed executions differed downstream. A one-image
per-step diagnostic verified identical loaded weights and first-layer states,
then differences of one integer current unit beginning at layer2. The NumPy
packed decoder returns contiguous tensors, whereas Torch arithmetic preserved
the channels-last convolution layout. Different FP32 CPU convolution paths
occasionally straddled nearest-even current-quantization ties.

Version2 of the integer adapter explicitly returns contiguous spike tensors for
both integer variants. This does not change the integer neuron equation or
rounded leak. It fixes the common FP32 synaptic execution path for a strict
integer-vs-packed comparison. The FP32 original model is unmodified. Attempt0
and diagnostic attempt1 remain retained and cannot support an exactness claim.
