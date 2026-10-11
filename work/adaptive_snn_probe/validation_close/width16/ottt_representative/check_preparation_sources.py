"""Small host/source checks only; does not execute inference or any vendor tool."""
from pathlib import Path
import ast,importlib.util,json,sys
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent
def main():
    scripts=[P/'prepare_and_run.py',P/'run_native16_rep3.py',P/'run_energy16_rep3_12.py',P/'audit_power16_rep3_12.py']
    for f in scripts:ast.parse(f.read_text(),filename=str(f))
    spec=importlib.util.spec_from_file_location('representative_capture_source_check',P/'prepare_and_run.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for name in('preparation_rep3.json','energy16_preparation_rep3.json'):
        d=module.read(P/name);module.verify(d['source_sha256']);module.verify(d['artifact_sha256'])
    W=P.parent
    for name in('leak_core16.sv','leak_dsp.sv','timing16.sv','tb_native16.sv','tb_energy16_12.sv','export16_12.tcl','power16_12.tcl'):assert module.sha(P/name)==module.sha(W/name)
    with np.load(W/'actual128_expected.npz')as sample:
        assert module.counts(sample['U'],sample['frame_lengths'])==[6282,3671,3671,3671,7335,6282,3671]
    cases=[([-256,255],[2],[1,1,1,1,2,1,1]),([256,-257],[2],[2,1,1,1,2,2,1]),([255,-256,300],[3],[2,2,2,2,3,2,2]),([-256,255],[1,1],[2,2,2,2,2,2,2])]
    for values,lengths,want in cases:assert module.counts(np.array(values),np.array(lengths))==want
    file=P/'source_test_failed_capture.json';assert not file.exists()
    file.write_text(json.dumps(dict(status='pass_exact_feedback_failed_distribution_gates',scope='Synthetic source-test rejection fixture; not a model result.')))
    try:module.verify_capture(file);raise RuntimeError('Failed distribution incorrectly accepted')
    except AssertionError as exc:assert 'failed distribution'in str(exc)
    assert not(P/'domain_acceptance_ottt_representative.json').exists(),'Source-only check must precede real capture preparation.'
    tb=(P/'tb_native16_rep3.sv').read_text();native=(P/'run_native16_rep3.py').read_text();energy=(P/'run_energy16_rep3_12.py').read_text();audit=(P/'audit_power16_rep3_12.py').read_text()
    assert '.E(g==0?5:(g==1?1:6))'in tb and 'localparam integer ENGINES=3'in tb
    assert 'for index,e in enumerate((5,1,6)):'in native and "native_index=index"in native
    assert "trace=checkfile.parent/f\"trace{row['native_index']}.txt\""in energy
    assert "row['native_index']=={5:0,1:1,6:2}[e]"in audit
    result=dict(status='pass_source_and_host_preparation_no_capture_no_vendor',byte_identical_source_copies=7,AST_scripts=4,
                native_mapping={0:5,1:1,2:6},independent_existing7335_issue_counts_pass=True,boundary_count_tests=4,failed_distribution_rejection_pass=True,
                energy_measurement_accepted=False,capture_measurement_accepted=False,
                source_sha256=module.pins([Path(__file__),*scripts,P/'tb_native16_rep3.sv',P/'preparation_rep3.json',P/'energy16_preparation_rep3.json']))
    out=P/'source_acceptance.json';assert not out.exists();module.write(out,result);print(json.dumps({k:v for k,v in result.items()if k!='source_sha256'}))
if __name__=='__main__':main()
