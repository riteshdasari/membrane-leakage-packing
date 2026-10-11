# Export the matching isolated route; no optimization or checkpoint mutation.
set_param general.maxThreads 1
if {[llength $argv] != 2} {error "dcp outdir"}
lassign $argv dcp out
open_checkpoint $dcp
if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Part mismatch"}
if {[llength [get_clocks]] != 1 || [get_property PERIOD [get_clocks]] != 12.0} {error "Clock mismatch"}
report_clocks -file $out/clocks.rpt
report_property [current_design] -file $out/design_properties.rpt
write_sdf -force -mode timesim -process_corner slow $out/routed.sdf
write_verilog -force -mode timesim -sdf_anno true -sdf_file $out/routed.sdf $out/routed.v
puts "FRONTIER_EXPORT PASS"
