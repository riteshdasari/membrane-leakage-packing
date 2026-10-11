run 401999 ps
open_saif activity.saif
current_scope /tb_selective_route_replay/dut
log_saif [get_objects -r *]
run 664272000 ps
close_saif
puts "SELECTIVE_SAIF_CLOSED START_PS 401999 END_PS 664673999 DURATION_PS 664272000"
quit
