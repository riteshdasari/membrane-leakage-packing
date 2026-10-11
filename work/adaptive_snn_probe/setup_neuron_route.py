from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'route_persistent_unit.tcl').read_text().replace('read_verilog -sv $here/persistent_unit.sv','read_verilog -sv $here/persistent_unit.sv\nread_verilog -sv $here/packed_neuron_alu.sv')
(P/'route_neuron_alu.tcl').write_text(s)
s=(P/'run_persistent_route.py').read_text().replace('persistent_unit.sv','packed_neuron_alu.sv').replace('persistent_unit_hardware.json','neuron_alu_hardware.json').replace('route_persistent_unit.tcl','route_neuron_alu.tcl')
(P/'run_neuron_route.py').write_text(s)
print('NEURON ROUTE SCRIPTS READY')
