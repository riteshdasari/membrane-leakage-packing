# Functional diagnostic only. This never supplies timed/energy acceptance.
set_param general.maxThreads 1
lassign $argv checkpoint out
open_checkpoint $checkpoint
if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Part mismatch"}
write_verilog -force -mode funcsim $out/functional.v
puts "LUT_FUNCTIONAL_EXPORT PASS"
