"""Independent file-level scalar, admission, provenance and histogram audit."""
from pathlib import Path
import hashlib,json
import numpy as np
HERE=Path(__file__).resolve().parent/'random_stratified_v2'
TRIAL=HERE.parent.parent.parent/'sequential_paper_trial'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(path):
    lines=iter(path.read_text().splitlines());n=int(next(lines));groups=[]
    for _ in range(n):
        count=int(next(lines));groups.append(np.array([tuple(map(int,next(lines).split()))for j in range(count)],dtype=np.int64))
    assert next(lines,None)is None
    return groups
def main():
    result=json.loads((HERE/'results.json').read_text());assert result['status']=='pass'
    for group in('source_sha256','artifact_sha256'):
        for path,want in result[group].items():assert sha(Path(path))==want,(group,path)
    groups=parse(HERE/'representative_actual_frames.txt');flat=np.concatenate(groups)
    a=np.load(HERE/'activity_operands.npz');assert len(flat)==result['sample_operations']
    assert np.array_equal(flat[:,0],a['U'])and np.array_equal(flat[:,1],a['beta'])
    assert np.array_equal(np.array([len(g)for g in groups]),a['window_lengths'])
    assert np.array_equal(a['logits'],np.load(TRIAL/'stage2_logits.npz')['logits'][:64])
    expected=np.array([(int(u)*int(b)+255)//256 for u,b in flat],dtype=np.int64)
    assert np.array_equal(expected,a['expected_leak'])
    assert all(int(u)!=0 and int(b)!=0 and -2048<=int(u)<=2047 and 0<=int(b)<=256 for u,b in flat)
    counts=[0]*6;offset=0;post_mismatch=0
    for group,window in zip(groups,result['windows']):
        u=group[:,0];b=group[:,1];nr=len(group)
        assert np.array_equal(np.diff(a['raw_index'][offset:offset+nr])>0,np.ones(max(nr-1,0),dtype=bool))
        local=[]
        for engine in range(6):
            cursor=0;issues=0
            while cursor<nr:
                paired=cursor+1<nr
                if engine==4:paired=False
                elif engine==1:paired=paired and b[cursor]==b[cursor+1]
                elif engine in(0,5):
                    paired=paired and b[cursor]==b[cursor+1]and -256<=u[cursor]<=255 and -256<=u[cursor+1]<=255
                    if engine==0:paired=paired and b[cursor]>=64
                size=2 if paired else 1
                if engine==5:
                    if paired:
                        v=int(u[cursor]);w=int(u[cursor+1]);beta=int(b[cursor])
                        product=((v+256)+(w<<16))*beta+255-256*beta+(255<<16)
                        spill=((product>>16)&1)^((beta&1)&(w&1))^1
                        low=((product>>8)&255)-256*spill
                        high=(product>>24)&511
                        if high>=256:high-=512
                        high+=spill and ((product>>16)&255)==255
                        post_mismatch+=int(low!=expected[offset+cursor])+int(high!=expected[offset+cursor+1])
                    else:post_mismatch+=int((int(u[cursor])*int(b[cursor])+255)//256!=expected[offset+cursor])
                cursor+=size;issues+=1
            local.append(issues);counts[engine]+=issues
        assert local==window['issues'];offset+=nr
    assert counts==result['sample_issues_by_engine']and post_mismatch==0
    stim=(HERE/'representative_stim.txt').read_text().splitlines();assert int(stim[0])==len(flat)
    pos=end=0
    for group in groups:
        end+=len(group)
        for u,b in group:
            assert tuple(map(int,stim[pos+1].split()))==(int(u),int(b),end);pos+=1
    hist=np.load(HERE/'activity_histograms.npz');weights=np.repeat(a['operation_expansion_weight'],a['window_lengths'])
    for key,values,minlength in [('U',a['U']+2048,4096),('beta',a['beta'],257),('previous_spike',a['previous_spike'],2),('U_coarse',(a['U']+2048)//64,64)]:
        assert np.array_equal(hist['sample_'+key],np.bincount(values,minlength=minlength))
        assert np.allclose(hist['weighted_'+key],np.bincount(values,weights=weights,minlength=minlength),atol=1e-6,rtol=1e-12)
    old=parse(TRIAL/'stage3_actual_frames.txt');of=np.concatenate(old)
    old_context=(of[:,1]<128).astype(np.int64)
    old_metrics={}
    for key,v,size in [('U',of[:,0]+2048,4096),('beta',of[:,1],257),('previous_spike',old_context,2),('U_coarse',(of[:,0]+2048)//64,64)]:
        oldhist=np.bincount(v,minlength=size);full=hist['full_'+key]
        old_metrics[key]=float(.5*np.abs(oldhist/oldhist.sum()-full/full.sum()).sum())
    answer=dict(status='pass',scalar_outputs=len(flat),windows=len(groups),all6_independent_counts=counts,
        exact_post_packing_sample_mismatches=post_mismatch,all_files_sourcepins_verified=True,
        stimulus_and_npz_order_identical=True,all64_logits_equal_reference=True,
        previous_first64_operand_capture_operations=len(of),previous_capture_distribution_total_variation=old_metrics,
        current_capture_distribution_total_variation=result['distribution_comparisons'],
        result_sha256=sha(HERE/'results.json'),verifier_sha256=sha(Path(__file__)))
    (HERE/'acceptance.json').write_text(json.dumps(answer,indent=2)+'\n')
    print(json.dumps(answer,indent=2),flush=True)
if __name__=='__main__':main()
