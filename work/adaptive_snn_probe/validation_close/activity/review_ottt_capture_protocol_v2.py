"""Independent read-only review of the second predeclared OTTT capture protocol."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source=P/'capture_ottt_representative.py';second=P/'capture_ottt_representative_v2.py'
    prepfile=P/'ottt_capture_preparation_v2.json';prep=json.loads(prepfile.read_text())
    first=P/'ottt_random_stratified_a0/results.json';boundary=P/'ottt_random_stratified_a0/window_boundary_diagnostic.json'
    replacements=[("default='ottt_random_stratified_a0'","default='ottt_random_stratified_a1'"),
        ('Eight equal-length nonzero-indexstrata perframe.','Two equal-length nonzero-indexstrata perframe.'),
        ('L=max(1,nearest-even-round(262144*Nframe/(Nfull*8)));min(8,Nframe)windows; capLtofloor(Nframe/K) forshortframes',
         'L=max(1,nearest-even-round(262144*Nframe/(Nfull*2)));min(2,Nframe)windows; capLtofloor(Nframe/K) forshortframes'),
        ('K=min(8,N);L=min(max(1,int(np.rint(target*N/(Nfull*8)))),N//K);weight=N/(K*L)',
         'K=min(2,N);L=min(max(1,int(np.rint(target*N/(Nfull*2)))),N//K);weight=N/(K*L)')]
    assert prep['literal_replacements']==[dict(old=a,new=b) for a,b in replacements]
    assert sha(source)==prep['base_source_sha256'] and sha(second)==prep['new_source_sha256']
    text=source.read_text();revised=text
    for old,new in replacements:
        assert revised.count(old)==1 and text.count(new)==0
        revised=revised.replace(old,new)
    assert revised==second.read_text(),'Unexpected source changes outside the four declared replacements.'
    reversed_=revised
    for old,new in reversed(replacements):
        assert reversed_.count(new)==1;reversed_=reversed_.replace(new,old)
    assert reversed_==text
    ast.parse(text);ast.parse(revised)
    assert sha(first)==prep['predecessor_failed_result_sha256'] and sha(boundary)==prep['boundary_diagnostic_sha256']
    prior=json.loads(first.read_text())
    assert prior['status']=='pass_exact_feedback_failed_distribution_gates' and prior['all64_logits_equal_integer_reference'] and prior['full_counts_equal_prior']
    priorpins={k:v for k,v in prior['source_sha256'].items() if k!=str(source)}
    assert prep['unchanged_prior_pins']==priorpins
    for path,pin in priorpins.items():assert sha(path)==pin,('Changed prior source or model artifact',path)
    for path,pin in prior['artifact_sha256'].items():assert sha(path)==pin,('Changed retained failed capture artifact',path)
    gates=dict(weighted_beta_TV_at_most=.05,weighted_previous_spike_TV_at_most=.05,weighted_U_coarse_TV_at_most=.05,
        absolute_narrow9_fraction_difference_at_most=.01,layer_time_TV_at_most=.005,adaptive_fixed_issue_gap_difference_at_most=.01)
    assert prep['distribution_gates']==gates and prep['fixed_seed']==417839 and prep['target_scalar_operands']==262144 and prep['windows_per_nonzero_frame']==2
    assert prep['attempt_name']=='ottt_random_stratified_a1'
    required=["samples=64,batch=4,threads=2,T=6",'unit=256,full_membrane_interface_signed_bits=16,internal_pair_signed_bits=9',
        'target=262144',"seed_text=f'417839/{self.layer_name}/{timestep}/{batch_start}'",'all64_logits_equal_integer_reference=True',
        'np.array_equal(values,ref[\'integer\'])and np.array_equal(values,ref[\'packed\'])',
        "for key in prior['operation_counts']:assert collected[key]==prior['operation_counts'][key]",
        'assert 150000<=sampleN<=300000','passed=all(v[\'pass_gate\']for v in gates.values())',
        "status='pass_exact_feedback_and_distribution_gates'if passed else'pass_exact_feedback_failed_distribution_gates'"]
    for phrase in required:assert phrase in revised,phrase
    report=dict(status='pass_independent_second_capture_source_review',four_declared_replacements_only=True,
        exact_reverse_substitution_reproduces_first_source=True,all_prior_source_checkpoint_data_and_reference_pins_verified=True,
        prior_source_pin_count=len(priorpins),fixed_seed=417839,target_scalar_operands=262144,
        windows_per_nonzero_frame=2,output_attempt='ottt_random_stratified_a1',unchanged_distribution_gates=gates,
        unchanged_checks=['All 64 logits equal the accepted plain integer and packed reference.',
            'Every raw leakage/state/spike follows an independent scalar oracle and fixed signed16 bounds.',
            'All complete arithmetic counts must equal the prior accepted 64-image execution.',
            'Model source, checkpoint, images, beta128, unit256, T6, batch4 and two threads remain pinned.',
            'Each selected window preserves original operand order; cross-window pairs remain disallowed.',
            'All six representativeness limits, the fixed sample budget and deterministic per-frame seed are retained.'],
        inference_launched=False,vendor_jobs_launched=False,representative_result_accepted=False,
        limitation='The second sampling protocol follows a retained failed first protocol; it is not an independent statistical confidence claim. Fresh execution must still pass every original gate.',
        consumer_followup='The original hardware consumer assumes eight windows and the v1 capture source pin. Use an additive v2 consumer with two-window weighting and explicit v1-to-v2 source admission; do not silently edit the frozen consumer.',
        source_sha256={str(Path(__file__).resolve()):sha(__file__),str(source):sha(source),str(second):sha(second),str(prepfile):sha(prepfile),
            str(first):sha(first),str(boundary):sha(boundary),**priorpins},artifact_sha256=prior['artifact_sha256'])
    out=P/'ottt_capture_v2_independent_source_review.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],prior_pins=len(priorpins),source_review=str(out),new_inference_or_vendor_jobs=False)))


if __name__=='__main__':main()
