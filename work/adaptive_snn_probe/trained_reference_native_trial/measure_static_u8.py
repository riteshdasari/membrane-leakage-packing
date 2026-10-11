"""Matched 6ns routed control for the statically certified shift1 baseline."""
from pathlib import Path
import sys
import hashlib
import json
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
O=P.parent/'residue_frontier_trial'
sys.path.insert(0,str(O))
import run_frontier as run
S=P/'static_u8_physical'
assert not S.exists();S.mkdir()
checks=[P/'results'/f'native_shift1_stall{k}_a1/native_checks.json' for k in (0,1)]
for path in checks:
    d=run.read(path);assert d['status']=='pass'
    row,=[r for r in d['rows'] if r['engine']==12]
    assert row['status']=='pass' and row['neurons']==635904
    run.verify(d['source_sha256']);run.verify(d['candidate_file_sha256'])
fixture=(O/'guard_add_frontier_timing.sv').read_text()
fixture=fixture.replace('guard_add_frontier_timing','guard_add_static_timing')
fixture=fixture.replace('guard_add_frontier #(.E(E))core','guard_add_static_narrow_eight core')
fixture=fixture[:fixture.index('`define GUARD_ADD_FRONTIER_TOP')]+'''
module top_guard_add_static_u8(input wire clk,rst,in_valid,out_ready,
 input wire[87:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,out_valid,output wire[3:0]take,out_count,
 output wire[95:0]out_data,output wire narrow_mode);
 (* KEEP_HIERARCHY="yes",DONT_TOUCH="yes" *)guard_add_static_timing fixture(.*);
endmodule
'''
(S/'timing.sv').write_text(fixture)
tcl=(O/'route_frontier.tcl').read_text()
tcl=tcl.replace('{^top_guard_add_frontier_e[0-5]$}','{^top_guard_add_static_u8$}')
tcl=tcl.replace('read_verilog -sv $here/../guard_add.sv','read_verilog -sv $here/../../guard_add.sv')
tcl=tcl.replace(' read_verilog -sv $here/../common_layout_trial/guard_add_selective.sv\n','')
tcl=tcl.replace('read_verilog -sv $here/guard_add_frontier.sv','read_verilog -sv $here/../guard_add_static_narrow_eight.sv')
tcl=tcl.replace('read_verilog -sv $here/guard_add_frontier_timing.sv','read_verilog -sv $here/timing.sv')
(S/'route.tcl').write_text(tcl)
stamps=run.pins([Path(__file__),P/'guard_add_static_narrow_eight.sv',P/'range_certificate.json',
    O/'guard_add_frontier_timing.sv',O/'route_frontier.tcl',*checks,S/'timing.sv',S/'route.tcl',P.parent/'guard_add.sv'])
run.write(S/'source_provenance.json',stamps)
provenance=hashlib.sha256(json.dumps(stamps,sort_keys=True).encode()).hexdigest()
command=[run.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
    '-source',S/'route.tcl','-tclargs','top_guard_add_static_u8',6,provenance,'fresh',S]
try:run.tool(command,S,'route',stamps)
except AssertionError:
    assert 'ERROR: [Synth 20-411]' in (S/'route.log').read_text(errors='replace')
    assert (S/'synth/design.dcp').exists() and (S/'synth/provenance.txt').read_text().strip()==provenance
    command[-2]='resume';command[4]='vivado_resume.log';command[6]='vivado_resume.jou'
    run.tool(command,S,'route_resume',stamps)
core=run.route_helpers.util(S/'core_util.rpt',False)
full=run.route_helpers.util(S/'util.rpt')
assert full['FF']-core['FF']==290 and core['DSP']==1
slack=list(map(float,(S/'slack.txt').read_text().splitlines()))
run.verify(stamps)
run.write(S/'hardware.json',dict(status='pass' if min(slack)>=0 else 'timing_failed',core=core,
    full_fixture=full,fixture_FF=290,WNS_ns=slack[0],WHS_ns=slack[1],clock_period_ns=6,
    source_sha256=stamps,artifact_sha256=run.pins(p for p in S.iterdir() if p.is_file()),
    domain='Signed8 U/I only; certified for the saved shift1 configurations, not a full U11 replacement',
    scope='Matched routed resource/STA control; energy and routed functional replay not measured'))
print('STATIC U8 ROUTE COMPLETE',core,slack,flush=True)
