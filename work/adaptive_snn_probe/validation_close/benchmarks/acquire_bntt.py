"""Acquire author checkpoint and canonical TinyImageNet bytes; no inference."""
from pathlib import Path
import hashlib, json, time, urllib.request, zipfile
P=Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    assets=[('bntt_pretrained_tiny_t30.pth.tar','https://drive.usercontent.google.com/download?id=11ybFXqRB3edxsFMUrPrwwH5_HlAAHNUp&export=download&confirm=t',51198934),
        ('tiny-imagenet-200.zip','https://cs231n.stanford.edu/tiny-imagenet-200.zip',248100043)]
    evidence={'source_repository':'https://github.com/Intelligent-Computing-Lab-Panda/Visual-Explanations-from-Spiking-Neural-Networks-using-Interspike-Intervals',
        'source_commit':'178789c74fef72b9c25bd31d65ac598c987e1de9',
        'official_checkpoint_readme':'https://github.com/Intelligent-Computing-Lab-Panda/Visual-Explanations-from-Spiking-Neural-Networks-using-Interspike-Intervals/blob/178789c74fef72b9c25bd31d65ac598c987e1de9/README.md',
        'inference_performed':False,'assets':[]}
    for filename,url,expected in assets:
        path=P/filename; started=time.time()
        if not path.exists():
            temp=path.with_name(path.name+'.partial')
            with urllib.request.urlopen(url,timeout=90) as response,temp.open('wb') as f:
                metadata={k:response.headers.get(k) for k in ['Content-Type','Content-Length','Content-Disposition','Last-Modified']}
                while True:
                    b=response.read(1<<20)
                    if not b:break
                    f.write(b)
            assert temp.stat().st_size==expected,(filename,temp.stat().st_size)
            temp.rename(path)
        else:metadata={}
        assert path.stat().st_size==expected
        evidence['assets'].append({'filename':filename,'url':url,'bytes':expected,
            'sha256':sha(path),'download_elapsed_s':time.time()-started,'http_headers':metadata})
        (P/'bntt_acquisition.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps(evidence['assets'][-1]),flush=True)
    with zipfile.ZipFile(P/'tiny-imagenet-200.zip') as z:
        names=z.namelist()
        valnames=[n for n in names if n.startswith('tiny-imagenet-200/val/images/') and n.endswith('.JPEG')]
        annotation=z.read('tiny-imagenet-200/val/val_annotations.txt').decode()
        classes=z.read('tiny-imagenet-200/wnids.txt').decode().splitlines()
        rows=[line.split('\t') for line in annotation.splitlines()]
        assert len(classes)==200 and len(set(classes))==200 and len(rows)==len(valnames)==10000
        assert set(r[0] for r in rows)=={n.rsplit('/',1)[-1] for n in valnames}
        assert all(r[1] in classes for r in rows)
        evidence['validation_inventory']={'images':len(valnames),'classes':len(classes),
            'annotation_sha256':hashlib.sha256(annotation.encode()).hexdigest(),
            'wnids_sha256':hashlib.sha256('\n'.join(classes).encode()).hexdigest(),
            'heldout_split':'All10000 val_annotations entries; never train or unlabeled test',
            'storage':'Compressed archive read directly; no full dataset extraction'}
    evidence['source_files_sha256']={p.name:sha(p) for p in sorted((P/'bntt_visual_source').iterdir()) if p.is_file()}
    (P/'bntt_acquisition.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence['validation_inventory']),flush=True)

if __name__=='__main__':main()
