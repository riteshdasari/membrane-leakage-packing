# Final contribution boundary for the leakage primitive

Prepared 2026-10-10 from the completed primary-paper/released-source audit; no additional broad literature search. Current full-width fallback is signed16, superseding the signed12 historical audit target. Admitted pair operands remain signed9, coefficients remain unsigned beta0–256, and the exact operation remains `L_beta(U)=ceil(beta*U/256)`.

## Defensible claim

The contribution can be described as a specialized, exact leakage primitive that selects a pair or scalar issue from actual membrane range while retaining the same integer membrane representation, and evaluates that selection against strong fixed-DSP and exact-LUT implementations. Its technical supporting results are the proven admission/decoding contract, an economical one-bit spill reference and narrow quotient correction, and measured implementation/workload trade-offs. Priority for that exact conjunction is not established. Novelty cannot come from renaming a generic operand-range detector a membrane detector.

The proposed formulation excludes spike-activity prediction, precision rescaling, overflow mantissa/exponent changes, exactness against FP32 neurons, and an unmeasured full accelerator contribution. Model-specific cheap leakage controls remain relevant even if the architecture supports a general runtime coefficient.

## Stride16 and the DSP48E1 25-bit input: what it does and does not prove

For admitted U0,U1 in−256…255, define:

`q0=beta*U0+255`, `q1=beta*U1+255`,

`A=(U0+256)+(U1<<16)`, `C=255-256*beta+(255<<16)`.

Then `P=A*beta+C=q0+(q1<<16)`. A fits signed25. The bounds `−65281<=q0<=65535` imply that the low16 field contributes either no spill or a borrow of one: `n=[q0<0]`. From the parity of `T=floor(P/65536)=q1−n`, one obtains:

`n=bit16(P) XOR (((beta&1)&(U1&1)) XOR 1)`.

The implemented rounded leakage results are recovered by eight low quotient bits plus n for the lower signed9 result, and a signed9 upper quotient with an increment only if `n=1` and `T mod256=255`. This is a compact decoder specialized to the declared rounded outputs.

A conventional nonoverlapping full 9×9 product layout uses stride18, requiring27 input bits for the signed9 upper operand. Under the present restricted coefficient domain, the complete unrounded product range is actually−65536…65280 and fits signed17; tightening that straightforward layout to stride17 still requires26 input bits. Both straightforward layouts exceed DSP48E1's25-bit multiplier input. This observation is device/layout-specific: DSP48E2 has a27-bit input.

**Neither26 nor27 is a universal lower bound for exact full-product packing.** The same stride16 P and recovered n also allow exact reconstruction of both complete rounded numerators:

`q0=(P mod65536)-65536*n`,

`q1=floor(P/65536)+n`.

Subtract255 from each to recover both full unrounded `beta*Ui` products. Thus exact full products can also use this overlapping layout with wider reconstruction logic. The defensible distinction is **cheap narrow quotient decoding for leakage**, not a claim that discarding the low8 bits uniquely enables exact two-lane packing on a25-bit port. Generic spill correction is established prior work.

## Actual membrane admission has direct conceptual prior art

David Brooks and Margaret Martonosi, *Value-Based Clock Gating and Operation Packing: Dynamic Strategies for Improving Processor Power and Performance*, ACM Transactions on Computer Systems18(2),89–126, May2000, [DOI10.1145/350853.350856](https://doi.org/10.1145/350853.350856); [full author paper](https://mrmgroup.cs.princeton.edu/papers/dbrooks-tocs2000.pdf), Sec5.1–5.2 and6.2. Their actual-value narrowness detector packs operations at issue and retains normal full-width execution; overflow replay is also discussed. This prevents a broad novelty claim for “detect actual narrow values and otherwise run wide.” Their evaluated ALU operations do not specify this rounded shared-coefficient membrane-leakage decoder.

John McAllister, *Evolutionary Requirements for Next-Generation Dataflow-Based FPGA System Design*, EUSIPCO2009,2688–2692, [official full proceedings paper](https://eurasip.org/Proceedings/Eusipco/Eusipco2009/contents/papers/1569193849.pdf), Sec3.3/Table3. The full paper directly attributes range-utilization FFT stream packing to McKeown et al., SiPS2008. It strengthens the prior conceptual overlap but does not expose the original paper's full runtime admission/exception details.

## Arithmetic ancestry and runtime DSP adaptation

Jan Sommer, Akif Özkan, Oliver Keszocze and Jürgen Teich, *DSP-Packing: Squeezing Low-precision Arithmetic into FPGA DSP Blocks*,2022, [primary manuscript arXiv2203.11028](https://arxiv.org/html/2203.11028), SecIV–VI andVII. Arbitrary-width product layouts, signed contamination/correction, overlap and SNN addition packing are established. E5's bit-level reconstruction is an arithmetic specialization, not a new general packing/correction principle.

Titus Bornträger, Shane Fleming, Philipp Holzinger, Dietmar Fey, Michaela Blott and Thomas B. Preußer, *Arithmetic Packing on Wide Integer Datapaths in DSP Primitives of Modern FPGA Devices*,2026, [primary manuscript arXiv2606.11065](https://arxiv.org/html/2606.11065), SecIII-B/C/D andV. Signed packing, modulo-reference exact spill reconstruction and DSP-low/fabric-high arithmetic partitioning are close predecessors. Their inspected real-time workload-dependent packing discussion is future work, but that does not erase older actual-value packing or other runtime-DSP work.

Feng Yu, Hongshi Tan, Yao Chen, Weng-Fai Wong and Bingsheng He, *XtraMAC: An Efficient MAC Architecture for Mixed-Precision LLM Inference on FPGA*,2026, [primary manuscript arXiv2605.06052](https://arxiv.org/html/2605.06052), SecIII-C/IV/VI. Runtime datatype switching controls packing in a shared integer-mantissa MAC architecture. Hence “adaptive DSP packing” by itself is too broad a novelty claim. E5 instead retains its stored integer contract and selects lane count from actual U values.

## Fixed-split version: supporting implementation and control

The fixed E1 split follows the ordinary quotient decomposition:

`U=256*h+l`, with `h=floor(U/256)` and `0<=l<=255`,

`ceil(beta*U/256)=beta*h+ceil(beta*l/256)`.

Its packed unsigned low8 terms have safe stride16 fields and share the DSP; exact high contributions are formed in fabric and added back. It admits both full16 operands when coefficient/availability permits, without inspecting U narrowness. This supplies an exact, strong fixed control and an implementation trade-off worth reporting. **The current evidence does not establish a separate strong-paper novelty claim for that decomposition.** Arithmetic Packing's low-DSP/high-fabric split is related ancestry; ordinary distributivity and integer quotient decomposition already explain the identity. Treat E1 as the constructive fixed baseline/supporting result unless a further independently novel implementation result is demonstrated.

## Limits of equivalence closure

Full methods remain unavailable for Ou et al.'s2024 dynamic DSP accelerator [DOI10.1109/TCSII.2024.3377356](https://doi.org/10.1109/TCSII.2024.3377356), Cui et al.'s six-signed packing [DOI10.1109/ICFPT64416.2024.11113473](https://doi.org/10.1109/ICFPT64416.2024.11113473), and the original McKeown2008 dynamic-range paper [DOI10.1109/SIPS.2008.4671768](https://doi.org/10.1109/SIPS.2008.4671768). UDP's full paper [DOI10.1145/3748173.3779194](https://doi.org/10.1145/3748173.3779194) is also inaccessible, although its [complete released multiplier source](https://github.com/wintermelon008/UDP) at revision `f5a6b4f2522e54a815f5026b67cf7f78b7438160` was reviewed. That module uses elaboration-time widths/parallelism and runtime sign correction; its released interface does not implement actual-U pair/full admission. No claim about every policy in the unavailable paper follows.

These explicit access gaps preclude “first ever,” “no one has done it,” or “final equivalence fully closed.” The bounded review supports carefully scoped comparison and related-work statements; it does not prove absence of equivalent prior art.
