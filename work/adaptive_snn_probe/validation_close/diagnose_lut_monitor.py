from pathlib import Path
import sys,re
P=Path(__file__).resolve().parent;S=P.parent/'sequential_paper_trial'
sys.path.insert(0,str(P.parent/'selective_energy_trial'))
import run_selective_energy as b
wd=P/'lut_diag_a1';assert not wd.exists();wd.mkdir()
tb=(S/'tb_energy12.sv').read_text()
probe=r'''
 wire[3:0]ds=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S;
 wire[3:0]di=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI;
 wire ci=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI;
 wire[3:0]co=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO;
 wire[3:0]doo=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .O;
 wire rd=dut.fixture.core.\lut.lane[0].r_reg[9] .D;
 wire rq=dut.fixture.core.\lut.lane[0].r_reg[9] .Q;
 wire rc=dut.fixture.core.\lut.lane[0].r_reg[9] .C;
 wire re=dut.fixture.core.\lut.lane[0].r_reg[9] .CE;
 wire[19:0]product=dut.fixture.core.\lut.lane[0].product ;
 always @(ds or di or ci or co or doo or rd or rq or rc or re or product)
  if(n>=910&&n<=916)$display("DBG T%0.3f ROW%0d S%h DI%h CI%b CO%h O%h D%b Q%b CLK%b CE%b PRODUCT%h",$realtime,n,ds,di,ci,co,doo,rd,rq,rc,re,product);
'''
tb=tb.replace('endmodule',probe+'\nendmodule')
(wd/'monitor.sv').write_text(tb)
(wd/'run.tcl').write_text('run 12000 ns\nquit\n')
rv=S/'hardware/export12_e2_a0/routed.v'
trace=S/'hardware/native_actual_s0_a3/trace2.txt'
pins=b.pins([Path(__file__),wd/'monitor.sv',wd/'run.tcl',rv,
    S/'hardware/export12_e2_a0/routed.sdf',trace])
b.write(wd/'provenance.json',pins)
commands=[
 [b.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=2','-d','DUT_TOP=top_sequential_leak_e2',rv,wd/'monitor.sv'],
 [b.VIVADO/'bin/xvlog.bat',b.VIVADO/'data/verilog/src/glbl.v'],
 [b.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','simprims_ver','-L','secureip','-L','unisims_ver','tb_sequential_energy_replay','glbl','-s','sim'],
 [b.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}','-testplusarg','ROWS=950','-testplusarg','ROI_FIRST=3','-testplusarg','ROI_LAST=950','-tclbatch',wd/'run.tcl']]
logs=[b.job([str(x).replace('\\','/')for x in c],wd,f'tool_{i}',pins,1.2)for i,c in enumerate(commands)]
b.write(wd/'diagnostic.json',dict(status='monitor_not_acceptance',source_sha256=pins,artifact_sha256=b.pins(logs)))
print(logs[-1].read_text()[-2200:],flush=True)
