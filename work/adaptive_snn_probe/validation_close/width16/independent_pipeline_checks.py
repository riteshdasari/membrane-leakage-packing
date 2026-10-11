"""Source/operand/provenance review only; never invokes vendor tools."""
from pathlib import Path
import ast
import hashlib
import json
import numpy as np

P=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


checks=[]
for rel in ['preparation_v2.json','energy16_preparation.json','lutceil_e7/preparation.json',
            'lutceil_e7/followup_v2_preparation.json','domain_acceptance_glif_v2.json']:
    d=read(P/rel)
    n=0
    for bucket in ['source_sha256','artifact_sha256']:
        for path,digest in d.get(bucket,{}).items():
            assert sha(path)==digest,(rel,path)
            n+=1
    for co in d.get('cohorts',{}).values():
        for path,digest in co.get('artifact_sha256',{}).items():
            assert sha(path)==digest,(rel,path)
            n+=1
    checks.append({'file':rel,'pin_checks':n,'changed':0})

domain=read(P/'domain_acceptance_glif_v2.json')
cohorts=[]
for name,co in domain['cohorts'].items():
    with np.load(co['expected_outputs_file']) as stored:
        u=stored['U'].astype(np.int64)
        beta=stored['beta'].astype(np.int64)
        lengths=stored['frame_lengths'].astype(np.int64)
        wanted=stored['expected_leak'].astype(np.int64)
    assert len(u)==len(beta)==len(wanted)==co['operations']
    assert np.all((-32768<=u)&(u<=32767))
    assert np.all((0<=beta)&(beta<=256))
    assert np.all(lengths>0) and lengths.sum()==len(u)
    # Independent quotient/remainder formulation, including negative products.
    quotient,remainder=np.divmod(u*beta,256)
    scalar=quotient+(remainder!=0)
    assert np.array_equal(scalar,wanted),name
    ends=np.repeat(np.cumsum(lengths),lengths)
    lines=Path(co['stimulus_file']).read_text().splitlines()
    assert int(lines[0])==len(u) and len(lines)==len(u)+1
    for pos,line in enumerate(lines[1:]):
        a,b,end=map(int,line.split())
        assert (a,b,end)==(int(u[pos]),int(beta[pos]),int(ends[pos]))
    request_counts=[]
    for engine,wanted_requests in enumerate(co['expected_requests_by_engine']):
        if engine==6:
            assert np.all(beta==128)
        count=pos=0
        while pos<len(u):
            pair=pos+1<ends[pos]
            if engine==4:
                pair=False
            elif engine==1:
                pair=pair and beta[pos]==beta[pos+1]
            elif engine in (0,5):
                pair=pair and beta[pos]==beta[pos+1] and -256<=u[pos]<=255 and -256<=u[pos+1]<=255
                if engine==0:
                    pair=pair and beta[pos]>=64
            pos+=2 if pair else 1
            count+=1
        assert count==wanted_requests,(name,engine,count,wanted_requests)
        request_counts.append(count)
    cohorts.append({'cohort':name,'scalar_cases':len(u),'frame_count':len(lengths),
                    'requests_by_engine':request_counts,
                    'E7_expected_requests':request_counts[2],
                    'exact_scalar_and_payload_mismatches':0})

scripts=[P/f for f in ['run_native16_v2.py','run_energy16_12.py','audit_power16_12.py',
    'lutceil_e7/run_native16_lutceil_v2.py','lutceil_e7/run_energy16_lutceil_12.py',
    'lutceil_e7/audit_power16_lutceil_12.py']]
for path in scripts:
    ast.parse(path.read_text(),filename=str(path))
native_e7=(P/'lutceil_e7/tb_native16_lutceil.sv').read_text()
assert '.E(g==6?7:g)' in native_e7
runner_e7=(P/'lutceil_e7/run_native16_lutceil_v2.py').read_text()
assert 'engine=(7 if e==6 else e),native_index=e' in runner_e7
energy_e7=(P/'lutceil_e7/run_energy16_lutceil_12.py').read_text()
assert "trace{row.get('native_index',e)}.txt" in energy_e7
audit_e7=(P/'lutceil_e7/audit_power16_lutceil_12.py').read_text()
assert "cohort['expected_requests_by_engine'][2 if e==7 else e]" in audit_e7
assert "trace{row.get('native_index',e)}.txt" in audit_e7

result={'status':'pass_source_and_software_review_no_vendor_launch',
        'manifest_pin_checks':checks,'cohorts':cohorts,
        'E7_mapping':'native slot6 -> implementation E7 -> acceptance engine7/native_index6 -> trace6; request oracle uses E2 pair-count slot2',
        'serious_correctness_findings':[],
        'provenance_hardening':'Native/energy jobs do not always pin imported run_selective_energy.py or installed glbl.v; numerical/payload/SDF checks remain independent, but record those hashes in a closure manifest for complete execution provenance.',
        'source_sha256':{str(p.resolve()):sha(p) for p in [Path(__file__),*scripts]}}
(P/'independent_pipeline_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
