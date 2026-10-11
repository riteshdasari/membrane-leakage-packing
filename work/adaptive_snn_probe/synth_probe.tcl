set here [file dirname [file normalize [info script]]]
set top [lindex $argv 0]
set kind [lindex $argv 1]
set_param general.maxThreads 1
read_verilog -sv [list $here/guard_acc.sv $here/old_acc_engines.sv $here/shared_neuron.sv]
if {[file exists $here/shared_neuron_pipe.sv]} {read_verilog -sv $here/shared_neuron_pipe.sv}
if {[file exists $here/reuse_neuron.sv]} {read_verilog -sv $here/reuse_neuron.sv}
if {$kind == "full"} {
 read_verilog -sv [list $here/old_pk_cluster.sv $here/old_ff_cluster.sv $here/old_lut_cluster.sv $here/old_tops.sv]
}
synth_design -top $top -part xc7a100tcsg324-1 -mode out_of_context
create_clock -name clk -period 5.0 [get_ports clk]
opt_design
set out $here/results/${top}_synth
file mkdir $out
report_utilization -hierarchical -file $out/util_hier.rpt
report_utilization -file $out/util.rpt
report_timing_summary -file $out/timing.rpt
write_checkpoint -force $out/design.dcp
puts "SYNTH_COMPLETE $top"
