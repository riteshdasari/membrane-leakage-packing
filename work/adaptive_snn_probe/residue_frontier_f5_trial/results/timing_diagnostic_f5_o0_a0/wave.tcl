open_vcd waveform.vcd
current_scope /tb_frontier_route_replay
log_vcd [get_objects -r *]
run 9000 ns
close_vcd
puts "SHORT_O0_REPLAY_FINISHED"
quit
