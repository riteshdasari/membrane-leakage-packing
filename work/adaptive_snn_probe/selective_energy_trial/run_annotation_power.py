"""Generate aligned annotation reports; no comparative claim is made here."""
from pathlib import Path
import argparse
import sys
sys.dont_write_bytecode=True
import run_selective_energy as base

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--variant',type=int,choices=(2,3),required=True)
    parser.add_argument('--replay-dir',type=Path,required=True)
    parser.add_argument('--saif',type=Path,required=True)
    parser.add_argument('--attempt',type=int,default=0)
    args=parser.parse_args()
    if not args.run:print('No tools run; annotation and coverage are not yet audited.');return
    replay=args.replay_dir.resolve();saif=args.saif.resolve()
    check=base.read(replay/'replay_checks.json')
    assert check['status']=='timing_pass_activity_pending' and check['variant']==args.variant
    base.verify(check['source_sha256']);base.verify(check['artifact_sha256'])
    normalized=base.read(saif.with_suffix('.names.json'))
    assert normalized['source_sha256']==check['saif']['saif_sha256']
    assert normalized['target_sha256']==base.sha(saif)
    assert all(normalized[key] for key in ('ordered_numeric_records_unchanged','hierarchy_unchanged','duration_unchanged'))
    wd=base.stage_dir('annotated_power',args.variant,args.attempt)
    stamps=base.frozen() | base.pins([Path(__file__),base.P/'annotation_power_audit.tcl',
        base.P/'normalize_saif_names.py',saif,saif.with_suffix('.names.json'),replay/'replay_checks.json'])
    base.write(wd/'provenance.json',stamps)
    dcp=base.COMMON/f'results/top_guard_add_selective_v{args.variant}_route/design.dcp'
    argv=[base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
        '-source',base.P/'annotation_power_audit.tcl','-tclargs',args.variant,dcp,saif,wd]
    log=base.job([str(x).replace('\\','/') for x in argv],wd,'annotation',stamps,2.3)
    assert f'SELECTIVE_ANNOTATION_POWER PASS V{args.variant}' in log.read_text()
    base.write(wd/'evidence.json',dict(status='annotation and power reports generated; audit required',
        variant=args.variant,replay_dir=str(replay),saif_file=str(saif),source_sha256=stamps,
        artifact_sha256=base.pins(path for path in wd.iterdir() if path.is_file()),
        duration_seconds=check['saif']['duration_seconds'],neurons=635904,
        scope='OOC vendor estimate, no comparative energy claim before coverage/precision checks'))
    print('ANNOTATION REPORTS COMPLETE',wd,flush=True)

if __name__=='__main__':main()
