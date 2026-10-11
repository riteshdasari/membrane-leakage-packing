set_param general.maxThreads 1
open_checkpoint [lindex $argv 0]
puts "IDENTITY NAME <[get_property NAME [current_design]]>"
report_property [current_design]
puts "IDENTITY FILESET_TOP <[get_property TOP [current_fileset]]>"
puts "IDENTITY PART <[get_property PART [current_design]]>"
puts "IDENTITY CLOCK <[get_property PERIOD [get_clocks]]>"
