# Specific contribution and prior-work boundary

A new integrated mechanism can contribute without inventing every building block. This work combines an overlapping rounded-leakage decoder, actual-membrane admission and exact signed16 singleton fallback in a measured one-DSP primitive.

Value-based narrowness detection and operation packing have prior work: Brooks and Martonosi, DOI 10.1145/350853.350856. DSP-Packing (arXiv:2203.11028) establishes packed arithmetic and signed correction. Arithmetic Packing (arXiv:2606.11065) covers exact spill reconstruction. XtraMAC (arXiv:2605.06052) covers runtime datatype packing. These building blocks are explicitly credited.

FireFly uses fixed12-bit SIMD spike accumulation and shift leakage. Our constructed controls execute the same leakage operation as E5. Their numbers are not FireFly accelerator reproductions. UDP (DOI 10.1145/3748173.3779194) supplies relevant configuration and correction ancestry, but its inspected full methods do not describe this actual-U pair/singleton policy.

Original full methods remain unavailable for Ou (10.1109/TCSII.2024.3377356), Cui (10.1109/ICFPT64416.2024.11113473) and McKeown (10.1109/SIPS.2008.4671768). This review supports a specific implemented contribution. It does not prove worldwide first-ever status. No publication acceptance or network-accuracy gain is claimed.
