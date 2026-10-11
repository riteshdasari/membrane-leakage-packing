"""Prepare pinned original-leakage groups for unchanged original and F5 cores."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
STUDY=P.parent/'trained_reference_admission_study'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pins(paths):return {str(Path(p).resolve()):sha(p) for p in paths}
def verify(hashes):
    for path,h in hashes.items():assert sha(path)==h,('Changed source',path)
def signed(x,w):return x-(1<<w) if x&(1<<(w-1)) else x
def load_groups(path):
    groups=[]
    with Path(path).open() as stream:
        total=int(stream.readline())
        for g in range(total):
            n,gap=map(int,stream.readline().split());assert 1<=n<=4096 and gap>=0
            pairs=[]
            for k in range(n):
                u,i=[int(x,16)for x in stream.readline().split()]
                assert 0<=u<2048 and 0<=i<2048
                u,i=signed(u,11),signed(i,11);assert -128<=i<=127
                pairs.append((u,i))
            groups.append((gap,pairs))
        assert not stream.read().strip()
    return groups

def take_for(e,pairs,pos):
    av=min(8,len(pairs)-pos)
    if e in (0,6):return min(av,6)
    if e not in (5,11):return av
    full=5 if e==11 else 6
    n=min(av,full)
    while n<av and -128<=pairs[pos+n][0]<=127:n+=1
    return n

def main():
    a=argparse.ArgumentParser();a.add_argument('--shift',type=int,choices=(1,3),required=True)
    a.add_argument('--directory',type=Path,required=True);args=a.parse_args()
    src=STUDY/f'leak_shift{args.shift}';wd=args.directory.resolve()
    assert wd.is_dir() and not (wd/'stream_stim.txt').exists()
    summary=json.loads((STUDY/'restored_reference_summary.json').read_text())
    manifest=json.loads((STUDY/'manifest.json').read_text());assert summary['status']==manifest['status']=='pass'
    verify(manifest['files']);verify(summary['source_sha256'])
    groups=load_groups(src/'stream_stim.txt');ledger=json.loads((src/'reference_ledger.json').read_text())
    assert len(groups)==len(ledger['ledger'])==9216 and sum(len(v)for _,v in groups)==635904
    previous=None
    for (gap,pairs),rec in zip(groups,ledger['ledger']):
        assert gap==0 and rec['leak_shift']==args.shift and not rec['hard_reset']
        assert len(pairs)==rec['neurons']==(128 if rec['layer']==0 else 10)
        assert pairs==list(zip(rec['postleak_U'],rec['current']))
        assert all(-1024<=u<=1023 and -128<=i<=127 for u,i in pairs)
        if args.shift==1:assert all(-128<=u<=127 for u,i in pairs)
        key=tuple(rec[k]for k in ('seed','t','layer','image'))
        assert previous is None or previous<key;previous=key
        sums=[u+i for u,i in pairs];fire=[int(s>=rec['threshold'])for s in sums]
        assert fire==rec['expected_spikes'] and [s-f*rec['threshold']for s,f in zip(sums,fire)]==rec['expected_state']
    for name in ('stream_stim.txt','reference_ledger.json'):(wd/name).write_bytes((src/name).read_bytes())
    predictions=[]
    for e in range(13 if args.shift==1 else 12):
        requests=0;hist={str(k):0 for k in range(1,9)}
        for gap,pairs in groups:
            pos=0
            while pos<len(pairs):
                n=take_for(e,pairs,pos);assert n>=1
                pos+=n;requests+=1;hist[str(n)]+=1
        predictions.append(dict(engine=e,requests=requests,take_histogram=hist))
    sources=pins([Path(__file__),P/'CONTRACT.md',STUDY/'restored_reference_summary.json',STUDY/'manifest.json',
                  src/'stream_stim.txt',src/'reference_ledger.json'])|summary['source_sha256']
    value=dict(status='pass',kind='restored_models',shift=args.shift,groups=len(groups),neurons=635904,
        engines=len(predictions),stimulus_sha256=sha(wd/'stream_stim.txt'),ledger_sha256=sha(wd/'reference_ledger.json'),
        source_sha256=sources,predicted_issues=predictions,
        scope='Original saved shift leakage/subtractive reset, same weights/fullbatch events; first48 groups per seed; no beta231 replacement.')
    (wd/'workload.json').write_text(json.dumps(value,indent=2)+'\n')
    print('RESTORED WORK PASS SHIFT',args.shift,'ENGINES',len(predictions),flush=True)

if __name__=='__main__':main()
