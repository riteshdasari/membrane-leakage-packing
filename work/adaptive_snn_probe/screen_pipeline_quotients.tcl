set here [file dirname [file normalize [info script]]]
set_param general.maxThreads 1
set top [lindex $argv 0]
if {![regexp {^top_quotient_(full|digit|split)_(const|prog)$} $top]} {error "Invalid screen top"}
read_verilog -sv $here/quotient_screen.sv
synth_design -top $top -part xc7a100tcsg324-1 -mode out_of_context
create_clock -name clk -period 6.0 [get_ports clk]
set out $here/results/${top}_screen
file mkdir $out
report_utilization -file $out/util.rpt
report_utilization -hierarchical -file $out/hierarchical_util.rpt
report_timing_summary -delay_type min_max -report_unconstrained -file $out/timing.rpt
report_timing -max_paths 5 -file $out/paths.rpt
write_checkpoint -force $out/design.dcp
puts "QUOTIENT_SYNTH_SCREEN $top"
