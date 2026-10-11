# Measurement only: do not change the routed design or recorded SAIF.
set_param general.maxThreads 1
if {[llength $argv] != 4} {error "engine dcp saif outdir"}
lassign $argv engine dcp saif out
if {$engine < 0 || $engine > 5} {error "Engine outside 0..5"}
file mkdir $out
open_checkpoint $dcp
if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Part mismatch"}
if {[llength [get_clocks]] != 1 || [get_property PERIOD [get_clocks]] != 6.0} {error "Clock mismatch"}
set_operating_conditions -process typical -junction_temp 25 -ambient_temp 25
report_operating_conditions -all -file $out/operating_conditions.rpt
report_clocks -file $out/clocks.rpt
read_saif -strip_path tb_sequential_energy_replay/dut -out_file $out/unmatched.rpt $saif
report_switching_activity -file $out/switching_activity.rpt [get_nets -hierarchical]
# Tcl list records are parsed without evaluation by the independent auditor.
set f [open $out/net_connectivity.jsonl w]
foreach net [get_nets -hierarchical] {
 puts $f [list [get_property NAME $net] [get_pins -quiet -of_objects $net] [get_ports -quiet -of_objects $net]]
}
close $f
set f [open $out/cell_ref_names.tsv w]
foreach cell [get_cells -hierarchical] {
 puts $f [list [get_property NAME $cell] [get_property REF_NAME $cell]]
}
close $f
report_power -hier all -hierarchical_depth 10 -advisory -file $out/power.rpt
report_power -hier all -hierarchical_depth 10 -advisory -format xml -file $out/power.xml
report_power -hier all -hierarchical_depth 10 -advisory -xpe $out/power_xpe.xml -file $out/power_xpe.rpt
puts "FRONTIER_ANNOTATION_POWER PASS E$engine"
