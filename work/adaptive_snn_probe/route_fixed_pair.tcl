set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
foreach top $argv {
 read_verilog -sv $here/fixed_pair.sv
 synth_design -top $top -part xc7a100tcsg324-1 -mode out_of_context
 create_clock -name clk -period 4.0 [get_ports clk]
 set pre $here/results/${top}_synth
 file mkdir $pre
 report_utilization -file $pre/util.rpt
 write_checkpoint -force $pre/design.dcp
 if {[catch {opt_design} problem options]} {
  puts "OPT_DIAGNOSTIC $problem"
  puts [dict get $options -errorinfo]
  error $problem
 }
 place_design
 route_design
 set out $here/results/${top}_route
 file mkdir $out
 report_utilization -file $out/util.rpt
 report_timing_summary -file $out/timing.rpt
 report_timing -max_paths 5 -file $out/paths.rpt
 write_checkpoint -force $out/design.dcp
 set fp [open $out/slack.txt w]
 puts $fp [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
 close $fp
 puts "PAIR_ROUTE_COMPLETE $top"
 close_design
}
