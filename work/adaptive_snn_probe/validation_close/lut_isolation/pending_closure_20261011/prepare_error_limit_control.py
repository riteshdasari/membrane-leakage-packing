"""Prepare (not launch) a matched R=0, E=100 timing control."""
from pathlib import Path
P = Path(__file__).resolve().parent
target=P/'run_error_limit_control.py'
assert not target.exists(), 'Preserve attempts'
s=(P/'run_optimization_control.py').read_text()
for old,new in [("'-pulse_e', '0',","'-pulse_e', '100',"),
                ("'-pulse_int_e', '0',","'-pulse_int_e', '100',"),
                ("wd = P / ('run_o0_' if a.o0 else 'run_default_') / a.attempt","wd = P / 'run_default_error_' / a.attempt")]:
    assert s.count(old)==1,old
    s=s.replace(old,new)
target.write_text(s)
print('Prepared matching error100/reject0 control; original inputs unchanged.')
