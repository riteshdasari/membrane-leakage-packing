# Measurement-only export and activity annotation of an immutable routed DCP.
set_param general.maxThreads 1
if {[llength $argv] < 4} {error "mode variant dcp outdir ?saif?"}
lassign $argv mode variant dcp out
if {$variant ni {2 3}} {error "Only frozen I8 V2/V3"}
set dcp [file normalize $dcp]
set out [file normalize $out]
file mkdir $out
open_checkpoint $dcp
# current_design NAME is Vivado's session design name, not the HDL top. The
# runner pins the exact DCP; export then verifies the emitted HDL top name.
report_property [current_design] -file $out/design_properties.rpt
if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Wrong part"}
set clocks [get_clocks]
if {[llength $clocks] != 1 || [get_property PERIOD $clocks] != 6.0} {error "Wrong clock"}
report_clocks -file $out/clocks.rpt
set f [open $out/design_metadata.txt w]
puts $f "MODE $mode"
puts $f "VARIANT $variant"
puts $f "DCP $dcp"
puts $f "VIVADO [version -short]"
puts $f "SESSION_DESIGN [get_property NAME [current_design]]"
puts $f "EXPECTED_TOP top_guard_add_selective_v$variant"
puts $f "PART [get_property PART [current_design]]"
puts $f "PERIOD_NS [get_property PERIOD $clocks]"
close $f
if {$mode eq "export"} {
 write_sdf -force -mode timesim -process_corner slow $out/routed.sdf
 write_verilog -force -mode timesim -sdf_anno true -sdf_file $out/routed.sdf $out/routed.v
 puts "SELECTIVE_ENERGY_EXPORT PASS V$variant"
} elseif {$mode eq "power"} {
 if {[llength $argv] != 5} {error "power requires matching SAIF"}
 set saif [file normalize [lindex $argv 4]]
 # Fixed junction temperature avoids unequal self-heating assumptions. Use the
 # same typical process and nominal rails for both activity estimates.
 set_operating_conditions -process typical -junction_temp 25 -ambient_temp 25
 report_operating_conditions -file $out/operating_conditions.rpt
 read_saif -strip_path tb_selective_route_replay/dut -out_file $out/unmatched.rpt $saif
 report_power -hier all -hierarchical_depth 10 -advisory -file $out/power.rpt
 report_power -hier all -hierarchical_depth 10 -advisory -format xml -file $out/power.xml
 report_power -hier all -hierarchical_depth 10 -advisory -rpx $out/power.rpx -file $out/power_rpx.rpt
 # Export activity/source properties for important controls and clocking, rather
 # than assuming a high global match percentage covers the correction cone.
 set f [open $out/activity_properties.txt w]
 foreach net [get_nets -hierarchical] {
  set name [get_property NAME $net]
  puts $f "NET $name"
  foreach prop [list_property $net] {
   if {[regexp -nocase {switch|toggle|static|probab|activity} $prop]} {
    puts $f "$prop [get_property $prop $net]"
   }
  }
 }
 close $f
 puts "SELECTIVE_ENERGY_POWER PASS V$variant"
} else {error "Unknown mode $mode"}
