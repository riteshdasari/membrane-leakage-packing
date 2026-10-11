# Retained validation interruption and resume

The user explicitly approved stopping and resuming our validation runners on 2026-10-10 after the cached-array performance issue was explained. The first automatic approval review rejected stopping them; no stop occurred until the user's approval arrived.

The original `energy_closure_sequence_close_a0.json` and all original source files remain unchanged. Its four completed E7 native/route stages retain their accepted receipts. The E8 pair/s0 vendor simulation completed with `LEAK_NATIVE PASS`, 140,272 requests per core and 271,866 scalar results. Its subsequent Python audit repeatedly decompressed complete NPZ arrays inside each request loop and was interrupted before producing an acceptance receipt.

Only six verified Python wrapper/worker processes belonging to `run_hardware_autoclose.py`, `run_energy_closure_sequence_v2.py`, and `run_native_static9.py` were stopped: 12448, 20916, 12560, 30124, 31484 and 17644. The public-model inference process was left running. No vendor simulator was active at this stop. Completed files were retained, without deletion or replacement.

A separate cached-array importer will recheck every saved E8 pair/s0 result, its scalar oracle, admission, frame boundaries, counts and latency, plus the completed vendor records and hashes. Its new receipt does not treat the interrupted original Python audit as completed. A new runner will reuse independently verified accepted E7 stages and run every remaining stage; the original sequence is retained as interrupted evidence, not claimed as a completed closure.
