run 10900 ns
open_vcd carry_window.vcd
log_vcd [get_objects -r /tb_sequential_energy_replay/dut/*]
run 500 ns
close_vcd
quit
