"""Acquire one official checkpoint and CIFAR10 archive with integrity checks."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,time,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
source=json.loads((P/'source_acquisition.json').read_text())
def download(name,url,expected_size=None,expected_git=None,expected_md5=None):
    target=P/'assets'/name;target.parent.mkdir(exist_ok=True)
    assert not target.exists()
    started=time.monotonic();sha=hashlib.sha256();md5=hashlib.md5();n=0
    with urlopen(Request(url,headers={'User-Agent':'SNN-packing-research'}),timeout=60)as r,target.open('xb')as f:
        while block:=r.read(1024*1024):f.write(block);sha.update(block);md5.update(block);n+=len(block)
    if expected_size is not None:assert n==expected_size,(n,expected_size)
    if expected_md5:assert md5.hexdigest()==expected_md5
    if expected_git:
        git=hashlib.sha1(f'blob {n}\0'.encode())
        with target.open('rb')as f:
            for b in iter(lambda:f.read(1024*1024),b''):git.update(b)
        assert git.hexdigest()==expected_git
    result=dict(path=str(target),url=url,bytes=n,sha256=sha.hexdigest(),md5=md5.hexdigest(),
        elapsed_seconds=time.monotonic()-started,expected_git_blob=expected_git,expected_md5=expected_md5)
    (P/(name+'.download.json')).write_text(json.dumps(result,indent=2)+'\n')
    print('ACQUIRED',name,n,'bytes',flush=True);return result
entry=source['model_tree_entry']
model_url='https://raw.githubusercontent.com/CAS-CLab/Gated-LIF/'+source['commit']+'/'+quote(entry['path'])
with ThreadPoolExecutor(max_workers=2)as ex:
    m=ex.submit(download,'glif_cifar10_T2.pth.tar',model_url,entry['size'],entry['sha'])
    d=ex.submit(download,'cifar-10-python.tar.gz','https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz',
        expected_md5='c58f30108f718f92721af3b95e74349a')
    records=[m.result(),d.result()]
(P/'asset_acquisition.json').write_text(json.dumps(dict(status='pass_download_integrity',records=records),indent=2)+'\n')
