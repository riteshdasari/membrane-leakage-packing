"""Retry missing transport ranges without overwriting prior attempt files."""
from pathlib import Path
from urllib.request import Request,urlopen
import hashlib,json,time,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;plan=json.loads((P/'range_download_plan.json').read_text())
folder=P/'dataset_ranges_v3';folder.mkdir();paths=[];records=[]
for i in range(41):
    start=i*plan['chunk_bytes'];n=min(plan['chunk_bytes'],plan['bytes']-start)
    old=P/'dataset_ranges'/f'{i:03d}.bin'
    if old.exists()and old.stat().st_size==n:path=old
    else:
        path=folder/f'{i:03d}.bin'
        for attempt in range(6):
            try:
                url=plan['url']+f'?packing_range={i}&attempt={attempt}'
                with urlopen(Request(url,headers={'Range':f'bytes={start}-{start+n-1}'}),timeout=60)as r:
                    assert r.status==206 and r.headers['Content-Range']==f'bytes {start}-{start+n-1}/{plan["bytes"]}'
                    with path.open('wb')as f:
                        while b:=r.read(128*1024):f.write(b)
                    assert path.stat().st_size==n
                print('RECOVERED MISSING RANGE',i,flush=True);break
            except Exception as error:
                print('RANGE RETRY',i,attempt,type(error).__name__,flush=True)
                if attempt==5:raise
                time.sleep(2)
    paths.append(path)
target=P/'assets/cifar-10-python-complete-v3.tar.gz';assert not target.exists()
sha=hashlib.sha256();md5=hashlib.md5()
with target.open('xb')as out:
    for i,path in enumerate(paths):
        part=hashlib.sha256()
        with path.open('rb')as f:
            for b in iter(lambda:f.read(1024*1024),b''):out.write(b);sha.update(b);md5.update(b);part.update(b)
        records.append(dict(index=i,path=str(path),bytes=path.stat().st_size,sha256=part.hexdigest()))
assert sha.hexdigest()==plan['expected_sha256']and md5.hexdigest()==plan['expected_md5'],(sha.hexdigest(),md5.hexdigest())
result=dict(status='pass_original_dataset_integrity',path=str(target),bytes=plan['bytes'],sha256=sha.hexdigest(),md5=md5.hexdigest(),records=records,
    earlier_transport_failures_retained=True,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
assert not(P/'range_download_acceptance.json').exists()
(P/'range_download_acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print('ORIGINAL ARCHIVE SHA256 AND MD5 PASS V3',flush=True)
