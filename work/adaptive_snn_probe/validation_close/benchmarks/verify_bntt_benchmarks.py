"""Independently audit saved bounded BNTT results; no model execution."""
from pathlib import Path
import hashlib,json,zipfile
import numpy as np
P=Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def read(path):return json.loads(Path(path).read_text())

def check(folder):
    path=P/folder/'results.json'
    if not path.exists():return {'status':'pending_or_failed_attempt','result':str(path)}
    r=read(path);n=r['samples'];c=r['operation_counts']
    pinned={'checkpoint_sha256':'bntt_pretrained_tiny_t30.pth.tar','dataset_sha256':'tiny-imagenet-200.zip',
        'contract_sha256':'bntt_contract.md','runner_sha256':'run_bntt.py','adapter_sha256':'bntt_integer.py',
        'packing_sha256':'ottt_integer_v2.py','predeclared_subset_sha256':'bntt_predeclared_subset.json'}
    for field,name in pinned.items():assert r[field]==sha(P/name),field
    acquisition=read(P/'bntt_acquisition.json')
    assert r['source_commit']==acquisition['source_commit']
    for name,s in acquisition['source_files_sha256'].items():assert sha(P/'bntt_visual_source'/name)==s
    assert c['raw']==n*30*610304
    assert c['zero']+c['nonzero']==c['raw'] and c['issues_adaptive']==c['nonzero']-c['pairs']
    assert 2*c['pairs']<=c['narrow']<=c['nonzero'] and c['packed_mismatches']==0
    assert r['state_mismatches']==r['spike_mismatches']==0
    z=np.load(P/folder/'logits.npz')
    assert z['float'].shape==z['integer'].shape==z['packed'].shape==(n,200)
    assert np.array_equal(z['integer'],z['packed']) and r['packed_vs_integer_logits_bit_equal']
    assert all(np.isfinite(z[key]).all() for key in ('float','integer','packed'))
    assert r['correct']=={key:int((z[key].argmax(1)==z['labels']).sum()) for key in ('float','integer','packed')}
    assert r['integer_vs_float_changed_predictions']==int((z['integer'].argmax(1)!=z['float'].argmax(1)).sum())
    assert r['packed_vs_integer_changed_predictions']==0
    declared=read(P/'bntt_predeclared_subset.json')['samples'][:n]
    assert r['selected_indices']==[s['canonical_index'] for s in declared]
    assert np.array_equal(z['indices'],r['selected_indices'])
    selected=read(P/folder/'selected_images.json')
    with zipfile.ZipFile(P/'tiny-imagenet-200.zip') as archive:
        classes=sorted(archive.read('tiny-imagenet-200/wnids.txt').decode().splitlines())
        annot={row[0]:row[1] for row in (line.split('\t') for line in archive.read('tiny-imagenet-200/val/val_annotations.txt').decode().splitlines())}
        assert len(selected)==n
        for i,(got,want) in enumerate(zip(selected,declared)):
            assert got['canonical_index']==want['canonical_index']
            assert got['image']==want['filename']
            assert got['class_id']==annot[got['image']]==want['class_id']
            assert got['label']==classes.index(got['class_id'])==z['labels'][i]
            assert got['poisson_seed']==2021+got['canonical_index']==want['poisson_seed']
            assert got['jpeg_sha256']==hashlib.sha256(archive.read('tiny-imagenet-200/val/images/'+got['image'])).hexdigest()
    bounds=r['range_by_layer']
    old_fit=all(v['old_min']>=-32768 and v['old_max']<=32767 for v in bounds.values())
    stored_fit=all(v['state_min']>=-32768 and v['state_max']<=32767 for v in bounds.values())
    assert (c['old_signed16_exceptions']==0)==old_fit
    assert (c['stored_signed16_exceptions']==0)==stored_fit
    assert r['fixed16_hardware_domain_supported']==(old_fit and stored_fit)
    assert all(v['old_min']>=-(1<<23) and v['old_max']<(1<<23) and v['state_min']>=-(1<<23) and v['state_max']<(1<<23) for v in bounds.values())
    return {'status':'passed','samples':n,'scope':'Bounded held-out subset; never full TinyImageNet accuracy',
        'correct':r['correct'],'changed_integer_vs_float_predictions':r['integer_vs_float_changed_predictions'],
        'declared_integer_vs_packed':'Every state/spike directly equal; all logits bit equal; independent scalar leakage oracle on every update',
        'state_mismatches':r['state_mismatches'],'spike_mismatches':r['spike_mismatches'],
        'fixed16_hardware_domain_supported':r['fixed16_hardware_domain_supported'],
        'old_signed16_exceptions':c['old_signed16_exceptions'],'stored_signed16_exceptions':c['stored_signed16_exceptions'],
        'raw_updates':c['raw'],'nonzero_updates':c['nonzero'],'adaptive_issues':c['issues_adaptive'],
        'fixed_two_lane_issues':c['issues_fixed_split'],
        'useful_nonzero_operations_per_adaptive_issue':c['nonzero']/c['issues_adaptive'],
        'adaptive_issue_overhead_vs_fixed_two_lane_fraction':c['issues_adaptive']/c['issues_fixed_split']-1,
        'constant_specific_zero_DSP_control':r['constant_specific_zero_DSP_control'],
        'result_sha256':sha(path),'logits_sha256':sha(P/folder/'logits.npz')}

def main():
    folders=sorted(p.name for p in P.iterdir() if p.is_dir() and p.name.startswith('tiny_T30_'))
    out={'status':'source_prepared_no_inference' if not folders else 'bounded_results_audited',
        'runs':{f:check(f) for f in folders},
        'constant_control_proof':read(P/'bntt_constant_control_exactness.json'),
        'auditor_sha256':sha(__file__),
        'no_fully_quantized_SNN_or_board_performance_claim':True}
    (P/'bntt_acceptance.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
