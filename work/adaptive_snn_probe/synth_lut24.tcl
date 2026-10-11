set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
read_verilog -sv [list $here/lut_full24.sv $here/old_lut_cluster.sv]
synth_design -top top_lut_full24 -part xc7a100tcsg324-1 -mode out_of_context
create_clock -name clk -period 4.0 [get_ports clk]
opt_design
set out $here/results/top_lut_full24_synth
file mkdir $out
report_utilization -file $out/util.rpt
report_timing_summary -file $out/timing.rpt
write_checkpoint -force $out/design.dcp
