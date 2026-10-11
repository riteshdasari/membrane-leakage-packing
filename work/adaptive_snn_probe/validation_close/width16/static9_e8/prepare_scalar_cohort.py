"""Separate all signed9 scalar/beta native cohort, retained alongside pair cohort."""
from pathlib import Path
import hashlib,json
import numpy as np
P=Path(__file__).resolve().parent;sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert not(P/'scalar_cohort.json').exists()
values=np.tile(np.arange(-256,256,dtype=np.int64),257);beta=np.repeat(np.arange(257,dtype=np.int64),512)
N=len(values);path=P/'scalar_stim.txt'
with path.open('w',newline='\n')as f:
    f.write(str(N)+'\n')
    for i,(u,b)in enumerate(zip(values,beta)):f.write(f'{int(u)} {int(b)} {i+1}\n')
out=P/'scalar_expected.npz';np.savez_compressed(out,U=values,beta=beta,expected_leak=-np.floor_divide(-(values*beta),256),frame_lengths=np.ones(N,np.int64))
record=dict(status='prepared',legal_signed9_scalar_cases=N,expected_requests_by_native_index=[N,N],source_sha256={str(Path(__file__)):sha(Path(__file__)),str(P/'preparation.json'):sha(P/'preparation.json')},artifact_sha256={str(p):sha(p)for p in[path,out]})
(P/'scalar_cohort.json').write_text(json.dumps(record,indent=2)+'\n');print('E8 NATIVE SCALAR COHORT PREPARED',N,flush=True)
