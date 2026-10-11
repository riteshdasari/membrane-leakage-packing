# Preserve the original power-flow settings/options; add connectivity type data.
set trial_here [file dirname [file normalize [info script]]]
source $trial_here/../selective_energy_trial/annotation_power_audit.tcl
set refs [open $out/cell_ref_names.tsv w]
foreach cell [get_cells -hierarchical -filter {IS_PRIMITIVE}] {
 puts $refs [list [get_property NAME $cell] [get_property REF_NAME $cell]]
}
close $refs
puts "OPERAND_ISOLATION_TYPE_EXPORT PASS"
