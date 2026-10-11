# Matched registered timing fixtures. Port timing is audited AFTER the registered
# design is placed/routed; it is not substituted for the clock-to-clock result.
set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
set top [lindex $argv 0]
set target [lindex $argv 1]
set provenance [lindex $argv 2]
set mode [lindex $argv 3]
if {$mode ni {fresh resume}} {error "Invalid checkpoint mode"}
if {![regexp {^top_sequential_leak_e[0-5]$} $top]} {error "Invalid timing fixture top"}
if {![string is double -strict $target] || $target != 6.0} {error "Invalid clock target"}
if {![regexp {^[0-9a-f]{64}$} $provenance]} {error "Missing source provenance hash"}
set trialout [lindex $argv 4]
if {$trialout eq ""} {error "Missing trial attempt directory"}
# The synthesis checkpoint is unchanged; provenance and SHA are verified by runner.
set checkpoint [lindex $argv 5]
if {$checkpoint eq ""} {error "Missing pinned original synthesis checkpoint"}
open_checkpoint $checkpoint
if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Part mismatch"}
set ip [get_ports -filter {DIRECTION == IN && NAME != clk}]
# Exact declared external replay phase: falling edge, +3 ns from prior rising edge.
# This is a fixture integration contract, not an arbitrary board input budget.
set_input_delay -clock clk -max 3.0 $ip
set_input_delay -clock clk -min 3.0 $ip
set_output_delay -clock clk -max 1.0 [all_outputs]
set_output_delay -clock clk -min 0.1 [all_outputs]
opt_design
place_design
route_design
set out $trialout
file mkdir $out
set core [get_cells fixture/core]
if {[llength $core] != 1} {error "Core hierarchy was not preserved"}
report_utilization -file $out/util.rpt
report_utilization -hierarchical -hierarchical_depth 10 -file $out/hierarchical_util.rpt
report_utilization -cells $core -file $out/core_util.rpt
report_timing_summary -delay_type min_max -report_unconstrained -file $out/timing.rpt
report_timing -delay_type max -max_paths 10 -file $out/paths_max.rpt
report_timing -delay_type min -max_paths 10 -file $out/paths_min.rpt
set src [get_cells -hierarchical -filter {IS_PRIMITIVE && NAME =~ fixture/src_* && REF_NAME =~ FD*}]
set sink [get_cells -hierarchical -filter {IS_PRIMITIVE && NAME =~ fixture/sink_* && REF_NAME =~ FD*}]
if {[llength $src] != 47 || [llength $sink] != 31} {
 error "Fixture FF preservation failed: launch=[llength $src], capture=[llength $sink], expected 47/31"
}
report_timing -from $src -delay_type max -max_paths 10 -file $out/launch_paths_max.rpt
report_timing -from $src -delay_type min -max_paths 10 -file $out/launch_paths_min.rpt
report_timing -to $sink -delay_type max -max_paths 10 -file $out/capture_paths_max.rpt
report_timing -to $sink -delay_type min -max_paths 10 -file $out/capture_paths_min.rpt
proc write_slack {filename} {
 set f [open $filename w]
 foreach dtype {max min} {
  set p [get_timing_paths -delay_type $dtype -max_paths 1]
  if {[llength $p] != 1} {error "No $dtype timing path"}
  puts $f [get_property SLACK $p]
 }
 close $f
}
write_slack $out/slack.txt
write_checkpoint -force $out/design.dcp

# Occupied SLICE sites are sets, not an additive resource. Record shared sites
# explicitly rather than subtracting the fixture slice count from total slices.
proc slice_sites {cells} {
 set sites {}
 foreach cell $cells {
  foreach site [get_sites -quiet -of_objects $cell] {
   if {[string match "SLICE_*" $site]} {lappend sites $site}
  }
 }
 return [lsort -unique $sites]
}
set allprim [get_cells -hierarchical -filter {IS_PRIMITIVE}]
set coreprim {};set fixtureprim {}
foreach cell $allprim {
 if {[string match "fixture/core/*" $cell]} {lappend coreprim $cell} else {lappend fixtureprim $cell}
}
set totalsites [slice_sites $allprim]
set coresites [slice_sites $coreprim]
set fixturesites [slice_sites $fixtureprim]
set sharedsites {}
foreach site $coresites {if {[lsearch -exact $fixturesites $site] >= 0} {lappend sharedsites $site}}
set f [open $out/fixture_accounting.txt w]
puts $f "launch_FF [llength $src]"
puts $f "capture_FF [llength $sink]"
puts $f "fixture_FF [expr {[llength $src]+[llength $sink]}]"
puts $f "full_occupied_slices [llength $totalsites]"
puts $f "core_slices_touched [llength $coresites]"
puts $f "fixture_slices_touched [llength $fixturesites]"
puts $f "shared_slices [llength $sharedsites]"
puts $f "core_exclusive_slices [expr {[llength $coresites]-[llength $sharedsites]}]"
puts $f "fixture_exclusive_slices [expr {[llength $fixturesites]-[llength $sharedsites]}]"
puts $f "core_primitive_cells [llength $coreprim]"
puts $f "fixture_primitive_cells [llength $fixtureprim]"
close $f
set f [open $out/slice_sites.txt w]
puts $f "CORE $coresites"
puts $f "FIXTURE $fixturesites"
puts $f "SHARED $sharedsites"
close $f
set f [open $out/provenance.txt w]
puts $f $provenance
puts $f "TOP $top"
puts $f "TARGET_NS $target"
puts $f "VIVADO [version -short]"
puts $f "HD_CLK_SRC [get_property HD.CLK_SRC [get_ports clk]]"
close $f

# Separately audit raw ports with a declared 1 ns setup / 0.1 ns minimum budget.
# All such ports lead only to preserved launch/capture FFs, not to core arithmetic.
set inputs [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_input_delay -clock clk -max 3.0 $inputs
set_input_delay -clock clk -min 3.0 $inputs
set_output_delay -clock clk -max 1.0 [all_outputs]
set_output_delay -clock clk -min 0.1 [all_outputs]
report_timing_summary -delay_type min_max -report_unconstrained -file $out/boundary_timing.rpt
report_timing -from $inputs -delay_type max -max_paths 10 -file $out/input_paths_max.rpt
report_timing -from $inputs -delay_type min -max_paths 10 -file $out/input_paths_min.rpt
report_timing -to [all_outputs] -delay_type max -max_paths 10 -file $out/output_paths_max.rpt
report_timing -to [all_outputs] -delay_type min -max_paths 10 -file $out/output_paths_min.rpt
write_slack $out/boundary_slack.txt
puts "FRONTIER_TIMING_ROUTED $top"






