"""Recheck existing unchanged control trace after preserving verifier failure."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import run_frontier as run
P=Path(__file__).resolve().parent
wd=P/'results/supply2_models_0_a0'
stamps=run.read(wd/'provenance.json')|run.pins([Path(__file__),P/'verify_frontier_supply2_v2.py'])
assert run.read(wd/'tool_3.job.json')['returncode']==0
assert run.read(wd/'verify.job.json')['returncode']!=0
run.tool([sys.executable,'-B',P/'verify_frontier_supply2_v2.py','--directory',wd,
          '--kind','models','--stall',0,'--output',wd/'frontier_checks.json'],
         wd,'verify_repaired',stamps,.1)
check=run.read(wd/'frontier_checks.json')
assert all(r['service_clocks']==354816 and r['requests']==317952 for r in check['rows'])
print('SUPPLY2 REPAIRED VERIFICATION PASS all6 engines 354816 clocks',flush=True)
