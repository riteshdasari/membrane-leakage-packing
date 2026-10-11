set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
foreach top $argv {
 open_checkpoint $here/results/${top}_synth/design.dcp
 create_clock -name clk -period 4.0 [get_ports clk]
 place_design
 route_design
 set out $here/results/${top}_route
 file mkdir $out
 report_utilization -file $out/util.rpt
 report_timing_summary -file $out/timing.rpt
 set fp [open $out/slack.txt w]
 puts $fp [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
 close $fp
 puts "ROUTE_COMPLETE $top"
 close_design
}
