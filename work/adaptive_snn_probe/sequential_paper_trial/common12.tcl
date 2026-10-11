# Re-time already routed, unchanged physical designs at one common operating clock.
set_param general.maxThreads 1
set fd [open [lindex $argv 0] r]
set records [split [string trim [read $fd]] "\n"]
close $fd
proc physical_signature {filename} {
 set fd [open $filename w]
 foreach cell [lsort [get_cells -hierarchical -filter {IS_PRIMITIVE}]] {
  puts $fd [list $cell [get_property REF_NAME $cell] [get_property LOC $cell] [get_property BEL $cell]]
  foreach pin [lsort [get_pins -quiet -of_objects $cell]] {puts $fd [list $pin [lsort [get_nets -quiet -of_objects $pin]]]}
 }
 close $fd
}
foreach record $records {
 lassign $record top dcp out
 if {![regexp {^top_sequential_leak_e[0-5]$} $top]} {error "Invalid top"}
 file mkdir $out
 open_checkpoint $dcp
 if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Part mismatch"}
 if {[get_property PERIOD [get_clocks clk]] != 9.0} {error "Original clock mismatch"}
 physical_signature $out/physical_before.tsv
 create_clock -name clk -period 12.0 [get_ports clk]
 set ip [get_ports -filter {DIRECTION == IN && NAME != clk}]
 set_input_delay -clock clk -max 6.0 $ip
 set_input_delay -clock clk -min 6.0 $ip
 set_output_delay -clock clk -max 1.0 [all_outputs]
 set_output_delay -clock clk -min 0.1 [all_outputs]
 report_utilization -file $out/util.rpt
 report_utilization -cells [get_cells fixture/core] -file $out/core_util.rpt
 report_timing_summary -delay_type min_max -report_unconstrained -file $out/timing.rpt
 report_timing -delay_type max -max_paths 10 -file $out/paths_max.rpt
 report_timing -delay_type min -max_paths 10 -file $out/paths_min.rpt
 set fd [open $out/slack.txt w]
 foreach kind {max min} {
  set path [get_timing_paths -delay_type $kind -max_paths 1]
  if {[llength $path] != 1} {error "No timing path"}
  puts $fd [get_property SLACK $path]
 }
 close $fd
 physical_signature $out/physical_after.tsv
 write_checkpoint -force $out/design.dcp
 puts "COMMON12_RETIMED $top"
 close_design
}
