# Terms used in this study

**Membrane U:** the neuron's stored numerical state. **Leakage:** decay of that state before/within the next update. **LIF:** leaky integrate-and-fire neuron. **GLIF:** a gated LIF model with learned channelwise coefficient selection.

**DSP:** a dedicated FPGA arithmetic block. **LUT:** configurable fabric logic used for comparisons, muxes and arithmetic. **FF:** a flip-flop register. These are distinct resources, so fewer DSPs alone does not prove lower total cost.

**Packing:** use one wide arithmetic operation to compute several smaller operations. **Admission:** check whether the current values legally fit that layout. **Singleton:** compute one operand using its full legal range.

**Signed9/signed16:** two's-complement integers with 9/16 stored bits. **Q8 coefficient:** beta/256, with integer code beta 0..256. **Ceiling:** round toward positive infinity. **Borrow:** the -1 spill caused by a negative lower field in an overlapping representation.

**Issue:** one accepted arithmetic request. **Advancing edge:** a pipeline clock edge on which a stage advances. **Stall:** the valid/ready interface retains a result while the receiver cannot accept it. Issue counts are not complete-neuron or whole-network cycles.

**SDF:** routed timing-delay data for gate-level simulation. **SAIF:** switching-activity data used by the FPGA power estimator. **Estimated dynamic energy:** switching energy in the declared fixture. It excludes static chip consumption and unmeasured system components.
