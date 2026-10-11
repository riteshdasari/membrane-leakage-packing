"""Prepare matched route/export/complete-SDF/power tools; never launch jobs."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
OLD=P.parent/'residue_frontier_trial'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def replace(source,old,new,count=1):
    assert source.count(old)==count,(old,source.count(old),count)
    return source.replace(old,new)


def main():
    dst=P/'run_u13_physical.py';assert not dst.exists(),'Preserve prepared runner'
    original=(OLD/'run_frontier.py').read_text()
    a=original.index('def frozen():');b=original.index('\ndef sources():',a)
    original=original[:a]+'''def frozen():
    manifest=read(P/'rtl_preparation_manifest.json')
    for key in ('source_sha256','prepared_sha256'):verify(manifest[key])
    manifest2=read(P/'physical_preparation_manifest.json')
    for key in ('source_sha256','prepared_sha256'):verify(manifest2[key])
    return manifest['source_sha256']|manifest['prepared_sha256']|manifest2['source_sha256']|manifest2['prepared_sha256']|pins([P/'rtl_preparation_manifest.json',P/'physical_preparation_manifest.json'])

''' + original[b:]
    a=original.index('def sources():');b=original.index('\ndef directory(',a)
    original=original[:a]+'''def sources():
    return pins([Path(__file__),P/'CONTRACT.md',P/'guard_add_frontier_u13.sv',
                 P/'guard_add_frontier_u13_timing.sv',P.parent/'guard_add.sv',
                 P/'prepared_algebra_checks.json'])

''' + original[b:]
    a=original.index('def native(');b=original.index('\ndef route(',a)
    original=original[:a]+original[b:]
    original=original.replace('top_guard_add_frontier_e','top_guard_add_frontier_u13_e')
    original=original.replace("P/'route_frontier.tcl'","P/'route_u13.tcl'")
    original=original.replace("P/'export_frontier.tcl'","P/'export_u13.tcl'")
    original=original.replace("==290","==338").replace("==183","==215").replace("==107","==123")
    original=original.replace('fixture,290FF','fixture,338FF')
    v4=(OLD/'run_frontier_replay_transport_v4.py').read_text()
    replay=v4[v4.index('def replay('):v4.index("\n\nif __name__=='__main__':")]
    replay=replace(replay,'tb=prepare_tb()',"tb=P/'tb_frontier_u13_route_replay.sv'")
    replay=replay.replace('run.','').replace('tb_frontier_route_replay','tb_frontier_u13_route_replay')
    a=original.index('def replay(');b=original.index('\ndef power(',a)
    original=original[:a]+replay+'\n\n'+original[b:]
    original=original.replace("P/'annotation_frontier.tcl'","P/'annotation_u13.tcl'")
    original=replace(original,"choices=('native','route','export','replay','power')","choices=('route','export','replay','power')")
    original=replace(original,"    if args.stage=='native':native(args.kind,args.stall,args.attempt)\n    elif args.stage=='route':route(args.engine,args.attempt)",
        "    if args.stage=='route':route(args.engine,args.attempt)")
    original=replace(original,'Serial RAM-gated full frontier validation; original evidence stays frozen.',
        'Prepared U13 physical validation: root-only serial RAM-gated execution.')
    dst.write_text(original)
    annotation=(OLD/'annotation_frontier.tcl').read_text().replace('tb_frontier_route_replay','tb_frontier_u13_route_replay')
    (P/'annotation_u13.tcl').write_text(annotation)
    auditor=(OLD/'audit_frontier_power_v4.py').read_text()
    auditor=auditor.replace('tb_frontier_route_replay','tb_frontier_u13_route_replay')
    auditor=auditor.replace('290','338').replace('183','215').replace('107','123').replace('524288','2097152')
    (P/'audit_u13_power.py').write_text(auditor)
    originals=[OLD/'run_frontier.py',OLD/'run_frontier_replay_transport_v4.py',
        OLD/'annotation_frontier.tcl',OLD/'audit_frontier_power_v4.py',Path(__file__)]
    outputs=[dst,P/'annotation_u13.tcl',P/'audit_u13_power.py']
    (P/'physical_preparation_manifest.json').write_text(json.dumps(dict(
        source_sha256={str(p):sha(p) for p in originals},
        prepared_sha256={str(p):sha(p) for p in outputs},
        scope='Preparation only: no synthesis/export/replay/power process launched; accepted transport/max and all four zero pulse settings retained'),indent=2)+'\n')
    print('U13 PHYSICAL FLOW PREPARED',flush=True)


if __name__=='__main__':main()
