"""Freeze an additive new-top energy runner/auditor; do not launch vendor jobs."""
from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent;W=P.parent;ROOT=W.parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
 assert not(P/'energy_preparation.json').exists()
 old=W/'lutceil_e7/audit_power16_lutceil_12.py'
 source=old.read_text()
 # Retain the previously accepted physical-net audit functions and complete
 # power accounting verbatim except explicit comparator identity restrictions.
 tail=source[source.index('def tcl_words(line):'):]
 edits=[("assert engine in range(8)","assert engine==9"),
        ("hardware['status'] == 'pass' and hardware['engine'] == engine","hardware['status'] == 'pass' and hardware['label']=='shared_GLIF_checkpoint_MCM_LUT2'"),
        ("assert len(dsps) == [1,1,0,2,1,1,0,0][engine]","assert len(dsps)==0"),
        ("assert hardware['WNS_ns'] >= 0 and hardware['WHS_ns'] >= 0","assert all(hardware[k]>=0 for k in ('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))")]
 for before,after in edits:
  assert tail.count(before)==1,(before,tail.count(before))
  tail=tail.replace(before,after)
 header=(P/'audit_energy_glif_mcm_header.py').read_text()
 complete=header+'\n\n'+tail+'\n\n'+(P/'audit_energy_glif_mcm_certificate.py').read_text()
 ast.parse(complete);(P/'audit_energy_glif_mcm.py').write_text(complete,encoding='utf-8')
 (P/'tb_energy_glif_mcm.sv').write_bytes((W/'tb_energy16_12.sv').read_bytes())
 (P/'export_energy_glif_mcm.tcl').write_bytes((W/'export16_12.tcl').read_bytes())
 power=(W/'power16_12.tcl').read_text()
 before='if {$engine < 0 || $engine > 6} {error "Engine outside 0..6"}'
 assert power.count(before)==1
 power=power.replace(before,'if {$engine != 9} {error "This measurement accepts only shared GLIF MCM engine9"}')
 before='open_checkpoint $dcp\n';assert power.count(before)==1
 power=power.replace(before,before+'if {[get_property NAME [current_design]] ne "top_sequential_leak16_glif_mcm"} {error "Shared GLIF MCM top mismatch"}\n')
 (P/'power_energy_glif_mcm.tcl').write_text(power,encoding='utf-8')
 for name in ('run_energy_glif_mcm.py','audit_energy_glif_mcm.py'):ast.parse((P/name).read_text())
 newfiles=[Path(__file__),P/'audit_energy_glif_mcm_header.py',P/'audit_energy_glif_mcm_certificate.py',P/'audit_energy_glif_mcm.py',
           P/'run_energy_glif_mcm.py',P/'tb_energy_glif_mcm.sv',P/'export_energy_glif_mcm.tcl',P/'power_energy_glif_mcm.tcl']
 existing=[P/'preparation.json',P/'leak_glif_mcm.sv',P/'timing_glif_mcm.sv',W/'domain_acceptance_glif_v2.json',
           W/'actual_glif_expected.npz',W/'actual_glif_stim.txt',old,W/'audit_power16_12_certified.py',W/'certify_energy_export.py',
           W/'tb_energy16_12.sv',W/'export16_12.tcl',W/'power16_12.tcl',
           W.parent/'lut_isolation/create_eof_only_sdf_derivative.py',W.parent/'lut_isolation/sdf_structure_audit_v1.py',
           W.parent/'lut_isolation/verify_eof_only_sdf_derivative_v1.py',ROOT/'selective_energy_trial/run_selective_energy.py',
           ROOT/'selective_energy_trial/replay_selective_energy.py',ROOT/'selective_energy_trial/normalize_saif_names.py',
           ROOT/'selective_energy_trial/audit_selective_energy.py']
 d=dict(status='prepared_new_measurement_no_vendor_launch',engine=9,top='top_sequential_leak16_glif_mcm',B=16,clock_ns=12,fixture_FF=94,
        required_before_launch='passed captured actual_glif native receipt and passed matched12ns shared-MCM route',
        preserved_physical_audit_functions=['tcl_words','connectivity','normalization_audit','annotation'],
        explicit_physical_audit_identity_changes=[dict(before=a,after=b)for a,b in edits],
        fixture_bench_bytes_identical=sha(P/'tb_energy_glif_mcm.sv')==sha(W/'tb_energy16_12.sv'),
        export_tcl_bytes_identical=sha(P/'export_energy_glif_mcm.tcl')==sha(W/'export16_12.tcl'),
        SDF='preserved raw export plus certified EOF-only derived export and one annotation-path replacement; all numerical timing unchanged',
        gates='complete native inputs and known controls/data through golden fixture; complete maxdelay transport SDF replay; no timing-check waiver; exact ROI duration; normalized states unchanged; every physical net matched and known; exact selected design and power settings',
        source_sha256={str(p.resolve()):sha(p)for p in newfiles+existing},
        scope='Fresh representative GLIF complete-fixture vendor dynamic estimate; no historical energy reuse, board/static/neuron/memory claim.')
 (P/'energy_preparation.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(d|dict(source_sha256=f'{len(d["source_sha256"])} source bindings'),indent=2))


if __name__=='__main__':main()
