set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
set top [lindex $argv 0]
set pre $here/results/${top}_synth
if {[lindex $argv 1] eq "resume"} {
 open_checkpoint $pre/design.dcp
} else {
 read_verilog -sv $here/stream_fold_leak.sv
 synth_design -top $top -part xc7a100tcsg324-1 -mode out_of_context
 create_clock -name clk -period 4.0 [get_ports clk]
 file mkdir $pre
 report_utilization -file $pre/util.rpt
 write_checkpoint -force $pre/design.dcp
}
opt_design
place_design
route_design
set out $here/results/${top}_route
file mkdir $out
report_utilization -file $out/util.rpt
report_utilization -hierarchical -file $out/hierarchical_util.rpt
report_timing_summary -file $out/timing.rpt
report_timing -max_paths 5 -file $out/paths.rpt
write_checkpoint -force $out/design.dcp
set f [open $out/slack.txt w]
puts $f [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
puts $f [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
close $f
set inputs [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_input_delay -clock clk -max 1.0 $inputs
set_input_delay -clock clk -min 0.1 $inputs
set_output_delay -clock clk -max 1.0 [all_outputs]
set_output_delay -clock clk -min 0.1 [all_outputs]
report_timing_summary -file $out/boundary_timing.rpt
report_timing -from $inputs -max_paths 8 -file $out/input_paths.rpt
report_timing -to [get_ports take*] -max_paths 5 -file $out/take_paths.rpt
set f [open $out/boundary_slack.txt w]
puts $f [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
puts $f [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
close $f
puts "STREAM_OFFSET_ROUTED $top"
