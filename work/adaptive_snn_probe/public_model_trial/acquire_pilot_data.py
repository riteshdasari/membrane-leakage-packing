"""Predeclared first64 held-out CIFAR10 samples; not full-test accuracy."""
from pathlib import Path
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,io,sys
sys.dont_write_bytecode=True
from PIL import Image
import numpy as np
P=Path(__file__).resolve().parent
def get(url):
    with urlopen(Request(url,headers={'User-Agent':'SNN-packing-research'}),timeout=30)as f:return f.read()
plan=dict(dataset='uoft-cs/cifar10',split='test',indices=list(range(64)),
    purpose='Deterministic compatibility pilot; full10000 test accuracy is a separate unfinished gate.',
    units=[16,64,256,1024],rounding='numpy rint nearest even, observed-operand screen only; no claim of integer model equivalence',
    baseline='Published floating-point GLIF checkpoint at its original T2, no retraining, no current clipping')
assert not(P/'pilot_plan.json').exists();(P/'pilot_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
meta=get('https://huggingface.co/api/datasets/uoft-cs/cifar10');(P/'hf_dataset_metadata.json').write_bytes(meta)
raw=get('https://datasets-server.huggingface.co/rows?dataset=uoft-cs/cifar10&config=plain_text&split=test&offset=0&length=64')
(P/'hf_pilot_rows.json').write_bytes(raw);rows=json.loads(raw)['rows'];assert len(rows)==64
folder=P/'pilot_images';folder.mkdir()
def one(row):
    idx=row['row_idx'];item=row['row'];url=item['img']['src'];b=get(url)
    p=folder/f'{idx:05d}.png';p.write_bytes(b)
    im=np.asarray(Image.open(io.BytesIO(b)).convert('RGB'),dtype=np.uint8);assert im.shape==(32,32,3)
    return idx,im,int(item['label']),dict(index=idx,label=int(item['label']),path=str(p),url=url,
        sha256=hashlib.sha256(b).hexdigest(),pixel_sha256=hashlib.sha256(im.tobytes()).hexdigest())
with ThreadPoolExecutor(max_workers=6)as ex:results=list(ex.map(one,rows))
assert [r[0]for r in results]==list(range(64))
np.savez_compressed(P/'pilot_test64.npz',images=np.stack([r[1]for r in results]),labels=np.array([r[2]for r in results],dtype=np.int64),indices=np.arange(64))
(P/'pilot_data_acquisition.json').write_text(json.dumps(dict(status='acquired_public_test64',
    dataset_commit=json.loads(meta)['sha'],records=[r[3]for r in results],original_archive_pixel_comparison_pending=True),indent=2)+'\n')
print('ACQUIRED PUBLIC HELD-OUT CIFAR10 TEST64',flush=True)
