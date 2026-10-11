set_param general.maxThreads 1
open_checkpoint [lindex $argv 0]
write_verilog -mode funcsim -force [lindex $argv 1]
puts "ROUTED_FUNCSIM_EXPORTED"
