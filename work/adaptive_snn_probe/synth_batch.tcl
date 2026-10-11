set here [file dirname [file normalize [info script]]]
set targets $argv
foreach target $targets {
 set argv [list $target acc]
 source $here/synth_probe.tcl
 close_project
}
