run 281999 ps
open_saif activity.saif
current_scope /tb_natural_energy_replay/dut
log_saif [get_objects -r *]
run 552996000 ps
close_saif
puts "FRONTIER_SAIF_CLOSED START_PS 281999 END_PS 553277999 DURATION_PS 552996000"
quit
