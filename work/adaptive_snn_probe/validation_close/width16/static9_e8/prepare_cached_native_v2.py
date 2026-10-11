"""Prepare array-cached host audit without touching the pinned native v1."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    original=P/'run_native_static9.py';target=P/'run_native_static9_v2.py';assert not target.exists()
    t=original.read_text();old="    a=np.load(output);ends=np.repeat(np.cumsum(a['frame_lengths']),a['frame_lengths']);rows=[]"
    new="""    # Cache compressed NPZ arrays once; array access in the request loop stays O(1).
    with np.load(output)as a:
        operands=a['U'];coefficients=a['beta'];expected_leak=a['expected_leak'];frame_lengths=a['frame_lengths']
    ends=np.repeat(np.cumsum(frame_lengths),frame_lengths);rows=[]"""
    assert t.count(old)==1;t=t.replace(old,new)
    # Preserve every loop expression while removing repeated zip-member decoding.
    for key,name in [('U','operands'),('beta','coefficients'),('expected_leak','expected_leak')]:
        start=t.index('    ends=np.repeat');t=t[:start]+t[start:].replace("a['"+key+"']",name)
    ast.parse(t);target.write_text(t,encoding='utf-8')
    result=dict(status='prepared_cached_arrays_semantics_preserved_no_vendor',source_sha256={str(original):sha(original),str(Path(__file__)):sha(Path(__file__))},artifact_sha256={str(target):sha(target)},
                change='Load four compressed NPZ arrays once before the independent request loop. Vendor commands, RTL, cohort selection, output/count/oracle/latency/protocol gates and acceptance schema unchanged.')
    (P/'cached_native_v2_preparation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],runner=str(target))))
if __name__=='__main__':main()
