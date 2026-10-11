"""Wait for the serial diagnostic, then publish and verify the bounded batch."""
from pathlib import Path
import subprocess,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;assert '--run'in sys.argv
while not(ROOT/'u11_fixed_functional_diagnostic/acceptance.json').exists():time.sleep(5)
for name in('publish_extended_followup.py','verify_extended_followup.py'):
    p=subprocess.run([sys.executable,'-B',str(ROOT/name)],capture_output=True,text=True)
    print(p.stdout,flush=True)
    if p.stderr:print(p.stderr,flush=True)
    assert p.returncode==0,(name,p.returncode)
print('EXTENDED FOLLOWUP DELIVERY CLOSED',flush=True)
