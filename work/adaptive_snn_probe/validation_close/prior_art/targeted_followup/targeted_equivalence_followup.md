# Targeted primary-source access follow-up

Date:10 October2026. Targeted works: Ou2024 dynamic DSP packing, Cui2024 six signed products, UDP2026, and McKeown2008 dynamic-range utilization. This follow-up does not repeat the previously completed broad paper audit. The current E5 hardware contract is signed16 scalar fallback with the original signed9 admitted pair; widening the fallback does not create a new packing principle.

The follow-up is complete as a **bounded search**, but complete method-level equivalence remains open for the four target papers. No absence-of-prior-work or first-ever claim follows from access failure.

## McKeown2008: a substantive new primary source

The [QUB institutional record](https://pure.qub.ac.uk/en/publications/power-efficient-dynamic-range-utilisation-for-dsp-on-fpga/) provides the original abstract and DOI but its access section contains no author manuscript attachment. The shell retrieval returned403; the browser reader could inspect the institutional record. Detailed runtime admission, overflow handling, and exact numerical guarantees still could not be checked in the original six-page SiPS2008 paper.

A full follow-on paper by its coauthor **John McAllister** was obtained from the [official EURASIP EUSIPCO2009 proceedings](https://eurasip.org/Proceedings/Eusipco/Eusipco2009/contents/papers/1569193849.pdf): *Evolutionary Requirements for Next-Generation Dataflow-Based FPGA System Design*, pp.2688–2692. Section3.3 explicitly attributes its FFT example to the SiPS2008 paper(ref.13). It explains that two input streams often use less than half their worst-case word range, so fixed-point data streams can share one data word. Table3 retains throughput while reducing the multiplier count. This is direct primary evidence of range-utilization packing and its hardware motivation.

This strengthens the conceptual overlap beyond the previously accessible abstract. It does **not** reveal whether the original implementation changes packed operation count from each actual operand value, how exceptional full-range samples are handled, or whether it preserves every original integer output. Those questions remain unresolved. The follow-on uses an FFT context rather than the present rounded membrane leakage kernel; application difference alone is insufficient to establish novelty.

Bibliographic detail: the QUB record calls the first author Michael McKeown; the primary coauthor paper cites S. McKeown, and the proceedings listing uses Stephen. The earlier categorical full-name correction is not retained. Cite the original paper by DOI and initials as supported by its publisher record, pending resolution of that metadata inconsistency.

## Ou2024: full methods remain unavailable

[DOI10.1109/TCSII.2024.3377356](https://doi.org/10.1109/TCSII.2024.3377356) identifies *A119.64GOPs/W FPGA-Based ResNet50 Mixed-Precision Accelerator Using the Dynamic DSP Packing*. Targeted title/DOI searches, author/institution pages, Macau public publication lists, and public preprint discovery produced no complete primary author manuscript or code. The [author's institutional page](https://ime.um.edu.mo/zh-hans/people-zh-hans/weihan-yu/) was retrievable only as an indexed page; direct retrieval returned403/503. The existing [institutional2024 publication list](https://ime.um.edu.mo/wp-content/uploads/2025/03/NewsletterPDF_Final250211_Editable_smallWebSite.pdf) confirms the work but does not contain its packing equations.

Do not classify its dynamic packing as static per-layer precision, actual-value adaptation, or approximate packing from the title or third-party abstract. Its full packing/unpacking method and comparison with the exact ceil kernel remain unchecked.

## Cui2024 six-signed packing: full methods remain unavailable

[DOI10.1109/ICFPT64416.2024.11113473](https://doi.org/10.1109/ICFPT64416.2024.11113473) still exposes publisher metadata/abstract and a section outline, with methods requiring sign-in. Targeted title/author searches and public repository/institution discovery did not yield a primary author copy. Publisher claims about six lossless signed products and packing/unpacking resource optimization establish relevant overlap, but do not expose sufficient algebra to prove or disprove equivalence with the present quotient-only stride16 specialization. No non-equivalence is inferred from CNN evaluation.

## UDP2026: author code remains inspectable; complete paper inaccessible

[DOI10.1145/3748173.3779194](https://doi.org/10.1145/3748173.3779194) and the [corresponding author's institutional publication page](https://cs.ustc.edu.cn/2020/1203/c23239a462623/page.htm) identify UDP. The institutional page provides no manuscript link for this item. Public PDF/HTML publisher requests remain unavailable; the retained PDF response is403 HTML, not a PDF. The bounded GitHub release/tree follow-up hit the public API rate limit, so no new release availability claim is made.

The already retained [author repository](https://github.com/wintermelon008/UDP), revision `f5a6b4f2522e54a815f5026b67cf7f78b7438160`, remains the source-level evidence. Its complete released multiplier has elaboration-time widths/parallelism and runtime sign correction. The retained README has a usage placeholder and no paper download; its citation file contains no manuscript link. This released module lacks an actual-membrane pair/full admission interface. That observation cannot be expanded into a statement about all architectures or policies in the inaccessible full paper.

## Claim boundary

Retain the prior audit's narrow claim: an exact rounded membrane-leakage primitive with actual signed9 pair admission, a full signed16 fallback, fixed stored state precision, one-bit spill reconstruction, and measured implementation trade-offs. Range-based operand packing and exact correction are established ideas. A measured kernel specialization could remain publishable, but these unresolved methods prevent a blanket equivalence-closed or priority claim.

The primary coauthor PDF and extracted text are retained locally. `access_checks.json` records public retrieval outcomes and file hashes. Authentication was not attempted and restricted access was not bypassed. No vendor jobs were launched by this follow-up.
