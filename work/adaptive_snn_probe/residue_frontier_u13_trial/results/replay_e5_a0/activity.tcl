run 281999 ps
open_saif activity.saif
current_scope /tb_frontier_u13_route_replay/dut
log_saif [get_objects -r *]
run 737016000 ps
close_saif
puts "FRONTIER_SAIF_CLOSED START_PS 281999 END_PS 737297999 DURATION_PS 737016000"
quit
