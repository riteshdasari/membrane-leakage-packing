# Reproduce the two exact SNN engines

Python needs NumPy; Vivado 2025.2 was used on Windows. No model, dataset or package download was performed. Original Desktop source files were not modified. Dataset/model snapshots needed for existing inference are included.

1. `python exact_inference.py`: all 36 full-test inference comparisons, using saved int4 models/calibrated thresholds. Does not retrain or require a board. Results: `results/exact_inference.json`.
2. `python check_exact_tiles.py`: 54 matched real-UNISIM engine cases. Edit the VIV path for your installation; the script checks at least 2 GiB free RAM. Leave QUICK/TRACE unset for the full run. Results: `results/exact_tile_checks.json`. Static packing is checked only with valid bounded inputs. Each driver supplies identical vectors when its core is ready.
3. `vivado -mode batch -source synth_exact.tcl -log results/exact_synth.log -journal results/exact_synth.jou -tclargs top_exact_checkpoint top_exact_promote top_exact_native top_exact_static top_exact_lut`
4. `vivado -mode batch -source route_probe.tcl -log results/exact_route.log -journal results/exact_route.jou -tclargs top_exact_checkpoint top_exact_promote top_exact_native top_exact_static top_exact_lut`

The RTL files are packed_exact_acc.sv, old_acc_engines.sv, exact_checkpoint.sv, exact_promote.sv, exact_tile.sv, and tb_exact_tile.sv. The portable functional boundary is `exact_tile`; top_exact_* are timing-only shells, not elastic host interfaces. See the report for numerical bounds, handshake, memory/power and paper-comparison limits. Synthesized DCPs and simulator databases are excluded; reproduce them with the above commands.

Model provenance/training and the older scheduling estimates are in probe.py, base.py, final_selected.py and final_selected.json. That JSON's scheduling model is not the new RTL's measured latency. build_exact.py regenerates two derived modules from the included earlier guard_acc.sv/shared_neuron_pipe.sv; regeneration is optional.

SHA256SUMS.txt covers all packaged files except itself. Reports and the consolidated exact_snn_results.json are at the archive root. This package does not claim a full network implementation, a FireFly reproduction, measured board throughput, host performance or measured power.
