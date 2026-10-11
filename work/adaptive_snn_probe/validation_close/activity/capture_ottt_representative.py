"""Explicitly invoked original64-image OTTT actual operand capture; no retuning."""
from pathlib import Path
import argparse,hashlib,json,sys,time
sys.dont_write_bytecode=True
import numpy as np
import torch
P=Path(__file__).resolve().parent
BENCH=P.parent/'benchmarks';sys.path.insert(0,str(BENCH))
from run_ottt_v3 import model,inference
from ottt_integer_v3 import StreamIntegerLIF
from ottt_integer_v2 import pair_starts
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def hist():return dict(U=np.zeros(65536,np.float64),U_coarse=np.zeros(1024,np.float64),previous_spike=np.zeros(2,np.float64),beta=np.zeros(257,np.float64))
def add(h,v,pr,w=1.0):
    h['U']+=w*np.bincount(v+32768,minlength=65536)
    h['U_coarse']+=w*np.bincount((v+32768)//64,minlength=1024)
    h['previous_spike']+=w*np.bincount(pr,minlength=2)
    h['beta'][128]+=w*len(v)
def tv(a,b):return float(.5*np.abs(a/a.sum()-b/b.sum()).sum())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',default='ottt_random_stratified_a0');args=ap.parse_args()
    assert all(c.isalnum()or c in'_- 'for c in args.name)and' 'not in args.name
    out=P/args.name;out.mkdir(exist_ok=False)
    reference_file=BENCH/'cifar10_T6_n64_a2/logits.npz';prior_file=BENCH/'cifar10_T6_n64_a2/results.json'
    prior=json.loads(prior_file.read_text());assert prior['packed_vs_integer_logits_equal']and prior['state_mismatches']==prior['spike_mismatches']==0
    assert prior['samples']==64 and prior['batch']==4 and prior['threads']==2
    Nfull=prior['operation_counts']['nonzero'];target=262144
    datapath=BENCH.parents[1]/'public_model_trial/full_test10000.npz';checkpoint=BENCH/'cifar10_ottta.pth'
    files=[Path(__file__),BENCH/'run_ottt_v3.py',BENCH/'ottt_integer_v3.py',BENCH/'ottt_integer_v2.py',BENCH/'ottt_contract.md',reference_file,prior_file,checkpoint,datapath]
    files+=sorted((BENCH/'ottt_source/models').glob('*.py'))+sorted((BENCH/'ottt_source/modules').glob('*.py'))
    pins={str(p):sha(p)for p in files}
    plan=dict(status='declared_before_inference',model='official OTTT online spiking VGG11 ws CIFAR10',samples=64,batch=4,threads=2,T=6,interop_threads=1,
        neuron='vanilla LIF tau2, beta128, noinputdecay, immediate subtractive reset, spike>=256',
        unit=256,full_membrane_interface_signed_bits=16,internal_pair_signed_bits=9,
        current='unchanged nearest-even sourceFP32input times256',range='Failifold,current,nextstate leavefixedsigned16; norequantization/clipping',
        selection='Eight equal-length nonzero-indexstrata perframe. Fixedseed417839 SHA256/layer/time/batchpositions; onecontiguous random windowwithin eachstratum. No measuredhardwareoutput influencesselection.',
        length='L=max(1,nearest-even-round(262144*Nframe/(Nfull*8)));min(8,Nframe)windows; capLtofloor(Nframe/K) forshortframes',
        Nfull_predeclared=Nfull,target_scalar_operands=target,common_zero_filter='oldU==0bypass grantedallcontrols',
        weights='Nframe/(K*L)percapturedoperand; preserve originalorder inside eachwindow; no acrosswindowpairs',
        distribution_gates=dict(weighted_beta_TV_at_most=.05,weighted_previous_spike_TV_at_most=.05,weighted_U_coarse_TV_at_most=.05,
             absolute_narrow9_fraction_difference_at_most=.01,layer_time_TV_at_most=.005,adaptive_fixed_issue_gap_difference_at_most=.01),
        exactness='Everyrawleak/state/spikeindependentdivisioncheck; all64logits bitidenticaltoacceptedintegerreference; fullarithmeticcounts matchaccepted64prior',
        exclusions='Bounded deterministic64image arithmeticenergy sample; notstatisticalconfidence/full10kcoverage/board/fullneuronenergy. E6shift isstrong requiredtau2negativecontrol.',source_sha256=pins)
    save(out/'plan.json',plan)
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(2022)
    source_frames=[];windows=[];frames=[];layers={};fullhist=hist();samplehist=hist();whist=hist();totals=dict(raw=0,zero=0,nonzero=0,narrow=0,signed16_exceptions=0)
    target_counts=[0]*7;started=time.monotonic();batch_start=0
    class CaptureLIF(StreamIntegerLIF):
        def forward(self,x,**kwargs):
            init=kwargs.get('init',False)
            old=torch.zeros_like(x,dtype=torch.int64)if init else self.integer_u
            previous=np.zeros(old.numel(),np.int64)if init else self.spike.reshape(-1).numpy().astype(np.int64)
            flat=old.reshape(-1).numpy();Nraw=len(flat)
            expected_leak=-np.floor_divide(-flat,2)
            current=np.rint(x.numpy()*256).astype(np.int64).reshape(-1)
            charge=expected_leak+current;expected_spike=charge>=256;expected_state=charge-expected_spike.astype(np.int64)*256
            assert np.all((-32768<=flat)&(flat<=32767))and np.all((-32768<=current)&(current<=32767))and np.all((-32768<=expected_state)&(expected_state<=32767)),self.layer_name
            timestep=0 if init else self.step_index
            answer=super().forward(x,**kwargs)
            assert np.array_equal(expected_state,self.integer_u.reshape(-1).numpy())
            assert np.array_equal(expected_spike,self.spike.reshape(-1).numpy().astype(bool))
            sourcehash=hashlib.sha256()
            for a in(flat,previous):sourcehash.update(a.astype('<i8',copy=False).tobytes())
            nz=np.flatnonzero(flat!=0);v=flat[nz];pr=previous[nz];N=len(v)
            narrow=(-256<=v)&(v<=255);starts=pair_starts(narrow[:-1]&narrow[1:]);fixedpairs=np.arange(0,N-1,2)
            for k,val in dict(raw=Nraw,zero=Nraw-N,nonzero=N,narrow=int(narrow.sum())).items():totals[k]+=val
            key=f'{self.layer_name}:{timestep}';layer=layers.setdefault(key,dict(layer=self.layer_name,timestep=timestep,raw=0,nonzero=0,narrow=0,sample_operations=0,adaptive_issues=0,fixed2_issues=0))
            for k,val in dict(raw=Nraw,nonzero=N,narrow=int(narrow.sum()),adaptive_issues=N-len(starts),fixed2_issues=(N+1)//2).items():layer[k]+=val
            source=dict(layer=self.layer_name,timestep=timestep,batch_first_image=batch_start,shape=list(old.shape),raw=Nraw,nonzero=N,raw_source_sha256=sourcehash.hexdigest())
            source_frames.append(source)
            if N==0:return answer
            add(fullhist,v,pr)
            K=min(8,N);L=min(max(1,int(np.rint(target*N/(Nfull*8)))),N//K);weight=N/(K*L)
            seed_text=f'417839/{self.layer_name}/{timestep}/{batch_start}'.encode();rng=np.random.default_rng(int.from_bytes(hashlib.sha256(seed_text).digest()[:8],'little'))
            for j in range(K):
                left=j*N//K;right=(j+1)*N//K;left=int(rng.integers(left,right-L+1));right=left+L
                sv=v[left:right].copy();sp=pr[left:right].copy();idx=nz[left:right].copy();sn=(-256<=sv)&(sv<=255)
                pairs=pair_starts(sn[:-1]&sn[1:]);counts=[L-len(pairs),(L+1)//2,(L+1)//2,(L+1)//2,L,L-len(pairs),(L+1)//2]
                target_counts[:]=[a+b for a,b in zip(target_counts,counts)]
                meta=dict(index=len(frames),layer=self.layer_name,timestep=timestep,batch_first_image=batch_start,stratum=j,window_length=L,
                    nonzero_left=left,nonzero_right=right,source_nonzero=N,operation_expansion_weight=weight,narrow=int(sn.sum()),expected_requests_by_engine=counts,
                    adaptive_full_pairs_wholly_inside=int(np.searchsorted(starts,right-1)-np.searchsorted(starts,left)),
                    adaptive_full_pairs_crossing=int(np.any(starts==left-1))+int(np.any(starts==right-1)),
                    adaptive_restarted_pairs=len(pairs),fixed_full_pairs_wholly_inside=int(np.searchsorted(fixedpairs,right-1)-np.searchsorted(fixedpairs,left)),
                    fixed_full_pairs_crossing=int(np.any(fixedpairs==left-1))+int(np.any(fixedpairs==right-1)),fixed_restarted_pairs=L//2)
                windows.append(meta);frames.append((sv,sp,idx));layer['sample_operations']+=L
                add(samplehist,sv,sp);add(whist,sv,sp,weight)
            return answer
    net=model(CaptureLIF).eval();state=torch.load(checkpoint,map_location='cpu',weights_only=True);net.load_state_dict(state['net'],strict=True)
    nodes=[(name,n)for name,n in net.named_modules()if isinstance(n,CaptureLIF)]
    for name,node in nodes:node.layer_name=name;node.capture=False
    data=np.load(datapath);labels=data['labels'][:64];mean=torch.tensor([.4914,.4822,.4465])[None,:,None,None];std=torch.tensor([.2023,.1994,.2010])[None,:,None,None];logits=[]
    with torch.inference_mode():
        for batch_start in range(0,64,4):
            images=data['images'][batch_start:batch_start+4].copy();x=torch.from_numpy(images).permute(0,3,1,2).float()/255;x=(x-mean)/std
            logits.append(inference(net,x).numpy().copy())
            save(out/'progress.json',dict(samples=batch_start+4,seconds=time.monotonic()-started));print('OTTT REPRESENTATIVE',batch_start+4,'/64',round(time.monotonic()-started,2),flush=True)
    values=np.concatenate(logits);ref=np.load(reference_file);assert np.array_equal(values,ref['integer'])and np.array_equal(values,ref['packed'])
    for key in('raw','zero','nonzero','narrow'):assert totals[key]==prior['operation_counts'][key],key
    collected={}
    for _,node in nodes:
        for k,val in node.stats.items():collected[k]=collected.get(k,0)+val
    for key in prior['operation_counts']:assert collected[key]==prior['operation_counts'][key],key
    sampleN=sum(len(f[0])for f in frames);assert 150000<=sampleN<=300000
    stream=out/'representative_actual_frames.txt';stim=out/'representative_stim.txt';end=0
    with stream.open('w',newline='\n')as ff,stim.open('w',newline='\n')as sf:
        ff.write(str(len(frames))+'\n');sf.write(str(sampleN)+'\n')
        for v,pr,idx in frames:
            ff.write(str(len(v))+'\n');end+=len(v)
            for u in v:ff.write(f'{int(u)} 128\n');sf.write(f'{int(u)} 128 {end}\n')
    arr=np.concatenate([f[0]for f in frames]);rawidx=np.concatenate([f[2]for f in frames]);sp=np.concatenate([f[1]for f in frames])
    np.savez_compressed(out/'activity_operands.npz',U=arr,beta=np.full(sampleN,128,np.int64),expected_leak=-np.floor_divide(-arr,2),previous_spike=sp,raw_index=rawidx,window_lengths=np.array([len(f[0])for f in frames]),operation_expansion_weight=np.array([w['operation_expansion_weight']for w in windows]),logits=values,labels=labels)
    np.savez_compressed(out/'activity_histograms.npz',**{group+'_'+key:val for group,h in [('full',fullhist),('sample',samplehist),('weighted',whist)]for key,val in h.items()})
    comparisons={key:dict(unweighted_TV=tv(fullhist[key],samplehist[key]),weighted_TV=tv(fullhist[key],whist[key]))for key in fullhist}
    layerfull=np.array([r['nonzero']for r in layers.values()]);layersample=np.array([r['sample_operations']for r in layers.values()]);layerTV=tv(layerfull,layersample)
    full_narrow=totals['narrow']/totals['nonzero'];sample_narrow=int(((-256<=arr)&(arr<=255)).sum())/sampleN
    full_gap=prior['operation_counts']['issues_adaptive']/prior['operation_counts']['issues_fixed_split']-1;samplegap=target_counts[5]/target_counts[1]-1
    observed=dict(weighted_beta_TV_at_most=comparisons['beta']['weighted_TV'],weighted_previous_spike_TV_at_most=comparisons['previous_spike']['weighted_TV'],
                  weighted_U_coarse_TV_at_most=comparisons['U_coarse']['weighted_TV'],absolute_narrow9_fraction_difference_at_most=abs(full_narrow-sample_narrow),layer_time_TV_at_most=layerTV,
                  adaptive_fixed_issue_gap_difference_at_most=abs(full_gap-samplegap))
    gates={key:dict(observed=val,limit=plan['distribution_gates'][key],pass_gate=val<=plan['distribution_gates'][key])for key,val in observed.items()}
    passed=all(v['pass_gate']for v in gates.values())
    for file,pin in pins.items():assert sha(file)==pin
    result=dict(status='pass_exact_feedback_and_distribution_gates'if passed else'pass_exact_feedback_failed_distribution_gates',samples=64,all64_logits_equal_integer_reference=True,
        full_counts_equal_prior=True,source_sha256=pins,raw_feedback_updates=totals['raw'],totals=totals,
        counts_by_layer={name:node.stats.copy() for name,node in nodes},rows=list(layers.values()),source_frames=source_frames,
        sample_operations=sampleN,sample_windows=len(frames),sample_issues_by_engine=target_counts,windows=windows,
        distribution_comparisons=comparisons,distribution_gates=gates,full_narrow9_fraction=full_narrow,sample_narrow9_fraction=sample_narrow,
        full_adaptive_fixed_issue_gap=full_gap,sample_adaptive_fixed_issue_gap=samplegap,elapsed_seconds=time.monotonic()-started,
        artifact_sha256={str(p):sha(p)for p in[out/'plan.json',stream,stim,out/'activity_operands.npz',out/'activity_histograms.npz']},
        scope='Captured arithmetic aftercommonzerofilter, original64vanillaLIFinputs; tau2 shiftcontrol mandatory. Noenergyresultuntilstrictnative/SDF/physicalSAIF.')
    save(out/'results.json',result);print(json.dumps({k:result[k]for k in('status','sample_operations','sample_windows','sample_issues_by_engine','distribution_gates','elapsed_seconds')},indent=2),flush=True)
if __name__=='__main__':main()
