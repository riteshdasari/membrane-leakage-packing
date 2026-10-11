"""Use the complete four-zero pulse configuration in AMD's timing example."""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent
F5=P.parent/'residue_frontier_f5_trial'
for directory in (P,F5):
    old=(directory/'run_frontier_replay_transport_v3.py').read_text()
    needle="'-transport_int_delays','-pulse_r','0','-pulse_int_r','0',"
    assert old.count(needle)==1
    new=old.replace(needle,needle+"'-pulse_e','0','-pulse_int_e','0',")
    new=new.replace('AMD transport, zero pulse rejection, slow/max',
                    'AMD transport, zero pulse error and rejection, slow/max')
    new=new.replace('REPLAY TRANSPORT V3 COMPLETE','REPLAY COMPLETE PULSE V4 COMPLETE')
    if directory==P:new=new.replace('default=2)', 'default=3)')
    else:new=new.replace('default=0)', 'default=1)')
    dest=directory/'run_frontier_replay_transport_v4.py'
    assert not dest.exists();dest.write_text(new)
    print(dest,hashlib.sha256(dest.read_bytes()).hexdigest())
    old=(directory/'audit_frontier_power_v3.py').read_text()
    assert hashlib.sha256((directory/'audit_frontier_power_v3.py').read_bytes()).hexdigest()=='2a92e9d081997f5b8ab1cf6c3ea1a73ce6e6e9cd25a4a74c999a3473e49f1902'
    new=old.replace("('-pulse_r', '-pulse_int_r')","('-pulse_r', '-pulse_int_r', '-pulse_e', '-pulse_int_e')")
    assert new!=old
    new=new.replace('AMD transport, zero pulse rejection, slow/max',
                    'AMD transport, zero pulse error and rejection, slow/max')
    dest=directory/'audit_frontier_power_v4.py'
    assert not dest.exists();dest.write_text(new)
    print(dest,hashlib.sha256(dest.read_bytes()).hexdigest())

old=(P/'queue_transport_energy_v5.py').read_text()
new=old.replace('attempt=2 if family', 'attempt=3 if family')
new=new.replace("else 0\n    directory", "else 1\n    directory")
new=new.replace('run_frontier_replay_transport_v3.py','run_frontier_replay_transport_v4.py')
new=new.replace('audit_frontier_power_v3.py','audit_frontier_power_v4.py')
new=new.replace("'audit_v3'", "'audit_v4'")
new=new.replace("attempt=1 if family=='original' else 0", "attempt=1")
new=new.replace('transport_energy_progress.json','transport_energy_v6_progress.json')
dest=P/'queue_transport_energy_v6.py'
assert not dest.exists();dest.write_text(new)
print(dest,hashlib.sha256(dest.read_bytes()).hexdigest())
