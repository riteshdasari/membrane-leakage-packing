"""Restore saved converted-integer SNN dynamics; no training or tool jobs."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode=True
import numpy as np

P=Path(__file__).resolve().parent
ORIGINAL=P.parent
R=ORIGINAL/'results'
sys.path.insert(0,str(ORIGINAL))
import probe


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def take_for(name,pairs,pos):
    av=min(8,len(pairs)-pos)
    if name=='fixed6':return min(av,6)
    if name=='fixed8':return av
    full=5 if name=='F5' else 6
    count=min(av,full)
    while count<av and -128<=pairs[pos+count][0]<=127:count+=1
    return count


def packed(pairs,name):
    a=sum((u%32)<<(6*lane) for lane,(u,current) in enumerate(pairs))
    b=sum((current%32)<<(6*lane) for lane,(u,current) in enumerate(pairs))
    physical=a+b;assert physical<1<<48
    answers=[]
    for lane,(u,current) in enumerate(pairs):
        field=(physical>>(6*lane))&63
        assert field==(u%32)+(current%32)
        high=u//32+current//32+(field>>5)
        assert -64<=high<=63
        if name.startswith('F') and lane>=int(name[1:]):assert -8<=high<=7
        answers.append(32*high+(field&31))
    assert answers==[u+current for u,current in pairs]
    return answers


def stats():return dict(requests=0,groups=0,scalar_updates=0,take_histogram={str(k):0 for k in range(1,9)},by_layer={})


def schedule(stat,pairs,name,layer,domain):
    pos=0;count=0
    while pos<len(pairs):
        n=take_for(name,pairs,pos)
        if domain and name!='fixed6':packed(pairs[pos:pos+n],name)
        count+=1;stat['take_histogram'][str(n)]+=1;pos+=n
    stat['requests']+=count;stat['groups']+=1;stat['scalar_updates']+=len(pairs)
    part=stat['by_layer'].setdefault(str(layer),dict(requests=0,groups=0,scalar_updates=0))
    part['requests']+=count;part['groups']+=1;part['scalar_updates']+=len(pairs)


def main():
    out=P/'restored_reference_summary.json'
    assert not out.exists(),'Preserve restored-reference evidence'
    configs=json.loads((R/'final_selected.json').read_text())['models']
    prior=json.loads((R/'exact_inference.json').read_text())['models']
    bundles={}
    for shift in (1,3):
        folder=P/f'leak_shift{shift}'
        assert not folder.exists();folder.mkdir()
        file=folder/'stream_stim.txt';handle=file.open('w',newline='\n');handle.write('9216\n')
        bundles[shift]=dict(folder=folder,handle=handle,ledger=[],metadata=[],groups=0,scalar_updates=0)
    profiles=[]
    for cfg in configs:
        seed,shift=cfg['seed'],cfg['leak_shift']
        data=np.load(R/f'model_seed{seed}.npz')
        weights=[data['w0'].astype(np.int64),data['w1'].astype(np.int64)]
        x,y=data['test_x'],data['test_y'];assert x.shape==(360,64) and y.shape==(360,)
        assert [w.shape for w in weights]==[(64,128),(128,10)]
        certificate=[dict(layer=li,current_lower=np.minimum(w,0).sum(0).tolist(),
                          current_upper=np.maximum(w,0).sum(0).tolist()) for li,w in enumerate(weights)]
        assert all(min(rec['current_lower'])>=-128 and max(rec['current_upper'])<=127 for rec in certificate)
        predictions,records=probe.reference(weights,cfg['thresholds'],x,shift)
        accuracy=float(np.mean(predictions==y))
        assert accuracy==cfg['reference_accuracy']
        old_reference,=[r for r in prior if r['seed']==seed and r['leak_shift']==shift and not r['hard_reset'] and r['mode']==0]
        assert accuracy==old_reference['reference_accuracy']
        pre_min=min(int(rec[1].min()) for rec in records);pre_max=max(int(rec[1].max()) for rec in records)
        domain=(-1024<=pre_min and pre_max<=1023)
        sample_min=min(int(rec[1][:48].min()) for rec in records);sample_max=max(int(rec[1][:48].max()) for rec in records)
        state=[np.zeros((len(x),w.shape[1]),np.int64) for w in weights]
        counts=np.zeros((len(x),10),np.int64);reference_counts=np.zeros_like(counts)
        rng=np.random.default_rng(123)
        statistics={name:stats() for name in ('fixed6','fixed8','F5','F6')}
        ranges=[dict(layer=li,preleak_min=0,preleak_max=0,postleak_min=0,postleak_max=0,
                     current_min=0,current_max=0,sum_min=0,sum_max=0,postreset_min=0,postreset_max=0,
                     U11_violations=0,I8_violations=0) for li in range(2)]
        disagreements=dict(state=0,spikes=0,predictions=0,counts=0)
        for t in range(32):
            sp=rng.random(x.shape)<x
            for li,w in enumerate(weights):
                rec=records[2*t+li];assert rec[0]==li and np.array_equal(sp,rec[2])
                old=state[li];pre=old.copy()
                if shift is not None:pre-=pre>>shift
                current=sp.astype(np.int64)@w
                # Independent residue reconstruction applied to every full360-image value.
                residue=pre%32+current%32
                sums=32*(pre//32+current//32+residue//32)+residue%32
                assert np.array_equal(pre,rec[1]) and np.array_equal(sums,rec[3])
                fired=sums>=cfg['thresholds'][li]
                next_state=sums-fired*cfg['thresholds'][li]
                reference_state=rec[3]-rec[4]*cfg['thresholds'][li]
                disagreements['state']+=int(np.count_nonzero(next_state!=reference_state))
                disagreements['spikes']+=int(np.count_nonzero(fired!=rec[4]))
                row=ranges[li]
                for name,array in (('preleak',old),('postleak',pre),('current',current),('sum',sums),('postreset',next_state)):
                    row[name+'_min']=min(row[name+'_min'],int(array.min()))
                    row[name+'_max']=max(row[name+'_max'],int(array.max()))
                row['U11_violations']+=int(np.count_nonzero((pre<-1024)|(pre>1023)))
                row['I8_violations']+=int(np.count_nonzero((current<-128)|(current>127)))
                state[li]=next_state
                for image in range(48):
                    pairs=[(int(u),int(i)) for u,i in zip(pre[image],current[image])]
                    for name,stat in statistics.items():schedule(stat,pairs,name,li,domain)
                    if domain and shift in bundles:
                        bundle=bundles[shift];stream=bundle['handle']
                        stream.write(f'{len(pairs)} 0\n')
                        for u,current_value in pairs:
                            assert -1024<=u<=1023 and -128<=current_value<=127
                            stream.write(f'{u&2047:03x} {current_value&2047:03x}\n')
                        bundle['ledger'].append(dict(seed=seed,t=t,layer=li,image=image,neurons=len(pairs),
                            threshold=cfg['thresholds'][li],leak_shift=shift,hard_reset=False,
                            postleak_U=[u for u,i in pairs],current=[i for u,i in pairs],
                            expected_state=next_state[image].tolist(),expected_spikes=fired[image].astype(int).tolist()))
                        bundle['groups']+=1;bundle['scalar_updates']+=len(pairs)
                sp=fired
                if li==1:reference_counts+=rec[4]
            counts+=sp
        disagreements['counts']=int(np.count_nonzero(counts!=reference_counts))
        disagreements['predictions']=int(np.count_nonzero(counts.argmax(1)!=predictions))
        assert not any(disagreements.values())
        for stat in statistics.values():
            stat['service_clocks_no_output_stalls_with_group_drains']=stat['requests']+4*stat['groups']
            for part in stat['by_layer'].values():part['service_clocks_no_output_stalls_with_group_drains']=part['requests']+4*part['groups']
        for name in ('F5','F6'):
            statistics[name]['service_change_percent_vs_fixed8']=100*(statistics[name]['service_clocks_no_output_stalls_with_group_drains']/statistics['fixed8']['service_clocks_no_output_stalls_with_group_drains']-1)
        if domain and shift in bundles:
            bundles[shift]['metadata'].append(dict(seed=seed,leak_shift=shift,hard_reset=False,
                sampled_images=48,all_images=360,all_images_reference_accuracy=accuracy,
                sampled_reference_accuracy=float(np.mean(predictions[:48]==y[:48])),labels=y[:48].tolist(),
                expected_counts=counts[:48].tolist(),thresholds=cfg['thresholds']))
        profiles.append(dict(seed=seed,leak_shift=shift,thresholds=cfg['thresholds'],hard_reset=False,
            all360_original_reference_accuracy=accuracy,first48_reference_accuracy=float(np.mean(predictions[:48]==y[:48])),
            full360_postleak_U_range=[pre_min,pre_max],first48_postleak_U_range=[sample_min,sample_max],
            U11_I8_domain_supported=domain,domain_violation_counts=sum(r['U11_violations'] for r in ranges),
            static_postleak_U8_certificate=(shift==1),layer_ranges=ranges,weight_current_certificate=certificate,
            exact_software_reference_disagreements=disagreements,scheduled_first48=statistics,
            unsupported_scope=None if domain else 'IF postleak U exceeds signed11; do not encode, clip or claim current RTL support. Schedule counts are hypothetical only.'))
        print('RESTORED',seed,shift,accuracy,'DOMAIN',domain,'U',pre_min,pre_max,
              'F5/F6/F8CLOCKS',*[statistics[k]['service_clocks_no_output_stalls_with_group_drains'] for k in ('F5','F6','fixed8')],flush=True)
        del records
    for shift,bundle in bundles.items():
        bundle['handle'].close()
        assert bundle['groups']==9216 and bundle['scalar_updates']==635904
        folder=bundle['folder']
        (folder/'reference_ledger.json').write_text(json.dumps(dict(metadata=bundle['metadata'],ledger=bundle['ledger']),separators=(',',':'))+'\n')
        bundle.pop('handle');bundle.pop('ledger')
    inputs=[Path(__file__),ORIGINAL/'probe.py',ORIGINAL/'base.py',ORIGINAL/'final_selected.py',
            ORIGINAL/'prepare_adaptive_delta_model.py',R/'final_selected.json',R/'exact_inference.json',
            *(R/f'model_seed{seed}.npz' for seed in range(3))]
    result=dict(status='pass',profiles=profiles,source_sha256={str(path.resolve()):sha(path) for path in inputs},
        prepared_streams={str(shift):dict(directory=str(bundle['folder']),groups=bundle['groups'],scalar_updates=bundle['scalar_updates'],
            stream_sha256=sha(bundle['folder']/'stream_stim.txt'),ledger_sha256=sha(bundle['folder']/'reference_ledger.json')) for shift,bundle in bundles.items()},
        trained_semantics='Stored int4 weights come from trained64-128-10ReLU ANN then quantization and calibrated integer rate-coded SNN conversion. Restored final_selected shift1/3/IF dynamics, subtractive reset,32steps,rng123 over the complete360-imagebatch. No direct SNN training or retraining is claimed.',
        shift1_static_bound='For each neuron current in[L,H] from all binary-spike subsets, state stays in[2L,2H] under ceil(state/2)+current and positive-threshold subtractive reset; therefore postleakU lies[L,H], which is certified signed8. A statically narrow8-lane implementation is a valid stronger comparator for shift1.',
        verification_scope='Plain probe.reference vs independent residue reconstruction of full360 state/spike/count/class trajectories, plus physical48bit packed addition of unchangedfirst48 ordered requests for full-domain-supported configs. Software only; no new RTL replay or energy claim.',
        generality_scope='Same three seeded64-128-10converted models and held-outdigits; leakage settings are configurations, not independent trained architectures. IF range failure retained without clipping. Current primitive has no leakage-coefficient dependency.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    artifacts={str(path.resolve()):sha(path) for path in P.rglob('*') if path.is_file()}
    (P/'manifest.json').write_text(json.dumps(dict(status='pass',files=artifacts),indent=2)+'\n')


if __name__=='__main__':main()
