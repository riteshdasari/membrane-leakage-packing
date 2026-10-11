"""One unchanged routed replay with vendor CARRY4 internal diagnostic probes."""
from pathlib import Path
import argparse
import shutil
import sys

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent.parent/'selective_energy_trial'))
import run_selective_energy as b
S=P.parent.parent/'sequential_paper_trial'
ap=argparse.ArgumentParser()
ap.add_argument('--run',action='store_true')
args=ap.parse_args()
assert args.run
wd=P/'internal_a0'
assert not wd.exists()
wd.mkdir()
monitor=(P.parent/'lut_diag_a1/monitor.sv').read_text()
probes=r'''
 wire cii=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in;
 wire cyi=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT_in;
 wire[3:0] sii=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in;
 wire[3:0] dii=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI_in;
 wire[3:0] fbi=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO_fb;
 wire[3:0] truth_o=sii^fbi;
 wire[3:0] truth_co=(sii&fbi)|(~sii&dii);
 always @(ds or di or ci or doo or co or cii or cyi or sii or dii or fbi or truth_o or truth_co)
   if(n>=913&&n<=915)
     $strobe("INTERNAL T%0.3f ROW%0d PORT_S%h PORT_DI%h PORT_CI%b CI_IN%b CY_IN%b S_IN%h DI_IN%h CO_FB%h CO%h O%h TRUTH_O%h TRUTH_CO%h",$realtime,n,ds,di,ci,cii,cyi,sii,dii,fbi,co,doo,truth_o,truth_co);
 always @(posedge rc)
   if(n>=913&&n<=915)
     $strobe("EDGE T%0.3f ROW%0d CI_IN%b S_IN%h CO_FB%h O%h TRUTH_O%h D%b Q%b",$realtime,n,cii,sii,fbi,doo,truth_o,rd,rq);
'''
assert monitor.count('endmodule')==1
(wd/'monitor.sv').write_text(monitor.replace('endmodule',probes+'\nendmodule'))
shutil.copyfile(P/'CARRY4_vendor.v',wd/'CARRY4_vendor.v')
(wd/'run.tcl').write_text('run 12000 ns\nquit\n')
rv=S/'hardware/export12_e2_a0/routed.v'
sdf=S/'hardware/export12_e2_a0/routed.sdf'
trace=S/'hardware/native_actual_s0_a3/trace2.txt'
stamps=b.pins([Path(__file__),wd/'monitor.sv',wd/'CARRY4_vendor.v',wd/'run.tcl',rv,sdf,trace,b.VIVADO/'data/verilog/src/glbl.v'])
b.write(wd/'provenance.json',stamps)
commands=[
 [b.VIVADO/'bin/xvlog.bat','-d','XIL_TIMING',wd/'CARRY4_vendor.v'],
 [b.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=2','-d','DUT_TOP=top_sequential_leak_e2',rv,wd/'monitor.sv'],
 [b.VIVADO/'bin/xvlog.bat',b.VIVADO/'data/verilog/src/glbl.v'],
 [b.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','work','-L','simprims_ver','-L','secureip','-L','unisims_ver','tb_sequential_energy_replay','glbl','-s','sim'],
 [b.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}','-testplusarg','ROWS=950','-testplusarg','ROI_FIRST=3','-testplusarg','ROI_LAST=950','-tclbatch',wd/'run.tcl']
]
logs=[]
for i,command in enumerate(commands):
    logs.append(b.job([str(x).replace('\\','/')for x in command],wd,f'tool_{i}',stamps,1.2))
assert 'Compiling module work.CARRY4' in logs[3].read_text()
assert 'SDF backannotation was successful' in logs[3].read_text()
data=logs[4].read_text(errors='replace')
settled=[x for x in data.splitlines() if x.startswith('EDGE ')]
b.write(wd/'diagnostic.json',{'status':'internal_probe_diagnostic_not_acceptance',
         'library_binding':'work.CARRY4 explicitly compiled','vendor_source_modified':False,
         'timing_checks_disabled':False,'maxdelay':True,'transport_int_delays':True,
         'artifact_sha256':b.pins(logs),'edges':settled,
         'fatal_lines':[x for x in data.splitlines() if 'Fatal:' in x]})
print('\n'.join(settled),flush=True)
print(data[-650:],flush=True)
