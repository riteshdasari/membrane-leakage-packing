"""Independent, lightweight scalar/source review; never launches HDL tools.

This checks the exact prepared source transformation, all U11/I8 scalar pairs,
and the combinational write-enable implication. It does not replace sequential
RTL equivalence, backpressure/reset tests, routing, SDF, or activity/power audits.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import itertools
import json
import re

P = Path(__file__).resolve().parent
FROZEN = P.parent / "common_layout_trial" / "guard_add_selective.sv"
ISOLATED = P / "guard_add_selective_isolated.sv"
FROZEN_SHA = "b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_review():
    assert sha(FROZEN) == FROZEN_SHA, "Frozen baseline changed"
    original = FROZEN.read_text(encoding="utf-8")
    actual = ISOLATED.read_text(encoding="utf-8")
    old_header = "module guard_add_selective #(parameter integer V=0)("
    new_header = "module guard_add_selective_isolated #(parameter integer V=3, parameter integer ISOLATE=1)("
    old_arithmetic = """  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  assign corrected_high=selected_hu5+adjustment;"""
    new_arithmetic = """  // Output use remains guarded by correction_step. This weaker enable
  // avoids extending the out_ready/output_space timing cone into arithmetic.
  // During backpressure with an exceptional output it intentionally stays on.
  wire isolation_enable=v2&&(|work_mask);
  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  wire signed[4:0]isolated_hu=(ISOLATE&&!isolation_enable)?5'd0:selected_hu5;
  wire signed[4:0]isolated_adjustment=(ISOLATE&&!isolation_enable)?5'd0:adjustment;
  assign corrected_high=isolated_hu+isolated_adjustment;"""
    assert original.count(old_header) == original.count(old_arithmetic) == 1
    expected = original.replace(old_header, new_header, 1).replace(old_arithmetic, new_arithmetic, 1)
    assert actual == expected, "Prepared RTL differs beyond the two reviewed substitutions"
    assert not re.search(r"\b(?:KEEP|DONT_TOUCH)\s*=", actual, re.I), "Unexpected core preservation attribute"
    guarded_write = "if(correction_step&&selected_mask[l])out_data[12*l+7+:5]<=corrected_high;"
    assert actual.count(guarded_write) == actual.count("<=corrected_high;") == 2
    assert "wire correction_step=SHARED&&output_space&&v2&&(|work_mask);" in actual
    assert "generate if(CURRENT8&&SHARED)begin:current8_bad_correction" in actual
    assert "wire[5:0]work_mask=busy?pending_mask:bad_mask;" in actual
    timing_original = (FROZEN.parent / "guard_add_selective_timing.sv").read_text()
    timing_actual = (P / "guard_add_selective_isolated_timing.sv").read_text()
    timing_expected = timing_original.replace("guard_add_selective_timing", "guard_add_selective_isolated_timing")
    timing_expected = timing_expected.replace("guard_add_selective #(.V(V)) core", "guard_add_selective_isolated #(.V(V),.ISOLATE(1)) core")
    old_top_lines = "\n".join(f"`GUARD_ADD_SELECTIVE_TOP(top_guard_add_selective_v{v},{v})" for v in range(4))
    assert timing_expected.count(old_top_lines) == 1
    timing_expected = timing_expected.replace(old_top_lines, "`GUARD_ADD_SELECTIVE_TOP(top_guard_add_selective_isolated_v3,3)")
    assert timing_actual == timing_expected, "Timing fixture changed beyond renamed core and sole V3 top"
    return {
        "status": "pass",
        "frozen_sha256": sha(FROZEN),
        "isolated_sha256": sha(ISOLATED),
        "frozen_fixture_sha256": sha(FROZEN.parent / "guard_add_selective_timing.sv"),
        "isolated_fixture_sha256": sha(P / "guard_add_selective_isolated_timing.sv"),
        "precise_changes": ["Module rename and V=3/ISOLATE=1 defaults", "Post-selection zero isolation of hU and adjustment in the current8 shared branch"],
        "corrected_high_write_sites": 2,
        "new_core_preservation_attributes": False,
        "fixture_preservation_attributes": "Original attributes retained identically; none added for operand isolation",
        "scheduler_register_reset_and_dsp_logic": "Byte-equivalent after the two specified substitutions (newline-normalized)",
        "source_diff": "".join(difflib.unified_diff(original.splitlines(True), actual.splitlines(True), fromfile="frozen", tofile="isolated")),
    }


def scalar_review():
    checked = exceptional = fast_small_count = fast_copy_only = 0
    reconstructed_min, reconstructed_max = 0, 0
    for u in range(-1024, 1024):
        hu, ru = divmod(u, 128)
        assert -8 <= hu <= 7 and 0 <= ru < 128
        for i in range(-128, 128):
            hi, ri = divmod(i, 128)
            assert hi in (-1, 0) and 0 <= ri < 128
            sign_i = int(i < 0)
            assert hi == -sign_i
            carry, low = divmod(ru + ri, 128)
            assert carry in (0, 1)
            reference_high, reference_low = divmod(u + i, 128)
            assert reference_high == hu + hi + carry and reference_low == low
            fast_small = -128 <= u <= 127
            fast_copy = carry == sign_i
            bad = not fast_small and not fast_copy
            if fast_small:
                recovered_high = carry - int(u < 0) - sign_i
                fast_small_count += 1
            elif fast_copy:
                recovered_high = hu
                fast_copy_only += 1
            else:
                assert carry != sign_i
                adjustment = -1 if sign_i else 1
                assert hi + carry == adjustment
                recovered_high = hu + adjustment
                exceptional += 1
            assert recovered_high == reference_high
            reconstructed = 128 * recovered_high + low
            assert reconstructed == u + i and -2048 <= reconstructed <= 2047
            assert -16 <= recovered_high <= 15
            reconstructed_min = min(reconstructed_min, reconstructed)
            reconstructed_max = max(reconstructed_max, reconstructed)
            # Explicitly mirror signed five-bit operands and zero gating.
            adjustment = -1 if sign_i else 1
            ungated = hu + adjustment
            for isolate in (0, 1):
                for enable in (0, 1):
                    iso_hu = 0 if isolate and not enable else hu
                    iso_adjustment = 0 if isolate and not enable else adjustment
                    corrected = iso_hu + iso_adjustment
                    assert -16 <= corrected <= 15
                    if isolate and not enable:
                        assert corrected == 0
                    else:
                        assert corrected == ungated
                    if bad and enable:
                        assert corrected == reference_high
            checked += 1
    assert checked == 524288 and exceptional == 229376
    return {
        "status": "pass", "scalar_pairs": checked, "exceptional_pairs": exceptional,
        "fast_small_pairs": fast_small_count, "fast_copy_only_pairs": fast_copy_only,
        "sum_range": [reconstructed_min, reconstructed_max],
        "certificate": "For bad lanes c != sign(I8), hence hI+c is exactly +1 or -1; hU plus that adjustment is the exact high quotient.",
        "gating_check": "ISOLATE=1 and enable=0 produces zero; enable=1 preserves the original signed five-bit corrector. ISOLATE=0 is algebraically unchanged.",
    }


def write_implication_review():
    cases = writes = last_busy_cases = blocked_exception_cases = 0
    # Cover a superset of reachable binary controller combinations. No claim of
    # sequential state reachability follows from this combinational enumeration.
    for bad_mask, pending_mask in itertools.product(range(64), repeat=2):
        for busy, v2, out_valid, out_ready, rst in itertools.product((0, 1), repeat=5):
            work = pending_mask if busy else bad_mask
            selected_mask = work & -work
            next_mask = work & ~selected_mask
            selected_lane = selected_mask.bit_length() - 1 if selected_mask else 0
            assert 0 <= selected_lane < 6
            assert selected_mask == 0 or selected_mask & work == selected_mask
            output_space = bool(not out_valid or out_ready)
            enable = bool(v2 and work)
            correction_step = bool(output_space and v2 and work)  # SHARED=1 for V3
            branch_entered = bool(busy or v2)
            actual_high_write = bool(not rst and output_space and branch_entered and correction_step and selected_mask)
            if actual_high_write:
                assert enable
                writes += 1
            if not rst and busy and v2 and work and not next_mask and output_space:
                assert enable and actual_high_write
                last_busy_cases += 1
            if not rst and v2 and work and not output_space:
                assert enable and not actual_high_write
                blocked_exception_cases += 1
            if rst:
                assert not actual_high_write
            cases += 1
    assert cases == 131072 and writes > 0 and last_busy_cases > 0 and blocked_exception_cases > 0
    return {
        "status": "pass", "binary_combinations": cases, "actual_high_write_combinations": writes,
        "last_busy_correction_combinations": last_busy_cases,
        "blocked_exception_combinations": blocked_exception_cases,
        "implication": "Every high-part write implies isolation_enable. Last busy correction remains enabled; blocked exceptions remain enabled but perform no write; reset overrides writes.",
        "scope": "Combinational implication over a superset of reachable states; not a sequential RTL or formal reachability proof.",
    }


def review():
    return {
        "status": "pass", "reviewer": "isolation_review subagent",
        "review_script_sha256": sha(Path(__file__)),
        "domain": "V=3, ISOLATE=1; signed11 membrane plus statically signed8 current; exact signed12 sum",
        "source_review": source_review(), "scalar_algebra": scalar_review(),
        "write_implication": write_implication_review(),
        "limits": ["No RTL simulator run by this reviewer", "No sequential reset/backpressure proof", "No routing or SDF timing check", "No proof that synthesis retains isolation", "No measured switching or energy result"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Recompute and require byte-equivalent saved JSON data without writing")
    args = ap.parse_args()
    result = review()
    path = P / "review_checks.json"
    if args.check:
        assert json.loads(path.read_text()) == result, "Saved independent review differs"
    else:
        assert not path.exists(), "Preserve existing review; use --check to reproduce"
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "scalar_pairs": result["scalar_algebra"]["scalar_pairs"], "exceptional_pairs": result["scalar_algebra"]["exceptional_pairs"], "control_combinations": result["write_implication"]["binary_combinations"], "check_only": args.check}))


if __name__ == "__main__":
    main()
