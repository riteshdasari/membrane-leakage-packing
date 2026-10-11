# UDP primary-method inspection

The complete twelve-page [ACM article](https://dl.acm.org/doi/epdf/10.1145/3748173.3779194), printed pages212–223, was inspected in its normal public reader. No original PDF was downloaded; the JSON records rendered-page coverage rather than inventing a PDF checksum.

Sections3.1–3.3 describe direct, offset and clip mappings, signed correction, and most-negative-activation handling. Section4 chooses packing parallelism from specified widths and DSP port constraints. Sections5.1–5.3 generate parameterized Chisel hardware and describe fixed-format cascading and high/low fusion across two DSPs. Section6 evaluates MAC workloads and distinguishes exact correction from optional approximate omission.

Runtime sign/value corrections exist. They must not be conflated with the configuration of operand widths and parallelism. This inspected method does not describe selecting signed9 membrane pairs versus exact signed16 singleton execution from actual membrane values. It nevertheless supplies substantial ancestry for exact signed packing and high/low reconstruction. Its discussion of Cui does not replace inspection of Cui's original method. Generic adaptive packing, fixed splitting and first-ever novelty are not established contributions of our work.

This closes the UDP full-method inspection gap only. Ou, Cui and McKeown remain unresolved originals; the bibliography and paper should retain that boundary.
