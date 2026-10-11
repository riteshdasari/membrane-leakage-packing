"""Strengthen the immutable v2 power audit with required timing-model checks."""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent
for directory in (P,P.parent/'residue_frontier_f5_trial'):
    src=directory/'audit_frontier_power_v2.py'
    assert hashlib.sha256(src.read_bytes()).hexdigest()=='b2fe3b92dc82e33eab44d84423d7a0b03cd009ef48f3c7455bf127259187dd0a'
    text=src.read_text()
    anchor="    raw = directory/'activity.saif'"
    assert text.count(anchor)==1
    checks='''    elaboration, = [read(path) for path in jobs if Path(read(path)['argv'][0]).name == 'xelab.bat']
    options = elaboration['argv']
    assert '-transport_int_delays' in options and '-maxdelay' in options
    for name in ('-pulse_r', '-pulse_int_r'):
        assert options.count(name) == 1 and options[options.index(name)+1] == '0'
    assert not any(option in options for option in ('-mindelay','-typdelay','-notimingchecks',
        '-nosdfinterconnectdelays','-nospecify','-sdfnowarn','-sdfnoerror'))
    assert result['timing_simulation_method'] == 'AMD transport, zero pulse rejection, slow/max'
'''
    target=directory/'audit_frontier_power_v3.py'
    assert not target.exists()
    target.write_text(text.replace(anchor,checks+anchor))
    print(target,hashlib.sha256(target.read_bytes()).hexdigest())
