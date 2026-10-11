"""Read-only explicit-path existence/status snapshot; not a new acceptance audit."""
from pathlib import Path
import hashlib,json,datetime,sys
sys.dont_write_bytecode=True
C=Path(__file__).resolve().parent;W=C/'width16';R=C.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def item(p):
    p=Path(p).resolve();d=dict(path=str(p),exists=p.exists())
    if p.is_file():
        d['sha256']=sha(p)
        if p.suffix=='.json':
            v=json.loads(p.read_text());d['saved_receipt_status']=v.get('status','no_status_field')
    return d
def main():
    target=C/'fixed16_final_evidence_snapshot_a0.json';assert not target.exists()
    groups={
      'arithmetic':[W/'domain_acceptance_glif_v2.json',W/'preparation_v2.json',R/'sequential_paper_trial/stage3_algebra.json'],
      'model':[R/'sequential_paper_trial/stage2_acceptance.json',R/'sequential_paper_trial/stage3_results.json',C/'benchmarks/cifar10_T6_n64_a2/results.json',C/'benchmarks/cifar10_full10000_a0/results.json',C/'benchmarks/benchmark_acceptance.json'],
      'representative_activity':[C/'activity/random_stratified_v2/acceptance.json',C/'activity/random_stratified_v2/representativeness_acceptance.json',C/'activity/ottt_random_stratified_a0/results.json'],
      'routes':[W/'route_resolved_acceptance_a1.json',W/'lutceil_e7/hardware/route12_e7_close_a0/hardware.json'],
      'E8':[W/'static9_e8/hardware/native_pair_s0_close_a0/acceptance_cached_cached_review_a0.json',W/'static9_e8/cached_native_v2_gate.json'],
      'separate_unresolved':[C/'lut_isolation/isolation_audit.json',C/'prior_art/equivalence_audit.json',C/'prior_art/targeted_followup/followup_manifest.json']}
    record=dict(status='read_only_completion_snapshot_not_acceptance',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),B=16,period_ns=12,fixture_FF=94,
                receipts={k:[item(p)for p in paths]for k,paths in groups.items()},
                fixed16_power_audits=[item(p)for parent in[W/'hardware',W/'lutceil_e7/hardware',W/'ottt_representative/hardware']if parent.exists()for p in parent.rglob('power_audit.json')],
                missing_gates=['E8 pair stalled, scalar unstalled/stalled and selected route plus explicit closure audit','All matched fixed16 golden/SDF/physical-SAIF/power stages and explicit selected-evidence audit','True representative OTTT accepted capture and E5/E1/E6 matched energy','Full OTTT independent final verification and broader BNTT accepted experiment'],
                separate_limits=['Original E2 delayed numerical discrepancy remains separately unresolved','Four prior-work full-method access gaps preclude a first-ever equivalence claim'],
                source_sha256={str(Path(__file__).resolve()):sha(__file__),str(C/'fixed16_final_evidence_checklist_a0.md'):sha(C/'fixed16_final_evidence_checklist_a0.md')},
                scope='Availability and saved status only, not a fresh verification of all referenced evidence. Progress records are not treated as final accuracy. No vendor/model job launched.')
    target.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(path=str(target),status=record['status'],power_audits_found=len(record['fixed16_power_audits']),missing_receipts=[r['path']for rows in record['receipts'].values()for r in rows if not r['exists']])) )
if __name__=='__main__':main()
