# Measurement-only annotation repair/audit; frozen DCP and raw SAIF unchanged.
set_param general.maxThreads 1
if {[llength $argv] != 4} {error "variant dcp saif outdir"}
lassign $argv variant dcp saif out
file mkdir $out
open_checkpoint $dcp
if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Part mismatch"}
if {[llength [get_clocks]] != 1 || [get_property PERIOD [get_clocks]] != 6.0} {error "Clock mismatch"}
set_operating_conditions -process typical -junction_temp 25 -ambient_temp 25
report_operating_conditions -all -file $out/operating_conditions.rpt
report_clocks -file $out/clocks.rpt
read_saif -strip_path tb_selective_route_replay/dut -out_file $out/unmatched.rpt $saif
report_switching_activity -all -file $out/switching_activity.rpt
# Record exact DCP connectivity for matching SAIF unknowns and important enables.
set f [open $out/net_connectivity.jsonl w]
foreach net [get_nets -hierarchical] {
 set name [get_property NAME $net]
 set pins [get_pins -quiet -of_objects $net]
 set ports [get_ports -quiet -of_objects $net]
 # Tcl list syntax retained, with one net per line for independent parsing.
 puts $f [list $name $pins $ports]
}
close $f
report_power -hier all -hierarchical_depth 10 -advisory -file $out/power.rpt
report_power -hier all -hierarchical_depth 10 -advisory -format xml -file $out/power.xml
report_power -hier all -hierarchical_depth 10 -advisory -xpe $out/power_xpe.xml -file $out/power_xpe.rpt
puts "SELECTIVE_ANNOTATION_POWER PASS V$variant"
