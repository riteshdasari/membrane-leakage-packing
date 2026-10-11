"""Preserve old audits; create explicit-top checkpoint attribution versions."""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent
old="""    dcp, = [name for name in producer if Path(name).name == 'design.dcp']
    hardware, = [name for name in producer if Path(name).name == 'hardware.json']"""
new="""    hardware, = [name for name in producer if Path(name).name == 'hardware.json'
                  and read(name).get('top') == result['design_top']]
    dcp = str(Path(hardware).parent/'design.dcp')
    assert dcp in producer and dcp in result['source_sha256']"""
for folder in (P,P.parent/'residue_frontier_f5_trial'):
    source=folder/'audit_frontier_power.py'
    target=folder/'audit_frontier_power_v2.py'
    text=source.read_text();assert text.count(old)==1
    wanted=text.replace(old,new)
    assert not target.exists(), 'Preserve audit versions'
    target.write_text(wanted)
    print('AUDITOR V2',target,hashlib.sha256(target.read_bytes()).hexdigest())
