"""Create an additive representative runner using certified cached energy checks."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;REP=P/'ottt_representative'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace(text,old,new,n=1):
    assert text.count(old)==n,(old,text.count(old),n)
    return text.replace(old,new)


def main():
    original=P/'run_energy_recovery_child.py';child=P/'run_energy_recovery_representative_child.py'
    text=original.read_text();new=text
    new=replace(new,"ALT = P / 'lutceil_e7'","ALT = P / 'lutceil_e7'\nREP = P / 'ottt_representative'")
    new=replace(new,"root = ALT if args.engine == 7 else P","root = REP if args.workload == 'ottt_representative' else (ALT if args.engine == 7 else P)")
    new=replace(new,"('run_energy16_lutceil_12.py' if args.engine == 7 else 'run_energy16_12.py')","('run_energy16_rep3_12.py' if args.workload == 'ottt_representative' else ('run_energy16_lutceil_12.py' if args.engine == 7 else 'run_energy16_12.py'))")
    new=replace(new,"assert args.workload != 'ottt' or args.engine != 7","assert args.workload != 'ottt' or args.engine != 7\n    assert args.workload != 'ottt_representative' or args.engine in (5,1,6)")
    new=replace(new,"('audit_power16_lutceil_12_certified.py' if args.engine == 7 else 'audit_power16_12_certified.py')","('audit_power16_rep3_12_certified.py' if args.workload == 'ottt_representative' else ('audit_power16_lutceil_12_certified.py' if args.engine == 7 else 'audit_power16_12_certified.py'))")
    new=replace(new,"('audit_power16_lutceil_12_certified.py' if e==7 else 'audit_power16_12_certified.py')","('audit_power16_rep3_12_certified.py' if args.workload == 'ottt_representative' else ('audit_power16_lutceil_12_certified.py' if e==7 else 'audit_power16_12_certified.py'))")
    new=replace(new,"choices=['glif','ottt']","choices=['ottt_representative']")
    new=replace(new,"('run_energy16_lutceil_12.py' if args.engine==7 else 'run_energy16_12.py')","('run_energy16_rep3_12.py' if args.workload == 'ottt_representative' else ('run_energy16_lutceil_12.py' if args.engine==7 else 'run_energy16_12.py'))")
    ast.parse(new)
    if child.exists():assert child.read_text()==new
    else:child.write_text(new,encoding='utf-8')
    originalprep=REP/'prepare_and_run.py';prep=REP/'prepare_and_run_certified.py'
    text=originalprep.read_text();new=text
    new=replace(new,"P/'run_energy16_rep3_12.py'","W/'run_energy_recovery_representative_child.py'",n=2)
    new=replace(new,"P/'audit_power16_rep3_12.py'","P/'audit_power16_rep3_12_certified.py'",n=2)
    new=replace(new,"'--engines',str(e)","'--engine',str(e)")
    new=replace(new,"'--attempt',tag])","'--attempt',tag,'--run'])")
    new=replace(new,"P/f'energy12_{WORKLOAD}_{tag}_golden_export_replay_power_progress.json'","P/f'energy_recovery_{WORKLOAD}_e{e}_{tag}_progress.json'")
    new=replace(new,"P/'cohort_acceptance.json',P/'domain_acceptance_ottt_representative.json'","P/'cohort_acceptance.json',P/'domain_acceptance_ottt_representative.json',W/'representative_certified_runner_source_checks.json',W/'certify_energy_export.py'")
    ast.parse(new)
    if prep.exists():assert prep.read_text()==new
    else:prep.write_text(new,encoding='utf-8')
    report=dict(status='pass_additive_representative_certified_runner_source_checks',
        native_trace_oracle_and_capture_distribution_checks_unchanged=True,
        golden_SDF_SAIF_and_physical_net_power_checks_inherited_from_frozen_producer=True,
        added_checks='Certified EOF-only balanced export and exact SDF annotation path; arrays cached once.',
        source_sha256={str(Path(__file__).resolve()):sha(__file__),str(original):sha(original),str(originalprep):sha(originalprep),
            str(P/'cached_energy_auditor_source_equivalence.json'):sha(P/'cached_energy_auditor_source_equivalence.json'),
            str(P/'certified_energy_auditor_source_checks.json'):sha(P/'certified_energy_auditor_source_checks.json')},
        artifact_sha256={str(child):sha(child),str(prep):sha(prep)},vendor_jobs_launched=False)
    dest=P/'representative_certified_runner_source_checks.json'
    if dest.exists():assert json.loads(dest.read_text())==report
    else:dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],manifest=str(dest))))


if __name__=='__main__':main()
