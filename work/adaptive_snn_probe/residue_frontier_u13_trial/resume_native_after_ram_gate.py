"""Resume the unlaunched simulator after the retained start-RAM gate stop."""
from pathlib import Path
import sys,time
sys.dont_write_bytecode=True
import run_u13_physical as run
import run_u13_native as native
P=Path(__file__).resolve().parent
assert '--run' in sys.argv
wd=P/'results/native_main_0_a0'
assert wd.exists() and not (wd/'tool_3.job.json').exists() and not (wd/'tool_3.log').exists()
assert not list(wd.glob('frontier_out*.txt'))
stamps=run.read(wd/'provenance.json')
run.verify(stamps)
for n in range(3):
    d=run.read(wd/f'tool_{n}.job.json');assert d['returncode']==0
    run.verify(d['source_sha256'])
assert 'Built simulation snapshot sim' in (wd/'tool_2.log').read_text()
resume_pins=stamps|run.pins([Path(__file__),*(wd/f'tool_{n}.job.json' for n in range(3))])
run.write(wd/'ram_gate_resume_provenance.json',dict(source_sha256=resume_pins,
    original_stop=dict(stage='tool_3',free_GiB=1.1265144348144531,required_GiB=1.2,
        simulator_not_launched=True,completed_compilation_reused=True),
    scope='Only remaining simulator and verifier launched; no source or completed job overwritten'))
# Avoid competing with the serialized registered static control route.
while not (P.parent/'trained_reference_native_trial/static_u8_physical/hardware.json').exists():time.sleep(5)
while run.base.free()<=1.2:time.sleep(5)
run.tool([run.base.VIVADO/'bin/xsim.bat','sim','-R'],wd,'tool_3',resume_pins,1.2)
run.tool([sys.executable,'-B',P/'verify_frontier_u13.py','--directory',wd,'--kind','main',
    '--stall',0,'--output',wd/'frontier_checks.json'],wd,'verify',resume_pins,.1)
run.verify(resume_pins)
print('U13 RAM-GATED MAIN0 RESUMED AND VERIFIED',flush=True)
native.native('main',1,0)
