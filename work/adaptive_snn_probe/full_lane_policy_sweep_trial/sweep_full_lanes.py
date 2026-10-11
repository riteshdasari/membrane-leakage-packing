"""Software-only full-U13 / actual-U8 prefix frontier on saved exact streams."""
from pathlib import Path
import hashlib
import json

P=Path(__file__).resolve().parent
ROOT=P.parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pins(paths):return {str(Path(p).resolve()):sha(p)for p in paths}
def verify(mapping):
    for name,h in mapping.items():assert sha(name)==h,('Changed evidence',name)

def take_for(k,pairs,pos):
    av=min(8,len(pairs)-pos);n=min(k,av)
    while n<av and -128<=pairs[pos+n][0]<=127:n+=1
    return n

def new_stats():
    return dict(groups=0,scalar_updates=0,requests=0,take_histogram={str(k):0 for k in range(1,9)},
                worst_case_all_tail_wide_requests=0,fixed8_requests=0,fixed6_requests=0)

def add_group(stat,n,length,k):
    stat['requests']+=n;stat['groups']+=1;stat['scalar_updates']+=length
    stat['worst_case_all_tail_wide_requests']+=(length+k-1)//k
    stat['fixed8_requests']+=(length+7)//8;stat['fixed6_requests']+=(length+5)//6

def finish(stat):
    # One-edge issue pipeline plus one drain per independently scheduled group.
    stat['one_edge_analytic_service_clocks']=stat['requests']+stat['groups']
    stat['one_edge_worst_case_all_tail_wide_service_clocks']=stat['worst_case_all_tail_wide_requests']+stat['groups']
    stat['one_edge_fixed8_service_clocks']=stat['fixed8_requests']+stat['groups']
    stat['one_edge_fixed6_service_clocks']=stat['fixed6_requests']+stat['groups']
    stat['request_change_percent_vs_fixed8']=100*(stat['requests']/stat['fixed8_requests']-1)
    stat['service_change_percent_vs_fixed8']=100*(stat['one_edge_analytic_service_clocks']/stat['one_edge_fixed8_service_clocks']-1)
    stat['service_change_percent_vs_fixed6']=100*(stat['one_edge_analytic_service_clocks']/stat['one_edge_fixed6_service_clocks']-1)
    assert stat['fixed8_requests']<=stat['requests']<=stat['worst_case_all_tail_wide_requests']

def physical_check(selected,k):
    # Eight unsigned six-bit radix32 fields in the same48-bit DSP layout.
    a=sum((u%32)<<(6*j)for j,(u,i)in enumerate(selected))
    b=sum((i%32)<<(6*j)for j,(u,i)in enumerate(selected))
    p=a+b;assert p<1<<48
    for lane,(u,i)in enumerate(selected):
        field=(p>>(6*lane))&63
        assert field==(u%32)+(i%32)
        base=u//32+i//32;high=base+(field>>5)
        assert -256<=base<=255 and -256<=high<=255
        if lane>=k:assert -8<=base<=6 and -8<=high<=7
        assert high*32+(field&31)==u+i

def study(name,ledger_path,source_meta,source_mapping):
    ledger=json.loads(ledger_path.read_text());assert len(ledger['ledger'])==9216
    metadata={m['seed']:m for m in ledger['metadata']};assert sorted(metadata)==[0,1,2]
    previous=None;groups=[];ranges={};scalar=0
    for rec in ledger['ledger']:
        key=tuple(rec[x]for x in ('seed','t','layer','image'))
        assert previous is None or previous<key;previous=key
        assert not rec['hard_reset'] and len(rec['postleak_U'])==len(rec['current'])==rec['neurons']
        assert rec['leak_shift']==(None if name=='original_IF' else int(name[-1]))
        pairs=list(zip(rec['postleak_U'],rec['current']))
        assert len(pairs)==(128 if rec['layer']==0 else 10)
        assert all(-4096<=u<=4095 and -128<=i<=127 for u,i in pairs)
        sums=[u+i for u,i in pairs];fire=[int(s>=rec['threshold'])for s in sums]
        assert fire==rec['expected_spikes']
        assert [s-f*rec['threshold']for s,f in zip(sums,fire)]==rec['expected_state']
        r=ranges.setdefault(str(rec['seed']),dict(U_min=0,U_max=0,I_min=0,I_max=0))
        r['U_min']=min(r['U_min'],min(u for u,i in pairs));r['U_max']=max(r['U_max'],max(u for u,i in pairs))
        r['I_min']=min(r['I_min'],min(i for u,i in pairs));r['I_max']=max(r['I_max'],max(i for u,i in pairs))
        groups.append((rec,pairs));scalar+=len(pairs)
    assert scalar==635904
    policies=[]
    for k in range(1,9):
        total=new_stats();by_seed={str(s):new_stats()for s in metadata}
        by_layer={str(l):new_stats()for l in (0,1)}
        by_seed_layer={f'{s}:{l}':new_stats()for s in metadata for l in (0,1)}
        for rec,pairs in groups:
            pos=requests=0;hist={str(n):0 for n in range(1,9)}
            while pos<len(pairs):
                n=take_for(k,pairs,pos);assert 1<=n<=min(8,len(pairs)-pos)
                selected=pairs[pos:pos+n];physical_check(selected,k)
                pos+=n;requests+=1;hist[str(n)]+=1
            stats=[total,by_seed[str(rec['seed'])],by_layer[str(rec['layer'])],by_seed_layer[f'{rec["seed"]}:{rec["layer"]}']]
            for stat in stats:
                add_group(stat,requests,len(pairs),k)
                for n,count in hist.items():stat['take_histogram'][n]+=count
        for stat in [total,*by_seed.values(),*by_layer.values(),*by_seed_layer.values()]:finish(stat)
        policies.append(dict(k_full_lanes=k,narrow_tails=8-k,total=total,by_seed=by_seed,by_layer=by_layer,by_seed_layer=by_seed_layer,
            predicted_one_bank_DSP_fabric_metadata_bits=37+5*k,
            predicted_one_bank_direct_adaptive_LUT_result_metadata_bits=77+5*k,
            predicted_DSP_low_part_PREG_bits=48,
            bit_count_scope='Analytic one-edge storage only:8 high fields(4bit narrow/9bit U13 full)+4count+1valid versus8 result fields(9bit narrow/14bit full)+4count+1valid. No synthesis mapping, detector LUT, clockenable, DSP resource, route, power, leakage/reset, memory or controller area prediction.'))
        print('SWEEP',name,'K',k,'REQUESTS',total['requests'],'SERVICE1',total['one_edge_analytic_service_clocks'],
              'WORST',total['one_edge_worst_case_all_tail_wide_service_clocks'],'DSPFABRICBITS',37+5*k,'LUTBITS',77+5*k,flush=True)
    return dict(name=name,groups=9216,scalar_updates=scalar,sampled_images_per_seed=48,timesteps=32,
        ranges_sampled=ranges,metadata=list(metadata.values()),policies=policies,
        input_source_sha256=source_mapping,source_metadata=str(source_meta),ledger_sha256=sha(ledger_path))

def main():
    output=P/'sweep_results.json';assert not output.exists()
    study_root=ROOT/'trained_reference_admission_study'
    restored=json.loads((study_root/'restored_reference_summary.json').read_text());assert restored['status']=='pass'
    verify(json.loads((study_root/'manifest.json').read_text())['files']);verify(restored['source_sha256'])
    if_root=ROOT/'residue_frontier_u13_trial/original_if'
    if_profile=json.loads((if_root/'profile.json').read_text());assert if_profile['status']=='pass'
    verify(json.loads((if_root/'manifest.json').read_text())['files']);verify(if_profile['source_sha256'])
    assert sha(if_root/'reference_ledger.json')==if_profile['ledger_sha256']
    assert sha(if_root/'stream_stim.txt')==if_profile['stream_sha256']
    cohorts=[]
    for shift in (1,3):
        paths=[study_root/'restored_reference_summary.json',study_root/'manifest.json',
               study_root/f'leak_shift{shift}/reference_ledger.json',study_root/f'leak_shift{shift}/stream_stim.txt']
        cohorts.append(study(f'original_shift{shift}',paths[2],paths[0],pins(paths)))
    paths=[if_root/'profile.json',if_root/'manifest.json',if_root/'reference_ledger.json',if_root/'stream_stim.txt']
    cohorts.append(study('original_IF',paths[2],paths[0],pins(paths)))
    native_checks=[]
    # Same real k5 policy/stream checked against one-edge IF DSP and direct LUT RTL.
    for folder in ('natural_frontier_trial','adaptive_natural_lut_trial'):
        file=ROOT/folder/'native_models_0_a0/native_checks.json';data=json.loads(file.read_text())
        assert data['status']=='pass' and data['kind']=='models' and not data['backpressure']
        verify(data['source_sha256']);verify(data['candidate_file_sha256'])
        row,=[r for r in data['rows']if r['engine']==5]
        k5=cohorts[-1]['policies'][4]['total']
        assert row['requests']==k5['requests'] and row['take_histogram']==k5['take_histogram']
        assert row['service_clocks']==k5['one_edge_analytic_service_clocks']
        native_checks.append(dict(cohort='original_IF',file=str(file),file_sha256=sha(file),engine=5,
            requests=row['requests'],service_clocks=row['service_clocks'],k5_native_policy_matches=True))
    # Original LIF cores remain four-edge; verify policy counts without conflating latency.
    for shift in (1,3):
        file=ROOT/f'trained_reference_native_trial/results/native_shift{shift}_stall0_a1/native_checks.json'
        data=json.loads(file.read_text());assert data['status']=='pass' and data['shift']==shift and not data['backpressure']
        verify(data['source_sha256']);verify(data['candidate_file_sha256'])
        for e,k in ((11,5),(5,6),(2,8)):
            row,=[r for r in data['rows']if r['engine']==e]
            stat=cohorts[shift//2]['policies'][k-1]['total']
            assert row['requests']==stat['requests'] and row['take_histogram']==stat['take_histogram']
            assert row['service_clocks']==stat['requests']+4*stat['groups']
            native_checks.append(dict(cohort=f'original_shift{shift}',file=str(file),file_sha256=sha(file),engine=e,k=k,
                requests=row['requests'],actual_four_edge_service_clocks=row['service_clocks'],native_policy_matches=True))
    result=dict(status='pass',cohorts=cohorts,native_policy_crosschecks=native_checks,
        source_sha256=pins([Path(__file__)]),
        exact_layout='Same eight six-bit radix32 residue fields. Firstk positions handle fullU13; following positions require actualU8 and are consumed only as a contiguous prefix. Unadmitted operands return in full positions on next request. No sorting/reordering/coefficient/output changes.',
        worst_case='All narrow tail positions wide: pergroupceil(N/k)requests; with one-edge groupdrain,add1clockpergroup. Alltailnarrow:ceil(N/8). Bound is attained by legal U13 wide values in every position, independent of currents. Hardware backpressure and operand delivery can add unbounded waiting outside this service bound.',
        latency_scope='One-edge analytic counts price the already-tested natural core style. Four-edge original LIF native counts are separately verified; no new kvariant RTL/route/power job is run.',
        generality_scope='Unchanged three seeded64-128-10converted networks, held-outdigits, originalIF or shift1/shift3 LIF coefficients; first48orderedhardwaregroups fromfull360RNGtrajectory. Leakage configurations are not independent architectures. Existing proofs distinguish finite32stepIF from indefiniteleakybounds.')
    output.write_text(json.dumps(result,indent=2)+'\n')
    (P/'manifest.json').write_text(json.dumps(dict(status='pass',files=pins([Path(__file__),output])),indent=2)+'\n')

if __name__=='__main__':main()
