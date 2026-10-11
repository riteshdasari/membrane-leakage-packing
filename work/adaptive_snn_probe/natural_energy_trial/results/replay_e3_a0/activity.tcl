run 281999 ps
open_saif activity.saif
current_scope /tb_natural_energy_replay/dut
log_saif [get_objects -r *]
run 552972000 ps
close_saif
puts "FRONTIER_SAIF_CLOSED START_PS 281999 END_PS 553253999 DURATION_PS 552972000"
quit
