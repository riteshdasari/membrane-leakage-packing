"""Gate representative OTTT64 operands, then explicitly launch isolated fixed16 tests."""
from pathlib import Path
import argparse,importlib.util,json,math,re,subprocess,sys,time
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;W=P.parent;ROOT=P.parent.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b
sha,read,write,pins,verify=b.sha,b.read,b.write,b.pins,b.verify
COHORT='actual_ottt_representative';WORKLOAD='ottt_representative'
GATES=dict(weighted_beta_TV_at_most=.05,weighted_previous_spike_TV_at_most=.05,weighted_U_coarse_TV_at_most=.05,
           absolute_narrow9_fraction_difference_at_most=.01,layer_time_TV_at_most=.005,adaptive_fixed_issue_gap_difference_at_most=.01)

def accept(path):
    d=read(path);assert d['status']=='pass';verify(d.get('source_sha256',{}));verify(d.get('artifact_sha256',{}));return d
def tv(a,c):return float(.5*np.abs(a/a.sum()-c/c.sum()).sum())
def counts(U,lengths):
    answer=[0]*7;pos=0
    for length in lengths:
        end=pos+int(length);N=int(length);i=pos;requests=0
        while i<end:
            pair=i+1<end and -256<=U[i]<=255 and -256<=U[i+1]<=255
            i+=2 if pair else 1;requests+=1
        answer=[a+c for a,c in zip(answer,[requests,(N+1)//2,(N+1)//2,(N+1)//2,N,requests,(N+1)//2])];pos=end
    assert pos==len(U);return answer
def verify_capture(resultfile):
    resultfile=Path(resultfile).resolve();r=read(resultfile)
    assert r['status']=='pass_exact_feedback_and_distribution_gates','No representative energy from failed distribution capture.'
    assert r['samples']==64 and r['all64_logits_equal_integer_reference']and r['full_counts_equal_prior']
    verify(r['source_sha256']);verify(r['artifact_sha256'])
    directory=resultfile.parent;plan=read(directory/'plan.json');verify(plan['source_sha256'])
    assert(plan['samples'],plan['batch'],plan['threads'],plan['T'],plan['unit'],plan['full_membrane_interface_signed_bits'],plan['internal_pair_signed_bits'])==(64,4,2,6,256,16,9)
    assert plan['distribution_gates']==GATES and set(r['distribution_gates'])==set(GATES)
    assert all(d['pass_gate']and d['limit']==GATES[k]and d['observed']<=d['limit']for k,d in r['distribution_gates'].items())
    known=read(P/'preparation_rep3.json');verify(known['source_sha256']);verify(known['artifact_sha256'])
    capturesource=str((W.parent/'activity/capture_ottt_representative.py').resolve())
    assert r['source_sha256'][capturesource]==known['source_sha256'][capturesource]==sha(capturesource)
    bench=W.parent/'benchmarks';referencefile=bench/'cifar10_T6_n64_a2/logits.npz';priorfile=bench/'cifar10_T6_n64_a2/results.json'
    assert r['source_sha256'][str(referencefile)]==sha(referencefile)and r['source_sha256'][str(priorfile)]==sha(priorfile)
    prior=read(priorfile);assert prior['packed_vs_integer_logits_equal']and prior['state_mismatches']==prior['spike_mismatches']==0
    assert r['raw_feedback_updates']==prior['operation_counts']['raw']and r['totals']['nonzero']==prior['operation_counts']['nonzero']
    npz=directory/'activity_operands.npz';histfile=directory/'activity_histograms.npz'
    assert r['artifact_sha256'][str(npz)]==sha(npz)and r['artifact_sha256'][str(histfile)]==sha(histfile)
    with np.load(npz)as d:
        arrays={k:d[k].copy()for k in d.files}
    U=arrays['U'];beta=arrays['beta'];expected=arrays['expected_leak'];lengths=arrays['window_lengths'];previous=arrays['previous_spike'];indices=arrays['raw_index'];weights=arrays['operation_expansion_weight']
    N=len(U);assert N==r['sample_operations'] and 150000<=N<=300000 and len(lengths)==r['sample_windows']==len(r['windows'])
    assert U.ndim==1 and all(x.shape==U.shape for x in(beta,expected,previous,indices))
    assert np.issubdtype(U.dtype,np.integer)and np.all((-32768<=U)&(U<=32767))and np.all(U!=0)
    assert np.all(beta==128)and np.all((previous==0)|(previous==1))
    assert np.array_equal(expected,-np.floor_divide(-U.astype(np.int64),2))
    assert np.all(lengths>0)and int(lengths.sum())==N and weights.shape==lengths.shape
    with np.load(referencefile)as ref:
        assert np.array_equal(arrays['logits'],ref['integer'])and np.array_equal(arrays['logits'],ref['packed'])
    pos=0;seen={};sourceframes={(f['layer'],f['timestep'],f['batch_first_image']):f for f in r['source_frames']}
    for i,(length,meta)in enumerate(zip(lengths,r['windows'])):
        length=int(length);key=(meta['layer'],meta['timestep'],meta['batch_first_image']);source=sourceframes[key]
        assert meta['index']==i and meta['window_length']==length and meta['source_nonzero']==source['nonzero']
        K=min(8,source['nonzero']);j=meta['stratum'];assert 0<=j<K
        assert j not in seen.setdefault(key,set());seen[key].add(j)
        left=meta['nonzero_left'];right=meta['nonzero_right'];assert right-left==length
        assert j*source['nonzero']//K<=left<right<=(j+1)*source['nonzero']//K
        assert weights[i]==meta['operation_expansion_weight']==source['nonzero']/(K*length)
        raw=indices[pos:pos+length];assert np.all((0<=raw)&(raw<source['raw']))and np.all(raw[1:]>raw[:-1])
        assert meta['expected_requests_by_engine']==counts(U[pos:pos+length],[length]);pos+=length
    assert all(len(js)==min(8,sourceframes[key]['nonzero'])for key,js in seen.items())
    assert set(seen)=={key for key,f in sourceframes.items()if f['nonzero']>0}
    # Independently bind both streaming text formats to every NPZ row and boundary.
    ff=directory/'representative_actual_frames.txt';sf=directory/'representative_stim.txt'
    with ff.open()as stream:
        assert int(stream.readline())==len(lengths);pos=0
        for length in lengths:
            assert int(stream.readline())==length
            for i in range(pos,pos+int(length)):
                row=stream.readline().split();assert len(row)==2 and tuple(map(int,row))==(int(U[i]),128)
            pos+=int(length)
        assert stream.read().strip()==''
    ends=np.repeat(np.cumsum(lengths),lengths)
    with sf.open()as stream:
        assert int(stream.readline())==N
        for i in range(N):
            row=stream.readline().split();assert len(row)==3 and tuple(map(int,row))==(int(U[i]),128,int(ends[i]))
        assert stream.read().strip()==''
    expected_counts=counts(U,lengths);assert expected_counts==r['sample_issues_by_engine']
    # Rebuild captured/weighted distributions; full distributions were collected on every raw model frame.
    expanded=np.repeat(weights,lengths);sample=dict(U=np.bincount(U+32768,minlength=65536),U_coarse=np.bincount((U+32768)//64,minlength=1024),previous_spike=np.bincount(previous,minlength=2),beta=np.bincount(beta,minlength=257))
    weighted=dict(U=np.bincount(U+32768,weights=expanded,minlength=65536),U_coarse=np.bincount((U+32768)//64,weights=expanded,minlength=1024),previous_spike=np.bincount(previous,weights=expanded,minlength=2),beta=np.bincount(beta,weights=expanded,minlength=257))
    with np.load(histfile)as h:
        for key in sample:
            assert np.array_equal(h['sample_'+key],sample[key])
            assert np.allclose(h['weighted_'+key],weighted[key],rtol=5e-10,atol=1e-7)
            assert abs(h['full_'+key].sum()-prior['operation_counts']['nonzero'])<.001
        observed=dict(weighted_beta_TV_at_most=tv(h['full_beta'],weighted['beta']),weighted_previous_spike_TV_at_most=tv(h['full_previous_spike'],weighted['previous_spike']),weighted_U_coarse_TV_at_most=tv(h['full_U_coarse'],weighted['U_coarse']))
    rows=r['rows'];full_layer=np.array([x['nonzero']for x in rows]);sample_layer=np.array([x['sample_operations']for x in rows])
    for row in rows:
        key=(row['layer'],row['timestep'])
        assert row['nonzero']==sum(f['nonzero']for f in r['source_frames']if(f['layer'],f['timestep'])==key)
        assert row['sample_operations']==sum(w['window_length']for w in r['windows']if(w['layer'],w['timestep'])==key)
    assert int(sample_layer.sum())==N and int(full_layer.sum())==prior['operation_counts']['nonzero']
    full_narrow=prior['operation_counts']['narrow']/prior['operation_counts']['nonzero'];sample_narrow=np.count_nonzero((-256<=U)&(U<=255))/N
    fullgap=prior['operation_counts']['issues_adaptive']/prior['operation_counts']['issues_fixed_split']-1
    observed|=dict(absolute_narrow9_fraction_difference_at_most=abs(full_narrow-sample_narrow),layer_time_TV_at_most=tv(full_layer,sample_layer),adaptive_fixed_issue_gap_difference_at_most=abs(fullgap-(expected_counts[5]/expected_counts[1]-1)))
    for key,value in observed.items():
        assert value<=GATES[key]and math.isclose(value,r['distribution_gates'][key]['observed'],rel_tol=1e-9,abs_tol=1e-10)
    return r,arrays,expected_counts,dict(status='pass',samples=64,operations=N,windows=len(lengths),all_logits_equal_accepted_integer=True,NPZ_stream_frames_identical=True,independent_exact_leak_mismatches=0,expected_requests_by_engine=expected_counts,recomputed_distribution_gates=observed)

def prepare(resultfile,routefile):
    resultfile=Path(resultfile).resolve();routefile=Path(routefile).resolve()
    r,arrays,counts_,check=verify_capture(resultfile);routes=accept(routefile)
    assert routes['B']==16 and routes['period_ns']==12 and set(routes['selected_routes'])==set(map(str,range(7)))
    selected={}
    for e in(5,1,6):
        file=Path(routes['selected_routes'][str(e)]).resolve()/'hardware.json';hw=accept(file)
        assert hw['B']==16 and hw['engine']==e and hw['clock_period_ns']==12 and hw['top']==f'top_sequential_leak16_e{e}'
        a=hw['slice_accounting'];assert(a['launch_FF'],a['capture_FF'],a['fixture_FF'])==(55,39,94)
        assert hw['part']=='xc7a100tcsg324-1'and hw['core']['DSP']==hw['full_fixture']['DSP']==(0 if e==6 else 1)
        assert all(math.isfinite(hw[k])and hw[k]>=0 for k in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))
        for name in('leak_core16.sv','leak_dsp.sv','timing16.sv'):assert hw['source_sha256'][str(W/name)]==sha(P/name)==sha(W/name)
        selected[str(e)]=dict(directory=str(file.parent),hardware_file=str(file),hardware_sha256=sha(file))
    receipt=P/'cohort_acceptance.json';domainfile=P/'domain_acceptance_ottt_representative.json'
    if receipt.exists():
        old=accept(receipt);assert old['capture_results_file']==str(resultfile)and old['capture_results_sha256']==sha(resultfile)
        assert old['resolved_route_acceptance_file']==str(routefile)and old['resolved_route_acceptance_sha256']==sha(routefile)
        assert old['selected_routes']==selected and domainfile.exists();return old
    assert not domainfile.exists()
    stim=P/'actual_ottt_representative_stim.txt';output=P/'actual_ottt_representative_expected.npz'
    assert not stim.exists()and not output.exists();stim.write_bytes((resultfile.parent/'representative_stim.txt').read_bytes())
    np.savez_compressed(output,U=arrays['U'],beta=arrays['beta'],expected_leak=arrays['expected_leak'],frame_lengths=arrays['window_lengths'])
    originals=read(W/'domain_acceptance_glif_v2.json');verify(originals['source_sha256'])
    sources=r['source_sha256']|r['artifact_sha256']|pins([Path(__file__),resultfile,routefile,W/'domain_acceptance_glif_v2.json',b.VIVADO/'data/verilog/src/glbl.v'])
    co=dict(stimulus_file=str(stim),expected_outputs_file=str(output),operations=len(arrays['U']),groups=len(arrays['window_lengths']),expected_requests_by_engine=counts_,expected_unstalled_min_max_latency=2,artifact_sha256=pins([stim,output]))
    domain=dict(status='pass_independent_representative_capture_preparation',arithmetic_mismatches=0,signed16_scalar_cases=originals['signed16_scalar_cases'],signed16_fixed_split_cases=originals['signed16_fixed_split_cases'],shift128_cases=originals['shift128_cases'],cohorts={COHORT:co},source_sha256=sources,
                scope='Original64 OTTTtau2/unit256, same fixed16 full interface and source-identical mainroutes; separate representative cohort after common zero filter. No RTL/energy acceptance at preparation.')
    write(domainfile,domain)
    record=check|dict(capture_results_file=str(resultfile),capture_results_sha256=sha(resultfile),resolved_route_acceptance_file=str(routefile),resolved_route_acceptance_sha256=sha(routefile),selected_routes=selected,source_sha256=sources,artifact_sha256=pins([stim,output,domainfile]))
    write(receipt,record);return record

def launch(receipt,attempt):
    verify(receipt['source_sha256']);verify(receipt['artifact_sha256']);progress=P/f'closure_{attempt}.json';assert not progress.exists()
    stamps=pins([Path(__file__),P/'cohort_acceptance.json',P/'domain_acceptance_ottt_representative.json',W/'representative_certified_runner_source_checks.json',W/'certify_energy_export.py',P/'run_native16_rep3.py',W/'run_energy_recovery_representative_child.py',P/'audit_power16_rep3_12_certified.py'])
    native_name=f'native_actual_ottt_rep_s0_{attempt}';nativefile=P/'hardware'/native_name/'acceptance.json'
    state=dict(status='running',B=16,clock_ns=12,fixture_FF=94,cohort=COHORT,steps=[],failures=[],accepted_energy={},source_sha256=stamps)
    def job(label,script,argv):
        log=P/f'{label}_{attempt}.log';assert not log.exists();write(progress,state);start=time.time();verify(stamps)
        with log.open('w',encoding='utf-8')as stream:rc=subprocess.run([sys.executable,'-B',str(script),*argv],cwd=P,stdout=stream,stderr=subprocess.STDOUT).returncode
        verify(stamps);step=dict(label=label,returncode=rc,seconds=time.time()-start,log_file=str(log),log_sha256=sha(log));state['steps'].append(step);return step
    native_step=job('native',P/'run_native16_rep3.py',['--cohort',COHORT,'--stall','0','--capture','1','--attempt',native_name])
    try:
        assert native_step['returncode']==0;n=accept(nativefile);assert n['cohort']==COHORT and n['capture']==1 and n['stall']==0
        assert[(r['native_index'],r['engine'])for r in n['rows']]==[(0,5),(1,1),(2,6)]
        assert[r['requests']for r in n['rows']]==[receipt['expected_requests_by_engine'][e]for e in(5,1,6)]
        native_step['status']='accepted';native_step['acceptance_file']=str(nativefile);native_step['acceptance_sha256']=sha(nativefile)
    except Exception as exc:
        native_step['status']='retained_failure';native_step['reason']=repr(exc);state['failures'].append(native_step);state['status']='failed_native_no_energy';write(progress,state);return
    spec=importlib.util.spec_from_file_location('representative_OTTT_power_auditor',P/'audit_power16_rep3_12_certified.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    for e in(5,1,6):
        selected=receipt['selected_routes'][str(e)];directory=Path(selected['directory']);template=str(directory.parent/re.sub(rf'e{e}(?=_)','e{engine}',directory.name))
        assert Path(template.format(engine=e))==directory;tag=f'{attempt}_e{e}'
        step=job(f'energy_e{e}',W/'run_energy_recovery_representative_child.py',['--workload',WORKLOAD,'--native-acceptance',str(nativefile),'--route-dir-template',template,'--engine',str(e),'--attempt',tag,'--run'])
        try:
            assert step['returncode']==0;child=accept(P/f'energy_recovery_{WORKLOAD}_e{e}_{tag}_progress.json');assert not child['failures']and child['engines']==[e]
            file=P/'hardware'/f'power12_{WORKLOAD}_e{e}_{tag}'/'power_audit.json';saved=accept(file);assert audit.annotation(file.parent)==saved
            assert Path(saved['routed_hardware_file']).resolve()==Path(selected['hardware_file']).resolve()and saved['routed_hardware_sha256']==selected['hardware_sha256']
            interval=saved['native_interval_audit'];assert interval['scalar_updates']==receipt['operations']and interval['requests']==receipt['expected_requests_by_engine'][e]
            assert saved['clock_period_ns']==12 and saved['fixture_FF']==94 and saved['physical_activity_unknown_records']==0
            step|=dict(status='accepted',power_audit_file=str(file),power_audit_sha256=sha(file))
            state['accepted_energy'][str(e)]=dict(power_audit_file=str(file),power_audit_sha256=sha(file),routed_hardware_file=selected['hardware_file'],routed_hardware_sha256=selected['hardware_sha256'],dynamic_power_W=saved['dynamic_power_W'],ROI_duration_ps=interval['duration_ps'],scalar_updates=interval['scalar_updates'],requests=interval['requests'],estimated_dynamic_energy_pJ_per_scalar_update=saved['estimated_dynamic_energy_pJ_per_scalar_update'])
        except Exception as exc:step|=dict(status='retained_failure',reason=repr(exc),accepted_energy=False);state['failures'].append(step)
        write(progress,state)
    state['status']='pass_representative_OTTT_selected_energy'if not state['failures']else'completed_with_retained_failures'
    state['scope']='Representative64 vanillaLIF arithmetic capture after commonzero filtering, source-identical selected fixed16 routes, E5/E1/E6 estimated full94FFfixture dynamicenergy. Original stresscontrols remain separate; notboard/fullneuronenergy.'
    state['artifact_sha256']=pins([P/'cohort_acceptance.json',nativefile,*[Path(s['log_file'])for s in state['steps']],*[Path(v['power_audit_file'])for v in state['accepted_energy'].values()]])
    write(progress,state);print(json.dumps(dict(status=state['status'],accepted_engines=list(state['accepted_energy']),failures=state['failures'])),flush=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--capture-results',required=True);ap.add_argument('--route-acceptance',required=True);ap.add_argument('--attempt',required=True)
    modes=ap.add_mutually_exclusive_group(required=True);modes.add_argument('--prepare-only',action='store_true');modes.add_argument('--launch',action='store_true');args=ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt);receipt=prepare(args.capture_results,args.route_acceptance)
    print(json.dumps(dict(status='prepared_exact_representative_cohort',operations=receipt['operations'],expected_requests=receipt['expected_requests_by_engine'],mode='launch'if args.launch else'prepare_only')),flush=True)
    if args.launch:launch(receipt,args.attempt)
if __name__=='__main__':main()
