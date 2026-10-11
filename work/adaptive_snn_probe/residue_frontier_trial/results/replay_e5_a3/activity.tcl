run 281999 ps
open_saif activity.saif
current_scope /tb_frontier_route_replay/dut
log_saif [get_objects -r *]
run 719232000 ps
close_saif
puts "FRONTIER_SAIF_CLOSED START_PS 281999 END_PS 719513999 DURATION_PS 719232000"
quit
