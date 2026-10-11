"""Fresh minimal startup check following a Windows window-station failure."""
from pathlib import Path
import argparse
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent.parent/'selective_energy_trial'))
import run_selective_energy as b
ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True);args=ap.parse_args()
assert args.attempt.replace('_','').isalnum()
wd=P/'hardware'/('vendor_startup_'+args.attempt)
assert not wd.exists();wd.mkdir()
source=b.VIVADO/'data/verilog/src/glbl.v'
stamps=b.pins([Path(__file__),source,P.parent.parent/'selective_energy_trial/run_selective_energy.py'])
b.write(wd/'provenance.json',stamps)
argv=[str(b.VIVADO/'bin/xvlog.bat').replace('\\','/'),str(source).replace('\\','/')]
log=b.job(argv,wd,'compile_glbl',stamps,1.2)
assert 'analyzing module glbl' in log.read_text()
b.write(wd/'acceptance.json',dict(status='pass_vendor_startup_only',source_sha256=stamps,artifact_sha256=b.pins([log,wd/'compile_glbl.job.json'])))
print('Fresh vendor startup PASS; no simulation, hardware or power acceptance implied.')
