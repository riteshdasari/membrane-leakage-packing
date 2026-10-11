"""Retain TLS error; independently accept only the complete original checksum."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;plan=json.loads((P/'range_download_plan.json').read_text())
target=P/'assets/cifar-10-python-ranged.tar.gz';assert not target.exists()
sha=hashlib.sha256();md5=hashlib.md5();records=[];size=plan['bytes'];chunk=plan['chunk_bytes']
with target.open('xb')as out:
    for i in range(41):
        path=P/'dataset_ranges'/f'{i:03d}.bin';expected=min(chunk,size-i*chunk)
        assert path.stat().st_size==expected,(i,path.stat().st_size,expected)
        part=hashlib.sha256()
        with path.open('rb')as f:
            for b in iter(lambda:f.read(1024*1024),b''):out.write(b);sha.update(b);md5.update(b);part.update(b)
        records.append(dict(index=i,bytes=expected,path=str(path),sha256=part.hexdigest()))
assert sha.hexdigest()==plan['expected_sha256']and md5.hexdigest()==plan['expected_md5'],(sha.hexdigest(),md5.hexdigest())
result=dict(status='pass_original_dataset_integrity',path=str(target),bytes=size,sha256=sha.hexdigest(),md5=md5.hexdigest(),records=records,
    earlier_transport_attempt_retained='One concurrent future reported a TLS EOF; complete retained chunk bytes are accepted only after independent original full archive SHA256 and MD5 verification.',
    recovery_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    original_source_sha256=hashlib.sha256((P/'acquire_data_ranges.py').read_bytes()).hexdigest())
assert not(P/'range_download_acceptance.json').exists()
(P/'range_download_acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print('RETAINED RANGES ORIGINAL ARCHIVE SHA256 AND MD5 PASS',flush=True)
