"""Predeclared stratified actual-operand capture, without model/coefficient selection."""
from pathlib import Path
import hashlib, json, sys, time
sys.dont_write_bytecode = True
import numpy as np
import torch

HERE = Path(__file__).resolve().parent / 'random_stratified_v2'
TRIAL = HERE.parent.parent.parent / 'sequential_paper_trial'
sys.path.insert(0, str(TRIAL))
from integer_glif import PUBLIC, load_model, normalized
from integer_glif_packed import install
from packed_executor import packed, starts_for

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, obj):
    (HERE/name).write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8')

def take(engine, u, b, i):
    if i+1 == len(u) or engine == 4: return 1
    if engine in (2,3): return 2
    if engine == 1: return 2 if b[i] == b[i+1] else 1
    return 2 if (b[i] == b[i+1] and -256 <= u[i] <= 255
                 and -256 <= u[i+1] <= 255 and (engine == 5 or b[i] >= 64)) else 1

def sequential_issues(u, b):
    counts=[]
    for engine in range(6):
        i=n=0
        while i<len(u): i += take(engine,u,b,i); n += 1
        counts.append(n)
    return counts

def new_hist():
    return dict(U=np.zeros(4096,dtype=np.float64), beta=np.zeros(257,dtype=np.float64),
                previous_spike=np.zeros(2,dtype=np.float64), U_coarse=np.zeros(64,dtype=np.float64))

def add_hist(hist,v,b,previous,weight=1.0):
    hist['U'] += weight*np.bincount(v+2048,minlength=4096)
    hist['beta'] += weight*np.bincount(b,minlength=257)
    hist['previous_spike'] += weight*np.bincount(previous,minlength=2)
    hist['U_coarse'] += weight*np.bincount((v+2048)//64,minlength=64)

def main():
    HERE.mkdir(parents=True,exist_ok=True)
    assert not (HERE/'plan.json').exists(), 'Do not overwrite a declared experiment.'
    prior=json.loads((TRIAL/'stage3_results.json').read_text())
    assert prior['status']=='pass_exact_packed_feedback_and_stream_screen'
    target=262144; total_arithmetic=prior['total']['arithmetic_operations']
    required=[Path(__file__),TRIAL/'integer_glif.py',TRIAL/'integer_glif_packed.py',
              TRIAL/'packed_executor.py',TRIAL/'stage2_logits.npz',TRIAL/'stage3_results.json',
              PUBLIC/'original_test64.npz',PUBLIC/'assets/glif_cifar10_T2.pth.tar']
    required += sorted((PUBLIC/'sources').glob('*.py'))
    sourcepins={str(p):digest(p) for p in required}
    plan=dict(status='declared_before_inference',samples=64,indices='original order 0..63',batch=4,
              threads=3,interop_threads=1,model='pinned official GLIF ResNet18 CIFAR10 T2 channelwise checkpoint',
              integer_contract='unchanged UNIT256, beta Q8, ceil(beta*U/256), original integer reference',
              capture='eight contiguous windows per nonzero batch/layer/time frame, each uniformly positioned within its equal-length nonzero-index stratum by a fixed deterministic PCG64 seed from SHA256 of seed417839/layer/time/batch; no measured outcome enters placement',
              length='L=max(1, nearest-even-round(262144*N_frame/(79246135*8))); same length in all eight windows of that frame',
              density_target_scalar_operations=target,prior_full_arithmetic_operations=total_arithmetic,
              filtering='same stable U==0 or beta==0 bypass granted every control; stream order unchanged within each window',
              coefficient_selection='none; trained coefficients/context from every source frame retained',
              boundaries='no pairing across windows; quantify changed phase and lost boundary pairs relative to full frame greedy assignment',
              weights='each sample operand weight N_frame/(8*L); exact layer/frame operation reweighting, deterministic sampling does not imply statistical unbiasedness',
              acceptance='all64 logits bit-identical to saved integer reference; all full totals equal frozen stage3; every raw source/coefficient/state independently checked; sample<=300000 and >=150000; scalar outputs and all6 policy counts independently generated',
              activity_scope='leakage arithmetic operands after common zero bypass. Zero-filter hardware, full neuron update, source memory bandwidth, board power, and whole10k representativeness excluded',
              source_sha256=sourcepins)
    plan['sampling_method_change_reason']='Fixed midpoint windows can systematically alias power-of-two feature planes and channelwise coefficients. Random positions were selected as the follow-up method before inspecting either outcome; both experiments retained, no best-result selection.'
    plan['retained_midpoint_capture_directory']=str(HERE.parent)
    plan['placement_seed']=417839
    save('plan.json',plan)
    torch.set_num_threads(3);torch.set_num_interop_threads(1)
    started=time.monotonic();rows={};frames=[];windows=[];source_frames=[]
    full_hist=new_hist();sample_hist=new_hist();weighted_hist=new_hist()
    total={k:0 for k in prior['total'] if k!='issues'};total['issues']={k:0 for k in prior['total']['issues']}
    sample_issues=[0]*6;sample_ops=0;sample_narrow=0;sample_same=0
    sample_raw_order_hash=hashlib.sha256();pending={};batch_start=0

    def execute(name,step,u,coefficient,reference):
        v=u.numpy().reshape(-1);b=coefficient.numpy().reshape(-1)
        result,counts=packed(v,b)
        assert np.array_equal(result,reference.numpy().reshape(-1))
        pending[name,step]=(v,b,counts,result)
        for key,val in counts.items():
            if key not in total: continue
            if key=='issues':
                for policy,n in val.items():total['issues'][policy]+=int(n)
            else:total[key]+=int(val)
        row=rows.setdefault(name+':'+str(step),dict(layer=name,time_step=step,frames=0,raw_operations=0,
            zero_bypassed=0,arithmetic_operations=0,narrow9_arithmetic_operations=0,same_coefficient_edges=0,
            adaptive_pairs=0,post_pairs=0,fixed_split_pairs=0,issues={p:0 for p in counts['issues']},sample_operations=0))
        row['frames']+=1
        for key,val in counts.items():
            if key=='issues':
                for policy,n in val.items():row['issues'][policy]+=int(n)
            else:row[key]+=int(val)
        return torch.from_numpy(result.reshape(u.shape))

    def observe(name,step,u,coefficient,current,leak,new,spikes,previous,p):
        nonlocal sample_ops,sample_narrow,sample_same
        v,b,counts,result=pending.pop((name,step))
        vv=u.numpy().reshape(-1);bb=coefficient.numpy().reshape(-1);pr=previous.numpy().reshape(-1)
        assert np.shares_memory(v,vv) and np.shares_memory(b,bb)
        independently_selected=torch.where(previous.bool(),p['k1'],p['k0']).numpy().reshape(-1)
        assert np.array_equal(b,independently_selected)
        expected=-np.floor_divide(-(v*b),256)
        assert np.array_equal(expected,result) and np.array_equal(expected,leak.numpy().reshape(-1))
        expected_new=expected.reshape(u.shape)+current.numpy()-p['bias'].numpy()-p['reset'].numpy()*previous.numpy()
        assert np.array_equal(expected_new,new.numpy())
        assert np.array_equal(expected_new>p['threshold'].numpy(),spikes.numpy().astype(bool))
        assert np.all((-2048<=v)&(v<=2047)) and np.all((b>=0)&(b<=256))
        h=hashlib.sha256()
        for arr in(v,b,pr):h.update(arr.astype('<i8',copy=False).tobytes())
        nz=np.flatnonzero((v!=0)&(b!=0));nv=v[nz];nb=b[nz];npv=pr[nz];N=len(nv)
        frame=dict(layer=name,time_step=step,batch_start=batch_start,raw_operations=len(v),
                   arithmetic_operations=N,raw_source_sha256=h.hexdigest(),sample_operations=0)
        source_frames.append(frame)
        if N==0:return
        add_hist(full_hist,nv,nb,npv)
        L=max(1,int(np.rint(target*N/(total_arithmetic*8))))
        assert 8*L<=N
        weight=N/(8*L);narrow=(-256<=nv)&(nv<=255);same=nb[:-1]==nb[1:]
        full_starts={0:starts_for(same&narrow[:-1]&narrow[1:]&(nb[:-1]>=64)),
                     1:starts_for(same),2:np.arange(0,N-1,2),3:np.arange(0,N-1,2),
                     4:np.empty(0,dtype=np.int64),5:starts_for(same&narrow[:-1]&narrow[1:])}
        seed_text=f'417839/{name}/{step}/{batch_start}'.encode('utf-8')
        rng=np.random.default_rng(int.from_bytes(hashlib.sha256(seed_text).digest()[:8],'little'))
        for j in range(8):
            bin_start=j*N//8;bin_end=(j+1)*N//8
            left=int(rng.integers(bin_start,bin_end-L+1));right=left+L
            assert 0<=left<right<=N
            sv=nv[left:right].copy();sb=nb[left:right].copy();sp=npv[left:right].copy();raw_indices=nz[left:right].copy()
            assert np.array_equal(sv,v[raw_indices]) and np.array_equal(sb,b[raw_indices])
            assert len(raw_indices)<2 or np.all(np.diff(raw_indices)>0)
            expected_out=-np.floor_divide(-(sv*sb),256)
            actual_out,helpercounts=packed(sv,sb);assert np.array_equal(actual_out,expected_out)
            issues=sequential_issues(sv,sb)
            helper_order=['adaptive_pre','fixed_split2','fixed_LUT2','fixed_scalar2','fixed_scalar1','adaptive_post']
            assert issues==[helpercounts['issues'][policy]for policy in helper_order]
            boundary=[]
            for engine in range(6):
                st=full_starts[engine]
                contained=int(np.searchsorted(st,right-1)-np.searchsorted(st,left))
                crossings=int(np.any(st==left-1))+int(np.any(st==right-1))
                restarted_pairs=L-issues[engine] if engine!=4 else 0
                boundary.append(dict(engine=engine,full_pairs_wholly_inside=contained,
                    full_pairs_crossing_boundary=crossings,restarted_window_pairs=restarted_pairs,
                    restarted_minus_contained_pairs=restarted_pairs-contained))
            win=dict(index=len(frames),layer=name,time_step=step,batch_start=batch_start,stratum=j,
                full_frame_arithmetic=N,nonzero_left=left,nonzero_right=right,length=L,
                raw_first_index=int(raw_indices[0]),raw_last_index=int(raw_indices[-1]),
                operation_expansion_weight=weight,issues=issues,boundary=boundary,
                narrow9_operations=int(((-256<=sv)&(sv<=255)).sum()),
                same_coefficient_edges=int((sb[:-1]==sb[1:]).sum()))
            windows.append(win);frames.append((sv,sb,sp,raw_indices,expected_out))
            sample_ops+=L;frame['sample_operations']+=L;rows[name+':'+str(step)]['sample_operations']+=L
            sample_narrow+=win['narrow9_operations'];sample_same+=win['same_coefficient_edges']
            sample_issues[:]=[a+c for a,c in zip(sample_issues,issues)]
            add_hist(sample_hist,sv,sb,sp);add_hist(weighted_hist,sv,sb,sp,weight)
            for arr in(sv,sb,sp,raw_indices):sample_raw_order_hash.update(arr.astype('<i8',copy=False).tobytes())

    data=np.load(PUBLIC/'original_test64.npz');reference=np.load(TRIAL/'stage2_logits.npz')
    model=load_model();states=install(model,observer=observe,audit_first_batch=True,leak_executor=execute);logits=[]
    with torch.inference_mode():
        for batch_start in range(0,64,4):
            logits.append(model(normalized(data['images'][batch_start:batch_start+4])).numpy().copy())
            print('STRATIFIED ACTIVITY',batch_start+4,'/64',round(time.monotonic()-started,1),'seconds',flush=True)
            save('progress.json',dict(samples=batch_start+4,seconds=time.monotonic()-started,sample_operations=sample_ops))
    actual_logits=np.concatenate(logits)
    assert np.array_equal(actual_logits,reference['logits'][:64])
    assert total==prior['total'],(total,prior['total'])
    assert all(r['independent_state_mismatches']==r['independent_spike_mismatches']==0 for r in states.values())
    assert not pending and 150000<=sample_ops<=300000
    for row in rows.values():
        prior_row,=[r for r in prior['rows']if r['layer']==row['layer'] and r['time_step']==row['time_step']]
        assert all(row[k]==prior_row[k] for k in prior_row)
    stream=HERE/'representative_actual_frames.txt';stim=HERE/'representative_stim.txt'
    with stream.open('w',encoding='utf-8',newline='\n')as ff,stim.open('w',encoding='utf-8',newline='\n')as sf:
        ff.write(str(len(frames))+'\n');sf.write(str(sample_ops)+'\n');end=0
        for sv,sb,sp,idx,exp in frames:
            ff.write(str(len(sv))+'\n');end+=len(sv)
            for u,b in zip(sv,sb):ff.write(f'{int(u)} {int(b)}\n');sf.write(f'{int(u)} {int(b)} {end}\n')
    def tv(a,b):return float(.5*np.abs(a/a.sum()-b/b.sum()).sum())
    comparisons={key:dict(unweighted_total_variation=tv(full_hist[key],sample_hist[key]),
                         weighted_total_variation=tv(full_hist[key],weighted_hist[key]))for key in full_hist}
    layerfull=np.array([r['arithmetic_operations']for r in rows.values()],dtype=float)
    layersample=np.array([r['sample_operations']for r in rows.values()],dtype=float)
    comparisons['layer_time_context']=dict(unweighted_total_variation=tv(layerfull,layersample),weighted_total_variation=0.0)
    histfile=HERE/'activity_histograms.npz'
    np.savez_compressed(histfile,**{group+'_'+key:val for group,hist in [('full',full_hist),('sample',sample_hist),('weighted',weighted_hist)]for key,val in hist.items()})
    flatfile=HERE/'activity_operands.npz'
    np.savez_compressed(flatfile,U=np.concatenate([f[0]for f in frames]),beta=np.concatenate([f[1]for f in frames]),
        previous_spike=np.concatenate([f[2]for f in frames]),raw_index=np.concatenate([f[3]for f in frames]),
        expected_leak=np.concatenate([f[4]for f in frames]),window_lengths=np.array([len(f[0])for f in frames]),
        operation_expansion_weight=np.array([w['operation_expansion_weight']for w in windows]),logits=actual_logits)
    boundary_totals=[]
    for engine in range(6):
        bs=[w['boundary'][engine]for w in windows]
        boundary_totals.append(dict(engine=engine,**{k:sum(b[k]for b in bs)for k in bs[0]if k!='engine'}))
    weighted_issues=[sum(w['operation_expansion_weight']*w['issues'][e]for w in windows)for e in range(6)]
    result=dict(status='pass',samples=64,all_logits_bit_identical_to_integer_reference=True,
        exact_neuron_feedback_updates=total['raw_operations'],state_spike_arithmetic_mismatches=0,
        complete64_stream_counts_match_frozen_stage3=True,full=total,sample_operations=sample_ops,
        sample_windows=len(frames),source_nonzero_frames=sum(f['arithmetic_operations']>0 for f in source_frames),
        sample_issues_by_engine=sample_issues,weighted_extrapolated_issues_by_engine=weighted_issues,
        sample_narrow9_fraction=sample_narrow/sample_ops,full_narrow9_fraction=total['narrow9_arithmetic_operations']/total['arithmetic_operations'],
        sample_same_coefficient_edges=sample_same,full_same_coefficient_edges=sum(r['same_coefficient_edges']for r in rows.values()),
        distribution_comparisons=comparisons,boundary_totals=boundary_totals,rows=list(rows.values()),
        source_frames=source_frames,windows=windows,elapsed_seconds=time.monotonic()-started,
        raw_sample_order_sha256=sample_raw_order_hash.hexdigest(),
        limitations=['Deterministic eight-window capture is bounded sampling, not an unbiased probabilistic estimate.',
            'Eight window boundaries per nonzero source frame change greedy pairing phase; counts and crossings are explicitly retained.',
            'Representative of first64 accepted model images, not of all10000 or another neuron model.',
            'Activity after common zero filtering excludes idle zero-update behavior and filter/memory hardware.'],
        source_sha256=sourcepins,artifact_sha256={str(p):digest(p)for p in[HERE/'plan.json',stream,stim,histfile,flatfile]})
    for path,expected in sourcepins.items():assert digest(Path(path))==expected
    save('results.json',result)
    print(json.dumps({k:result[k]for k in('status','sample_operations','sample_windows','sample_issues_by_engine','sample_narrow9_fraction','full_narrow9_fraction','distribution_comparisons','elapsed_seconds')}),flush=True)

if __name__=='__main__': main()
