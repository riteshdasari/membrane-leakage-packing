from pathlib import Path
import sys,json,shutil
P=Path(__file__).resolve().parent
S=P.parent/'sequential_paper_trial'
sys.path.insert(0,str(P.parent/'selective_energy_trial'))
import run_selective_energy as base
src=S/'hardware/replay12_e2_a0'
wd=P/'lut_diag_a0'
assert not wd.exists()
wd.mkdir()
shutil.copytree(src/'xsim.dir',wd/'xsim.dir')
trace=S/'hardware/native_actual_s0_a3/trace2.txt'
script=wd/'inspect.tcl'
script.write_text('run 10900 ns\nopen_vcd carry_window.vcd\nlog_vcd [get_objects -r /tb_sequential_energy_replay/dut/*]\nrun 500 ns\nclose_vcd\nquit\n')
pins=base.pins([Path(__file__),script,trace,src/'tool_2.job.json',S/'hardware/export12_e2_a0/routed.v',S/'hardware/export12_e2_a0/routed.sdf']+
               [p for p in (wd/'xsim.dir').rglob('*') if p.is_file()])
base.write(wd/'provenance.json',pins)
cmd=[base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}',
    '-testplusarg','ROWS=950','-testplusarg','ROI_FIRST=3','-testplusarg','ROI_LAST=950',
    '-tclbatch',script]
log=base.job([str(x).replace('\\','/')for x in cmd],wd,'inspect',pins,1.2)
base.verify(pins)
base.write(wd/'diagnostic.json',dict(status='diagnostic_waveform_saved_not_an_acceptance',
    source_sha256=pins,artifact_sha256=base.pins([log,wd/'carry_window.vcd']),
    unchanged_compiled_delayed_snapshot=True,timing_checks_disabled=False))
print(log.read_text()[-1700:],flush=True)
