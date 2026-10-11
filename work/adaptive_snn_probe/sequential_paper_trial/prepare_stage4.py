"""Prepare isolated hardware sources without changing earlier evidence."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;ROOT=P.parent
assert json.loads((P/'stage3_acceptance.json').read_text())['status']=='pass_and_proceed_to_RTL'
assert not(P/'leak_dsp.sv').exists()
original=(ROOT/'packed_leak.sv').read_text()
body=original[original.index('module leak_dsp('):original.index('`define LEAK_TOP')]
body=body.replace('module leak_dsp(','module sequential_leak_dsp(')
(P/'leak_dsp.sv').write_text('`timescale 1ns/1ps\n'+body,encoding='utf-8')
fixture=(ROOT/'certified_u11_trial/timing.sv').read_text()
fixture=fixture.replace('certified_u11','sequential_leak').replace('[87:0]u_in,i_in','[23:0]u_in,input wire[17:0]beta_in')
fixture=fixture.replace('[87:0]src_u','[23:0]src_u').replace('[87:0]src_i','[17:0]src_beta')
fixture=fixture.replace('[3:0]','[1:0]').replace('[95:0]','[23:0]')
fixture=fixture.replace('.i_in(src_i)','.beta_in(src_beta)').replace('src_i<=i_in','src_beta<=beta_in')
fixture=fixture.replace('183 launch FFs and 107 capture FFs = 290 fixture FFs','47 launch FFs and 31 capture FFs = 78 fixture FFs')
fixture=fixture.replace('Every engine retains 183 launch FFs and 107 capture FFs = 290 fixture FFs.','Every engine retains 47 launch FFs and 31 capture FFs = 78 fixture FFs.')
fixture=fixture.replace('`undef GUARD_ADD_FRONTIER_TOP','`GUARD_ADD_FRONTIER_TOP(top_sequential_leak_e5,5)\n`undef GUARD_ADD_FRONTIER_TOP')
(P/'timing.sv').write_text(fixture,encoding='utf-8')
route=(ROOT/'certified_u11_trial/route.tcl').read_text()
route=route.replace('top_certified_u11_e[0-4]','top_sequential_leak_e[0-5]')
route=route.replace('read_verilog -sv $here/core.sv','read_verilog -sv $here/leak_core.sv\n read_verilog -sv $here/leak_dsp.sv')
route=route.replace('!= 183','!= 47').replace('!= 107','!= 31').replace('expected 183/107','expected 47/31')
# Apply the same raw-port budget before placement as well as reporting it later.
line='set_property HD.CLK_SRC BUFGCTRL_X0Y0 [get_ports clk]'
route=route.replace(line,line+'\n set ip [get_ports -filter {DIRECTION == IN && NAME != clk}]\n set_input_delay -clock clk -max 1.0 $ip\n set_input_delay -clock clk -min 0.1 $ip\n set_output_delay -clock clk -max 1.0 [all_outputs]\n set_output_delay -clock clk -min 0.1 [all_outputs]')
(P/'route.tcl').write_text(route,encoding='utf-8')
pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[P/'leak_core.sv',P/'leak_dsp.sv',P/'timing.sv',P/'route.tcl',Path(__file__),P/'stage3_acceptance.json',ROOT/'packed_leak.sv',ROOT/'certified_u11_trial/route.tcl',ROOT/'certified_u11_trial/timing.sv']}
(P/'stage4_source_preparation.json').write_text(json.dumps(dict(status='prepared',source_sha256=pins,fixture_FF=78,launch_FF=47,capture_FF=31,target_ns=6),indent=2)+'\n',encoding='utf-8')
print('STAGE4 SOURCES PREPARED',flush=True)
