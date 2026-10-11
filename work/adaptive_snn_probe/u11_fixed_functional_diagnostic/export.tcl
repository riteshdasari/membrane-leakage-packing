set_param general.maxThreads 1
lassign $argv dcp out
open_checkpoint $dcp
if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Part mismatch"}
if {[get_property NAME [current_design]] ne "top_natural_u11_e1"} {error "Top mismatch"}
write_verilog -force -mode funcsim $out/mapped_functional.v
puts "U11_FIXED_FUNCTIONAL_EXPORT PASS"
