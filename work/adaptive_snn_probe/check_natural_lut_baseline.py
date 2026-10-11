"""Operation-equivalent one-edge LUT baseline; no four-stage constraint."""
from pathlib import Path
import sys,time,hashlib,json
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
W=P/'residue_frontier_u13_trial'
sys.path.insert(0,str(W))
import run_u13_physical as run
N=P/'natural_lut_baseline_trial'
assert '--run' in sys.argv and not N.exists();N.mkdir()
core=N/'natural_lut.sv'
core.write_text('''`timescale 1ns/1ps
module natural_lut(input wire clk,rst,in_valid,out_ready,
 input wire[103:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[111:0]out_data,output wire narrow_mode);
 reg valid=0;reg[3:0]count=0;reg[111:0]data=0;
 wire advance=!valid||out_ready;
 assign in_ready=advance;assign take=available;
 assign out_valid=valid;assign out_count=count;assign out_data=data;
 assign narrow_mode=1'b0;
 wire accept=in_valid&&advance&&(available!=0);
 wire[111:0]sums;
 generate for(genvar l=0;l<8;l=l+1)begin:lane
  wire signed[13:0]u14={u_in[13*l+12],u_in[13*l+:13]};
  wire signed[13:0]i14={{6{i_in[13*l+7]}},i_in[13*l+:8]};
  (* use_dsp="no" *)wire signed[13:0]sum=u14+i14;
  assign sums[14*l+:14]=sum;
 end endgenerate
 always @(posedge clk)begin
  if(rst)begin valid<=0;count<=0;data<=0;end
  else if(advance)begin
   valid<=accept;
   if(accept)begin count<=available;
    for(integer l=0;l<8;l=l+1)data[14*l+:14]<=available>l?sums[14*l+:14]:14'd0;
   end
  end
 end
endmodule
''')
# Keep the existing independent integer oracle and protocol driver. Only the
# top's instance set, implementation name and declared latency change.
tbtext=(W/'tb_frontier_u13_compare.sv').read_text()
tbtext=tbtext.replace('guard_add_frontier_u13 #(.E(E))dut','natural_lut dut')
tbtext=tbtext.replace('step-qstep[head%32]!=4','step-qstep[head%32]!=1')
tbtext=tbtext.replace('cycle-qclk[head%32]<4','cycle-qclk[head%32]<1')
tbtext=tbtext[:tbtext.index('module tb_frontier_u13_compare;')]+'''
module tb_frontier_u13_compare;
 reg clk=0;initial begin #6;forever #3 clk=~clk;end
 wire done;
 frontier_u13_driver #(.E(2))driver(clk,done);
 initial begin wait(done);$display("FRONTIER_U13_COMPARE PASS STALL %0d",`STALL);$finish;end
endmodule
'''
(N/'tb_native.sv').write_text(tbtext)
checker=(W/'verify_frontier_u13.py').read_text()
checker=checker.replace('P = Path(__file__).resolve().parent',f'P = Path({W.as_posix()!r})')
for old,new in [('for engine in range(6):','for engine in (2,):'),
                ('advance-issued==4','advance-issued==1'),('advance==4','advance==1'),
                ('retire-accept>=4','retire-accept>=1'),('latmin==latmax==4','latmin==latmax==1')]:
    assert old in checker;checker=checker.replace(old,new)
checker=checker.replace('4advancingclocks','1advancingclock')
(N/'verify_native.py').write_text(checker)
fixture=(W/'guard_add_frontier_u13_timing.sv').read_text()
fixture=fixture.replace('guard_add_frontier_u13_timing','natural_lut_timing')
fixture=fixture.replace('guard_add_frontier_u13 #(.E(E))core','natural_lut core')
fixture=fixture[:fixture.index('`define ')]+'''
module top_natural_lut(input wire clk,rst,in_valid,out_ready,
 input wire[103:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,out_valid,output wire[3:0]take,out_count,
 output wire[111:0]out_data,output wire narrow_mode);
 (* KEEP_HIERARCHY="yes",DONT_TOUCH="yes" *)natural_lut_timing fixture(.*);
endmodule
'''
(N/'timing.sv').write_text(fixture)
route=(W/'route_u13.tcl').read_text()
route=route.replace('{^top_guard_add_frontier_u13_e[0-5]$}','{^top_natural_lut$}')
route=route.replace('read_verilog -sv $here/guard_add_frontier_u13.sv','read_verilog -sv $here/natural_lut.sv')
route=route.replace('read_verilog -sv $here/guard_add_frontier_u13_timing.sv','read_verilog -sv $here/timing.sv')
(N/'route.tcl').write_text(route)
stamps=run.pins([Path(__file__),core,N/'tb_native.sv',N/'verify_native.py',N/'timing.sv',N/'route.tcl',
    W/'tb_frontier_u13_compare.sv',W/'verify_frontier_u13.py',W/'guard_add_frontier_u13_timing.sv',
    W/'route_u13.tcl',W/'prepare_u13_work.py'])
run.write(N/'preparation.json',dict(source_sha256=stamps,
    scope='One-edge eight-lane signed13 U+signed8 I to signed14. Same source order, integer oracle, reset/backpressure/poison checks and registered338FF fixture. No DSP, no imposed output-alignment stages.'))
native=[]
for kind in ('models','main'):
    for stall in (0,1):
        wd=N/f'native_{kind}_{stall}_a0';wd.mkdir()
        run.tool([sys.executable,'-B',W/'prepare_u13_work.py','--kind',kind,'--directory',wd],wd,'prepare',stamps,.1)
        current=stamps|run.pins([wd/'stream_stim.txt',wd/'workload.json'])
        run.write(wd/'provenance.json',current)
        commands=[
         [run.base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}',
          '-d',f'CAPTURE_TRACE={int(kind=="models" and not stall)}',core,N/'tb_native.sv'],
         [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
         [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_frontier_u13_compare','glbl','-s','sim'],
         [run.base.VIVADO/'bin/xsim.bat','sim','-R'],
         [sys.executable,'-B',N/'verify_native.py','--directory',wd,'--kind',kind,'--stall',stall,
          '--output',wd/'native_checks.json']]
        for k,command in enumerate(commands):
            while run.base.free()<=1.2:time.sleep(5)
            run.tool(command,wd,f'tool_{k}',current,1.2)
        check=run.read(wd/'native_checks.json');assert check['status']=='pass' and len(check['rows'])==1
        assert check['rows'][0]['engine']==2
        native.append(check|dict(check_file=str(wd/'native_checks.json')))
        print('NATURAL LUT NATIVE PASS',kind,stall,check['rows'][0]['service_clocks'],flush=True)
run.write(N/'native_acceptance.json',dict(status='pass',cohorts=native,source_sha256=stamps,
    scope='Operation-equivalent one-edge baseline. Existing independent oracle cloned only for declared latency and single instance.'))
# All Vivado synthesis/export/power remains serialized. The functional-diagnostic
# exporter must also release its slot; its later low-memory XSim can overlap.
completion=W/'results/completion_progress.json'
func_export=P/'residue_frontier_f5_trial/results/diagnostic_routed_functional_a0/export.job.json'
while run.read(completion)['status'] not in ('all_checks_passed','completed_with_retained_failures') or not func_export.exists():time.sleep(5)
assert run.read(func_export)['returncode']==0
while run.base.free()<=2.3:time.sleep(5)
wd=N/'route_a0';wd.mkdir()
current=stamps|run.pins([N/'native_acceptance.json'])
provenance=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()
command=[run.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
         '-source',N/'route.tcl','-tclargs','top_natural_lut',6,provenance,'fresh',wd]
try:run.tool(command,wd,'route',current)
except AssertionError:
    assert 'ERROR: [Synth 20-411]' in (wd/'route.log').read_text(errors='replace')
    assert (wd/'synth/design.dcp').exists() and (wd/'synth/provenance.txt').read_text().strip()==provenance
    command[-2]='resume';command[4]='vivado_resume.log';command[6]='vivado_resume.jou'
    run.tool(command,wd,'route_resume',current)
c=run.route_helpers.util(wd/'core_util.rpt',False);full=run.route_helpers.util(wd/'util.rpt')
assert c['DSP']==0 and full['FF']-c['FF']==338
slack=list(map(float,(wd/'slack.txt').read_text().splitlines()))
run.verify(current)
run.write(wd/'hardware.json',dict(status='pass' if min(slack)>=0 else 'timing_failed',core=c,
    full_fixture=full,fixture_FF=338,WNS_ns=slack[0],WHS_ns=slack[1],clock_period_ns=6,
    latency_advancing_edges=1,source_sha256=current,
    artifact_sha256=run.pins(p for p in wd.iterdir() if p.is_file()),
    scope='Operation-equivalent naturally shallow LUT baseline; matched338FF fixture. Resource/STA only, no accepted timing replay or energy.'))
print('NATURAL LUT ROUTE COMPLETE',c,slack,flush=True)
