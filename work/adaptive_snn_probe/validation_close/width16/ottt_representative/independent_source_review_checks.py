"""Independent host/source review only: no module/model/vendor execution."""
from pathlib import Path
import ast, hashlib, json
import numpy as np

P=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())

def main():
    names=('prepare_and_run.py','run_native16_rep3.py','run_energy16_rep3_12.py','audit_power16_rep3_12.py')
    trees={name:ast.parse((P/name).read_text(),filename=str(P/name)) for name in names}
    allpins={}
    for name in ('source_acceptance.json','preparation_rep3.json','energy16_preparation_rep3.json'):
        d=read(P/name)
        for kind in ('source_sha256','artifact_sha256'):
            for file,pin in d.get(kind,{}).items():
                assert file not in allpins or allpins[file]==pin
                allpins[file]=pin
    for file,pin in allpins.items():assert sha(file)==pin,('Changed review source',file)
    copies=('leak_core16.sv','leak_dsp.sv','timing16.sv','tb_native16.sv','tb_energy16_12.sv','export16_12.tcl','power16_12.tcl')
    for name in copies:assert sha(P/name)==sha(P.parent/name)
    # Extract only these host functions: importing the implementation is unnecessary.
    funcs=[n for n in trees[names[0]].body if isinstance(n,ast.FunctionDef) and n.name in ('counts','verify_capture')]
    ns=dict(np=np,Path=Path,read=read)
    exec(compile(ast.fix_missing_locations(ast.Module(body=funcs,type_ignores=[])),str(P/names[0]),'exec'),ns)
    try:
        ns['verify_capture'](P/'source_test_failed_capture.json')
        raise RuntimeError('Failed capture status was accepted')
    except AssertionError as exc:assert 'failed distribution' in str(exc)
    def independent_counts(U,lengths):
        # Pair count is floor(run_length/2) over maximal narrow runs, per frame.
        totals=[0]*7;pos=0
        for n in map(int,lengths):
            v=U[pos:pos+n];mask=(-256<=v)&(v<=255)
            edge=np.flatnonzero(np.diff(np.r_[False,mask,False].astype(np.int8)))
            pairs=int(((edge[1::2]-edge[::2])//2).sum())
            row=(n-pairs,(n+1)//2,(n+1)//2,(n+1)//2,n,n-pairs,(n+1)//2)
            totals=[a+b for a,b in zip(totals,row)];pos+=n
        assert pos==len(U)
        return totals
    with np.load(P.parent/'actual128_expected.npz') as d:
        actual=ns['counts'](d['U'],d['frame_lengths']);oracle=independent_counts(d['U'],d['frame_lengths'])
        assert actual==oracle==[6282,3671,3671,3671,7335,6282,3671]
    cases=([-256,255],[-257,256],[255,-256,300],[-256,255,-256,255,0],[-32768,32767])
    checked=0
    for values in cases:
        U=np.array(values)
        for split in range(1,len(U)+1):
            lengths=np.array([split]+([len(U)-split] if split<len(U) else []))
            assert ns['counts'](U,lengths)==independent_counts(U,lengths);checked+=1
    tb=(P/'tb_native16_rep3.sv').read_text();native=(P/names[1]).read_text();energy=(P/names[2]).read_text();audit=(P/names[3]).read_text()
    assert '.E(g==0?5:(g==1?1:6))' in tb and 'localparam integer ENGINES=3' in tb
    assert 'for index,e in enumerate((5,1,6)):' in native and 'native_index=index' in native
    assert 'trace=checkfile.parent/f"trace{row[\'native_index\']}.txt"' in energy
    assert "row['native_index']=={5:0,1:1,6:2}[e]" in audit
    active=list(P.glob('closure_*.json'))
    result=dict(status='pass_independent_source_only_review',AST_scripts=4,unique_verified_manifest_pins=len(allpins),byte_identical_parent_copies=len(copies),native_index_to_engine={0:5,1:1,2:6},independent_runlength_request_oracle_stress_operations=7335,boundary_frame_cases=checked,failed_distribution_capture_rejected=True,model_execution=False,vendor_execution=False,capture_or_energy_acceptance=False,closure_files_present_at_review=[str(x)for x in active],source_sha256={str(p.resolve()):sha(p)for p in [Path(__file__),*[P/n for n in names],P/'tb_native16_rep3.sv',P/'source_acceptance.json',P/'preparation_rep3.json',P/'energy16_preparation_rep3.json',P/'README.md']})
    (P/'independent_source_review_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
