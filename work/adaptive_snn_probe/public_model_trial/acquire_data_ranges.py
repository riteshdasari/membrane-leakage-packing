"""Parallel provider-supported ranges, then original archive integrity checks."""
from pathlib import Path
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;folder=P/'dataset_ranges';folder.mkdir()
url='https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz';size=170498071;chunk=4*1024*1024
plan=dict(url=url,bytes=size,chunk_bytes=chunk,threads=8,expected_sha256='6d958be074577803d12ecdefd02955f39262c83c16fe9348329d7fe0b5c001ce',
    expected_md5='c58f30108f718f92721af3b95e74349a',scope='Identical official archive, faster transport only')
(P/'range_download_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
start_time=time.monotonic()
def one(index):
    start=index*chunk;end=min(start+chunk,size)-1;path=folder/f'{index:03d}.bin'
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'Range':f'bytes={start}-{end}','User-Agent':'SNN-packing-research'}),timeout=60)as r:
                assert r.status==206 and r.headers['Content-Range']==f'bytes {start}-{end}/{size}'
                with path.open('wb')as f:
                    while b:=r.read(128*1024):f.write(b)
                assert path.stat().st_size==end-start+1
            return dict(index=index,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        except Exception:
            if attempt==2:raise
with ThreadPoolExecutor(max_workers=8)as ex:
    records=[]
    for job in as_completed([ex.submit(one,i)for i in range((size+chunk-1)//chunk)]):
        records.append(job.result());print('DATA RANGES',len(records),41,'seconds',round(time.monotonic()-start_time,1),flush=True)
target=P/'assets/cifar-10-python-ranged.tar.gz';assert not target.exists()
sha=hashlib.sha256();md5=hashlib.md5()
with target.open('xb')as out:
    for i in range(41):
        with(folder/f'{i:03d}.bin').open('rb')as f:
            for b in iter(lambda:f.read(1024*1024),b''):out.write(b);sha.update(b);md5.update(b)
assert sha.hexdigest()==plan['expected_sha256']and md5.hexdigest()==plan['expected_md5']
result=dict(status='pass_original_dataset_integrity',path=str(target),bytes=size,sha256=sha.hexdigest(),md5=md5.hexdigest(),
    records=sorted(records,key=lambda x:x['index']),elapsed_seconds=time.monotonic()-start_time)
(P/'range_download_acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print('ORIGINAL CIFAR10 ARCHIVE INTEGRITY PASS',flush=True)
