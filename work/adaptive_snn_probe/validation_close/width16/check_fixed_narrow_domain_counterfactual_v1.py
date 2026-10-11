"""Unsafe arithmetic diagnostic only: forcibly reinterpret U's low9 bits."""
from pathlib import Path
import datetime,hashlib,json,sys
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;V=P.parent
out=P/'fixed_narrow_domain_counterfactual_v1.json'
assert not out.exists(),'Preserve prior diagnostic'
pins={};verified_pin_count=0;cache={}
def sha(path):
    path=Path(path).resolve();key=str(path)
    if key not in cache:
        h=hashlib.sha256()
        with path.open('rb')as f:
            for block in iter(lambda:f.read(1<<20),b''):h.update(block)
        cache[key]=h.hexdigest()
    return cache[key]
def pin(path):path=Path(path).resolve();pins[str(path)]=sha(path)
def read(path):return json.loads(Path(path).read_text())
def verify(record):
    global verified_pin_count
    for field in('source_sha256','artifact_sha256','source_artifact_sha256'):
        for path,expected in record.get(field,{}).items():
            assert sha(path)==expected,('Changed accepted evidence',path)
            pins[str(Path(path).resolve())]=expected;verified_pin_count+=1
pin(__file__)
inputs=[('GLIF',P/'domain_acceptance_glif_v2.json','actual_glif',V/'activity/random_stratified_v2/results.json','pass'),('OTTT',P/'ottt_representative/domain_acceptance_ottt_representative.json','actual_ottt_representative',V/'activity/ottt_random_stratified_a1/results.json','pass_exact_feedback_and_distribution_gates')]
results={}
for label,cohort_path,key,capture_path,capture_status in inputs:
    co_record=read(cohort_path);capture=read(capture_path)
    assert capture['status']==capture_status
    verify(co_record);verify(capture);pin(cohort_path);pin(capture_path)
    co=co_record['cohorts'][key];verify(co)
    source_path=Path(co['expected_outputs_file']);pin(source_path)
    with np.load(source_path)as z:
        U=z['U'].astype(np.int64);beta=z['beta'].astype(np.int64);saved=z['expected_leak'].astype(np.int64)
        frame_lengths=z['frame_lengths'].astype(np.int64)
    N=len(U);assert N==co['operations']==capture['sample_operations']
    assert np.all((U>=-32768)&(U<=32767))and np.all((beta>=0)&(beta<=256))
    assert np.all(U!=0)and np.all(beta!=0),'This diagnostic concerns post-common-zero-filter arithmetic'
    assert frame_lengths.sum()==N
    correct=-np.floor_divide(-U*beta,256)
    assert np.array_equal(correct,saved)
    wrapped=np.remainder(U+256,512)-256
    unsafe=-np.floor_divide(-wrapped*beta,256)
    wide=(U<-256)|(U>255);mismatch=unsafe!=correct;difference=np.abs(unsafe-correct)
    # All current coefficient values are nonzero, hence wrapping U by512k
    # changes ceil(beta*U/256) by the exact nonzero integer2*beta*k.
    assert np.array_equal(wide,mismatch)
    assert np.array_equal(correct-unsafe,2*beta*np.floor_divide(U-wrapped,512))
    python_mismatch=python_wide=python_max=0
    for index,(u,b)in enumerate(zip(U.tolist(),beta.tolist())):
        w=((u+256)%512)-256
        true_value=-((-u*b)//256)
        bad_value=-((-w*b)//256)
        assert (true_value,bad_value,w)==(int(correct[index]),int(unsafe[index]),int(wrapped[index]))
        python_wide+=int(not(-256<=u<=255));python_mismatch+=int(true_value!=bad_value)
        python_max=max(python_max,abs(true_value-bad_value))
    assert python_wide==int(wide.sum())and python_mismatch==int(mismatch.sum())and python_max==int(difference.max())
    first=int(np.flatnonzero(mismatch)[0]);maximum=int(np.argmax(difference))
    ends=np.cumsum(frame_lengths);starts=np.r_[0,ends[:-1]]
    def example(index):
        frame=int(np.searchsorted(ends,index,side='right'))
        return {'scalar_index':index,'window_index':frame,'index_inside_window':int(index-starts[frame]),'U':int(U[index]),'beta':int(beta[index]),'forcibly_reinterpreted_signed9_U':int(wrapped[index]),'declared_full16_leakage':int(correct[index]),'unsafe_wrapped_leakage':int(unsafe[index]),'absolute_deviation':int(difference[index])}
    # Bind the actual captured source NPZ as well as the hardware cohort copy.
    source_npz_path=capture_path.parent/'activity_operands.npz';pin(source_npz_path)
    with np.load(source_npz_path)as z:
        assert np.array_equal(z['U'],U)and np.array_equal(z['beta'],beta)
        assert np.array_equal(z['expected_leak'],correct)
    if label=='OTTT':
        accepted_path=P/'ottt_representative/cohort_acceptance.json';accepted=read(accepted_path)
        assert accepted['status']=='pass'and accepted['capture_results_sha256']==sha(capture_path)
        assert accepted['NPZ_stream_frames_identical'];verify(accepted);pin(accepted_path)
    results[label]={'status':'pass_bound_unsafe_arithmetic_counterfactual','cohort_file':str(cohort_path),'cohort_sha256':sha(cohort_path),'capture_file':str(capture_path),'capture_sha256':sha(capture_path),'hardware_scalar_NPZ_file':str(source_path),'hardware_scalar_NPZ_sha256':sha(source_path),'accepted_capture_NPZ_file':str(source_npz_path),'accepted_capture_NPZ_sha256':sha(source_npz_path),'scalar_operations':N,'source_windows':len(frame_lengths),'nonzero_coefficients':True,'original_signed16_bounds':[int(U.min()),int(U.max())],'actual_coefficient_bounds':[int(beta.min()),int(beta.max())],'signed9_legal_count':int((~wide).sum()),'signed9_domain_exclusion_count':int(wide.sum()),'signed9_domain_exclusion_fraction':float(wide.mean()),'unsafe_leakage_mismatch_count':int(mismatch.sum()),'unsafe_leakage_mismatch_fraction':float(mismatch.mean()),'max_absolute_result_deviation':int(difference.max()),'first_mismatch':example(first),'maximum_deviation_example':example(maximum),'ordinary_Python_integer_cases_checked':N,'ordinary_Python_vs_vectorized_mismatches':0,'saved_reference_vs_vectorized_mismatches':0,'wrap_identity_checked_every_operand':True,'scope':'Unweighted bounded representative64-stream scalar arithmetic after accepted common zero filtering; no model feedback, accuracy, timing or energy inference'}
result={'status':'pass_explicitly_unsafe_fixed_narrow_domain_diagnostic','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'counterfactual':'Discard all upper membrane bits and reinterpret the low9 bits as a signed9 integer, then compute ceil(beta*U_wrapped/256). This changes the declared operation and is explicitly unsafe.','records':results,'verified_accepted_source_artifact_pin_records':verified_pin_count,'total_ordinary_Python_integer_cases_checked':sum(r['ordinary_Python_integer_cases_checked']for r in results.values()),'interpretation':'Actual wide membranes occur even in narrow-heavy GLIF. At nonzero beta, forcing low9 reinterpretation changes every excluded scalar result, so signed9-only E8 cannot preserve these fixed16 workloads. E5 exact fallback is needed for legal wide operands; fallback rarity alone does not make it removable.','limits':['Not a fair hardware baseline: E8 legally supports signed9 inputs only, not arbitrary16-bit truncation.','Not measured or inferred SNN accuracy and not FP32-to-integer conversion error.','No counterfactual results feed the membrane model; no clipping/retuning/change to accepted results.','Counts describe captured windows, not fullnetwork/full10k prevalence or statistical confidence.','No latency, energy or causal contribution claim follows from this arithmetic-only diagnostic.'],'source_artifact_sha256':pins}
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'records':results},indent=2))
