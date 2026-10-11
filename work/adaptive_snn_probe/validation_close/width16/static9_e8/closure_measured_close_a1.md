# Signed9 static packing cost ablation

All four explicit E8 native cohorts and the selected E5/E8 matched routes passed independent source and artifact verification. Both routes use16-bitports,12ns and94 fixtureFFs; E8 input values must signextend from9bits.

E5 core: 62 LUT, 44 FF,1 DSP. E8 core: 47 LUT, 36 FF,1 DSP.

E5−E8: +15 LUT, +8 FF, +0 DSP. This is the combined admission/full-width-support cost; it is not literal controller-only overhead.

E8 is a narrow-domain ablation. It has no wide fallback and supplies no full16 baseline or energy result.

E5 route: `C:\Users\Ritesh\Documents\Codex\2026-10-08\oka\work\adaptive_snn_probe\validation_close\width16\hardware\route12_e5_a0\hardware.json`. E8 route: `C:\Users\Ritesh\Documents\Codex\2026-10-08\oka\work\adaptive_snn_probe\validation_close\width16\static9_e8\hardware\route12_e8_close_a1\hardware.json`.

Exact evidence: `C:\Users\Ritesh\Documents\Codex\2026-10-08\oka\work\adaptive_snn_probe\validation_close\width16\static9_e8\closure_measured_close_a1.json`.
