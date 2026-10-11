# Shared GLIF coefficient control

This experiment adds a fair checkpoint-specific zero-DSP comparator to the
generic E7 LUT pair. It preserves the full signed16 membrane domain and both
independent runtime coefficient inputs. The declared coefficient set contains
all 33 trained values: 74..88 and 153..170. All 33 appear in the frozen
262,528-operation representative capture.

The trained checkpoint has 3,904 channels and 149 distinct (beta0, beta1) pairs.
These pair counts do not imply that 149 arithmetic engines are instantiated.
One shared two-lane engine accepts the entire existing stream, with exactly the
same upstream channel/previous-spike coefficient selection as E5 and E7. No
standalone channel area is averaged or treated as a whole-model hardware cost.

The comparator uses beta = 80 + delta or 160 + delta. For the complete trained
set, delta lies in -7..10. A lane computes 3U, 5U, 7U and 9U with constant
shift/add operations, obtains the remaining absolute-delta multiples through
wiring shifts, selects a multiple, and adds or subtracts it from 80U or 160U.
It then forms the exact ceiling quotient using the product's arithmetic floor
and a nonzero-remainder increment. All intermediates retain sufficient signed
width. There is no rounding approximation or membrane-dependent packing.

The existing two-advancing-edge elastic protocol, ordered consumption, two
output lanes and 94-FF timing fixture are retained. Coefficient selection and
source memory stay outside the primitive for every compared implementation.

Preparation checked 2,162,688 mathematical signed16/coefficient cases with
zero mismatches and independently recovered every captured coefficient from
its saved layer, raw index and previous-spike bit. This is arithmetic and
provenance validation; RTL, route and energy acceptance require the following
separate jobs. The completed receipt is `preparation.json`.

Run native exhaustive and representative checks in unstalled and stalled
configurations. Use separate attempt directories; retain every failed attempt:

```powershell
& C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe -B work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/run_native_glif_mcm.py --cohort exhaustive --stall 0 --attempt a0
& C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe -B work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/run_native_glif_mcm.py --cohort actual_glif --stall 0 --capture --attempt a0
& C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe -B work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/run_native_glif_mcm.py --cohort exhaustive --stall 1 --attempt a0
& C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe -B work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/run_native_glif_mcm.py --cohort actual_glif --stall 1 --attempt a0
```

After the unstalled receipts pass, route the matched fixture at 12ns:

```powershell
& C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe -B work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/run_route_glif_mcm.py --exhaustive-acceptance work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/hardware/native_exhaustive_s0_a0/acceptance.json --actual-acceptance work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/hardware/native_actual_glif_s0_a0/acceptance.json --attempt a0
```

Only a passed route with zero DSPs, all 94 fixture FFs and nonnegative setup and
hold slack qualifies for the subsequent exact full-interconnect SDF replay and
SAIF energy comparison. Native acceptance alone gives no physical timing or
energy result. The capture should require 131,328 issues, matching the E7 pair.

This is one concrete optimized checkpoint-specific baseline. Its measurement
does not prove that no other LUT or multi-constant circuit can be better. A
per-channel fully replicated implementation would need a separate system-level
budget and workload service model, outside this primitive comparison.
