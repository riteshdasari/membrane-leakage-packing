set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
foreach top $argv {
 open_checkpoint $here/results/${top}_route/design.dcp
 set inputs [get_ports -filter {DIRECTION == IN && NAME != clk}]
 set_input_delay -clock clk -max 1.0 $inputs
 set_input_delay -clock clk -min 0.1 $inputs
 set_output_delay -clock clk -max 1.0 [all_outputs]
 set_output_delay -clock clk -min 0.1 [all_outputs]
 set out $here/results/${top}_route
 report_timing_summary -file $out/boundary_timing.rpt
 report_timing -from $inputs -max_paths 5 -file $out/input_paths.rpt
 report_utilization -hierarchical -file $out/hierarchical_util.rpt
 set mon [get_cells -quiet -hierarchical -filter {NAME =~ *narrow_q_reg*}]
 if {[llength $mon]>0} {
  report_timing -from [get_ports {u_in[*]}] -to [get_pins -of_objects $mon -filter {REF_PIN_NAME == D}] -max_paths 5 -file $out/range_monitor_paths.rpt
 }
 set f [open $out/boundary_slack.txt w]
 puts $f [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
 puts $f [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
 close $f
 puts "BOUNDARY_CHECKED $top"
 close_design
}
