run 401999 ps
open_saif activity.saif
current_scope /tb_selective_route_replay/dut
log_saif [get_objects -r *]
run 663588000 ps
close_saif
puts "SELECTIVE_SAIF_CLOSED START_PS 401999 END_PS 663989999 DURATION_PS 663588000"
quit
