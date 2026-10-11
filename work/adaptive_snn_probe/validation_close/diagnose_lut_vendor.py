from pathlib import Path
import sys,shutil
P=Path(__file__).resolve().parent;S=P.parent/'sequential_paper_trial'
sys.path.insert(0,str(P.parent/'selective_energy_trial'))
import run_selective_energy as b
wd=P/'lut_diag_a2';assert not wd.exists();wd.mkdir()
shutil.copyfile(P/'lut_diag_a1/monitor.sv',wd/'monitor.sv')
vendor=b.VIVADO/'data/verilog/src/unisims/CARRY4.v'
shutil.copyfile(vendor,wd/'CARRY4_vendor.v')
assert b.sha(vendor)==b.sha(wd/'CARRY4_vendor.v')
(wd/'run.tcl').write_text('run 12000 ns\nquit\n')
rv=S/'hardware/export12_e2_a0/routed.v'
trace=S/'hardware/native_actual_s0_a3/trace2.txt'
pins=b.pins([Path(__file__),wd/'monitor.sv',wd/'run.tcl',rv,
    S/'hardware/export12_e2_a0/routed.sdf',trace,vendor,wd/'CARRY4_vendor.v'])
b.write(wd/'provenance.json',pins)
commands=[
 [b.VIVADO/'bin/xvlog.bat','-d','XIL_TIMING',wd/'CARRY4_vendor.v'],
 [b.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=2','-d','DUT_TOP=top_sequential_leak_e2',rv,wd/'monitor.sv'],
 [b.VIVADO/'bin/xvlog.bat',b.VIVADO/'data/verilog/src/glbl.v'],
 [b.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','work','-L','simprims_ver','-L','secureip','-L','unisims_ver','tb_sequential_energy_replay','glbl','-s','sim'],
 [b.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}','-testplusarg','ROWS=950','-testplusarg','ROI_FIRST=3','-testplusarg','ROI_LAST=950','-tclbatch',wd/'run.tcl']]
logs=[b.job([str(x).replace('\\','/')for x in c],wd,f'tool_{i}',pins,1.2)for i,c in enumerate(commands)]
b.write(wd/'diagnostic.json',dict(status='vendor_source_monitor_not_acceptance',source_sha256=pins,
    artifact_sha256=b.pins(logs),vendor_source_modified=False,XIL_TIMING_enabled=True))
print(logs[-1].read_text()[-1400:],flush=True)
