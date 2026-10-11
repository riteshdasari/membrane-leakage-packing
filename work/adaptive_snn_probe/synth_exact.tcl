set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
foreach top $argv {
 read_verilog -sv [list $here/packed_exact_acc.sv $here/old_acc_engines.sv $here/exact_checkpoint.sv $here/exact_promote.sv $here/exact_tile.sv]
 synth_design -top $top -part xc7a100tcsg324-1 -mode out_of_context
 create_clock -name clk -period 4.0 [get_ports clk]
 opt_design
 set out $here/results/${top}_synth
 file mkdir $out
 report_utilization -file $out/util.rpt
 report_timing_summary -file $out/timing.rpt
 write_checkpoint -force $out/design.dcp
 puts "SYNTH_COMPLETE $top"
 close_design
}
