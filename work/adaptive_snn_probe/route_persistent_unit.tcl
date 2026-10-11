set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
set top [lindex $argv 0]
read_verilog -sv $here/persistent_unit.sv
synth_design -top $top -part xc7a100tcsg324-1 -mode out_of_context
create_clock -name clk -period 4.0 [get_ports clk]
set pre $here/results/${top}_synth
file mkdir $pre
report_utilization -file $pre/util.rpt
write_checkpoint -force $pre/design.dcp
opt_design
place_design
route_design
set out $here/results/${top}_route
file mkdir $out
report_utilization -file $out/util.rpt
report_timing_summary -file $out/timing.rpt
report_timing -max_paths 5 -file $out/paths.rpt
write_checkpoint -force $out/design.dcp
set f [open $out/slack.txt w]
puts $f [get_property SLACK [get_timing_paths -max_paths 1]]
close $f
puts "PERSISTENT_ROUTED $top"
