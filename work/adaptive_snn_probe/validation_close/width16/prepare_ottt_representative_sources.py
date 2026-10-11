"""Isolate exact fixed16 sources for a future accepted representative OTTT capture."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;P=W/'ottt_representative';ROOT=W.parent.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(paths):return{str(p):sha(p)for p in paths}
def replace(t,a,b):assert t.count(a)>=1,(a,t[:50]);return t.replace(a,b)
def main():
    P.mkdir(exist_ok=True);assert not(P/'preparation_v2.json').exists()
    copied=[]
    for name in('leak_core16.sv','leak_dsp.sv','timing16.sv','tb_native16.sv','tb_energy16_12.sv','export16_12.tcl','power16_12.tcl'):
        target=P/name;assert not target.exists();target.write_bytes((W/name).read_bytes());assert sha(target)==sha(W/name);copied.append(target)
    native=(W/'run_native16_v2.py').read_text()
    native=replace(native,"ROOT=P.parent.parent","ROOT=P.parent.parent.parent")
    native=replace(native,"choices=['general','shift128','actual128','actual_glif']","choices=['actual_ottt_representative']")
    native=replace(native,"P/'domain_acceptance_glif_v2.json'","P/'domain_acceptance_ottt_representative.json'")
    native=replace(native,"shift=0 if args.cohort in('general','actual_glif') else 1","shift=1 # All7 controls; E6 legal because prepared operands are beta128.")
    native=replace(native,"scope='Native primitive exact outputs","scope='Representative OTTT64 arithmetic capture: native primitive exact outputs")
    native=P/'run_native16_rep.py',native
    energy=(W/'run_energy16_12.py').read_text()
    energy=replace(energy,"ROOT=P.parent.parent","ROOT=P.parent.parent.parent")
    energy=replace(energy,"P/'domain_acceptance_glif_v2.json'","P/'domain_acceptance_ottt_representative.json'")
    energy=replace(energy,"assert native['cohort']==('actual_glif'if ARGS.workload=='glif'else'actual128')","assert native['cohort']=='actual_ottt_representative'")
    energy=replace(energy,"choices=['glif','ottt']","choices=['ottt_representative']")
    energy=replace(energy,"P/'audit_power16_12.py'","P/'audit_power16_rep_12.py'")
    needle="    verify(hw['source_sha256']);verify(hw['artifact_sha256']);return wd,hw"
    inserted="""    verify(hw['source_sha256']);verify(hw['artifact_sha256'])
    # Golden copies must be identical to sources of this selected main route.
    for name in('leak_core16.sv','leak_dsp.sv','timing16.sv'):
        original=str((P.parent/name).resolve())
        assert hw['source_sha256'][original]==sha(P/name)==sha(original)
    return wd,hw"""
    energy=replace(energy,needle,inserted);energy=P/'run_energy16_rep_12.py',energy
    audit=(W/'audit_power16_12.py').read_text()
    audit=replace(audit,"OLD=P.parent.parent/'selective_energy_trial'","OLD=P.parent.parent.parent/'selective_energy_trial'")
    audit=replace(audit,"check['cohort'] in ('actual_glif','actual128')","check['cohort']=='actual_ottt_representative'")
    audit=replace(audit,"check['cohort']=='actual128'","check['cohort']=='actual_ottt_representative'")
    audit=replace(audit,"scope='Fixed16 actual source operands","scope='Representative OTTT64 fixed16 actual source operands")
    audit=replace(audit,"scope='Vendor estimated dynamic energy","scope='Representative OTTT64 after common zero filtering: vendor estimated dynamic energy")
    audit=P/'audit_power16_rep_12.py',audit
    generated=[]
    for target,text in(native,energy,audit):
        ast.parse(text);assert not target.exists();target.write_text(text,encoding='utf-8');generated.append(target)
    inputs=[Path(__file__),W/'preparation_v2.json',W/'energy16_preparation.json',W/'domain_acceptance_glif_v2.json',
            W/'run_native16_v2.py',W/'run_energy16_12.py',W/'audit_power16_12.py',
            W.parent/'activity/capture_ottt_representative.py',W.parent/'activity/ottt_capture_preparation.json',
            ROOT/'selective_energy_trial/run_selective_energy.py',ROOT/'selective_energy_trial/audit_selective_energy.py',
            ROOT/'selective_energy_trial/replay_selective_energy.py',ROOT/'selective_energy_trial/normalize_saif_names.py',
            *[W/p.name for p in copied]]
    d=dict(status='source_copies_prepared_no_capture_no_vendor',B=16,cohort='actual_ottt_representative',clock_ns=12,fixture_FF=94,
           source_sha256=pin(inputs),artifact_sha256=pin(copied+generated),
           copy_scope='All RTL/fixtures/TCL byte-identical main fixed16; runner/auditor changes only isolated paths, distinct cohort/workload and explicit expected operand binding.',
           source_only=True,required_capture_status='pass_exact_feedback_and_distribution_gates',energy_engines=[5,1,6])
    (P/'preparation_v2.json').write_text(json.dumps(d,indent=2)+'\n')
    d2=d|dict(source_sha256=d['source_sha256']|pin([P/'preparation_v2.json']))
    (P/'energy16_preparation.json').write_text(json.dumps(d2,indent=2)+'\n')
    print(json.dumps(dict(status=d['status'],destination=str(P),byte_identical_copies=len(copied),adapted_scripts=len(generated))))
if __name__=='__main__':main()
