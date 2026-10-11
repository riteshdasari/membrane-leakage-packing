"""Read-only admission/acceptance audit; never replaces a pending full result."""
from pathlib import Path
import gzip, hashlib, json, struct
import numpy as np

P = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def width_audit(ranges, width=16):
    low, high = -(1 << (width-1)), (1 << (width-1))-1
    bad_old = {k:v for k,v in ranges.items() if v['old_min']<low or v['old_max']>high}
    bad_next = {k:v for k,v in ranges.items() if v['state_min']<low or v['state_max']>high}
    return {'width':width, 'old_operand_bounds_fit':not bad_old,
        'every_post_reset_stored_state_bounds_fit':not bad_next,
        'unsupported_old_layers':bad_old, 'unsupported_post_reset_layers':bad_next,
        'post_reset_exception_count':0 if not bad_next else None,
        'post_reset_count_derivation':'Global min/max covers every state in each forward, including zero leakage bypass. A bound violation is flagged unsupported; no count is invented.'}

def check_run(folder, expected_samples):
    path=P/folder/'results.json'
    if not path.exists():
        return {'status':'pending', 'path':str(path),
            'progress':read(P/folder/'progress.json') if (P/folder/'progress.json').exists() else None}
    r=read(path); c=r['operation_counts']
    assert r['samples']==expected_samples
    for field,source in [('checkpoint_sha256',P/'cifar10_ottta.pth'),
        ('data_sha256',P.parents[1]/'public_model_trial'/'full_test10000.npz'),
        ('contract_sha256',P/'ottt_contract.md')]:
        assert r[field]==sha(source), (folder,field)
    pinned_code=[('runner_sha256',P/('run_ottt_v3.py' if folder=='cifar10_T6_n64_a2' else 'run_ottt_stream.py'))]
    pinned_code += [('integer_sha256',P/'ottt_integer_v2.py')] if folder=='cifar10_T6_n64_a2' else [
        ('adapter_sha256',P/'ottt_integer_v3.py'),('packing_sha256',P/'ottt_integer_v2.py')]
    for field,source in pinned_code:assert r[field]==sha(source),(folder,field)
    assert r['source_commit']==read(P/'ottt_commit.json')['sha']
    assert c['raw']==expected_samples*2_457_600
    assert c['zero']+c['nonzero']==c['raw']
    assert c['issues_adaptive']==c['nonzero']-c['pairs']
    assert c['issues_scalar']==c['nonzero']
    assert c['packed_mismatches']==0
    assert 2*c['pairs']<=c['narrow']<=c['nonzero']
    z=np.load(P/folder/'logits.npz')
    assert len(z['labels'])==expected_samples
    fp=z['float']; integer=z['integer']; labels=z['labels']
    with np.load(P.parents[1]/'public_model_trial'/'full_test10000.npz') as original:
        assert np.array_equal(labels,original['labels'][:expected_samples])
    assert np.isfinite(fp).all() and np.isfinite(integer).all()
    got={'float':int((fp.argmax(1)==labels).sum()),'integer':int((integer.argmax(1)==labels).sum())}
    wanted_integer=r['correct'].get('integer',r['correct'].get('integer_packed'))
    assert got['float']==r['correct']['float'] and got['integer']==wanted_integer
    if 'packed' in z.files:
        assert np.array_equal(integer,z['packed'])
        assert r['packed_vs_integer_logits_equal']
        assert r['state_mismatches']==r['spike_mismatches']==0
    else:
        assert r['changed_integer_vs_float_predictions']==int((fp.argmax(1)!=integer.argmax(1)).sum())
    w=width_audit(r['range_by_layer'])
    if 'signed16_exceptions' in c:
        assert (c['signed16_exceptions']==0)==w['old_operand_bounds_fit']
    if (P/folder/'actual_operand_frames.txt').exists():
        lines=(P/folder/'actual_operand_frames.txt').read_text().splitlines()
        frame_count=int(lines[0]); i=1; u=[]; beta=[]
        for _ in range(frame_count):
            n=int(lines[i]);i+=1
            for _ in range(n):
                a,b=map(int,lines[i].split());i+=1;u.append(a);beta.append(b)
        assert i==len(lines) and len(u)==r['sample_operand_count']
        assert all(b==128 for b in beta)
        assert min(u)==r['sample_u_min'] and max(u)==r['sample_u_max']
        assert sha(P/folder/'actual_operand_frames.txt')==r['sample_sha256']
        meta=read(P/folder/'actual_operand_frames.json')
        assert frame_count==len(meta)
        assert u==[x for f in meta for x in f['u']]
    return {'status':'passed', 'samples':expected_samples,'correct':got,
        'changed_predictions':int((fp.argmax(1)!=integer.argmax(1)).sum()),
        'result_sha256':sha(path),'logits_sha256':sha(P/folder/'logits.npz'),
        'packing_local_mismatches':c['packed_mismatches'],
        'separate_integer_vs_packed_full_feedback': 'passed; every state/spike and all logits' if 'packed' in z.files else '64-image separate-execution evidence plus local scalar oracle on every full-run leakage result',
        'integer_vs_fp32_is_conversion':True, 'width_acceptance':w,
        'raw_updates':c['raw'], 'nonzero_updates':c['nonzero'],
        'adaptive_issues':c['issues_adaptive'],'fixed_two_lane_issues':c['issues_fixed_split'],
        'useful_nonzero_operations_per_adaptive_issue':c['nonzero']/c['issues_adaptive'],
        'adaptive_issue_overhead_vs_fixed_two_lane_fraction':c['issues_adaptive']/c['issues_fixed_split']-1,
        'zero_DSP_exact_control':'ceil(U/2); shift and rounding bit',
        'no_full_accelerator_performance_or_energy_claim':True}

def mnist_manifest():
    entries=[]
    for name,md5 in [('t10k-images-idx3-ubyte.gz','9fb629c4189551a2d022fa330f9573f3'),
        ('t10k-labels-idx1-ubyte.gz','ec29112dd5afa0611ce80d1b7f02629c')]:
        path=P/'mnist_public'/name
        raw=path.read_bytes(); assert hashlib.md5(raw).hexdigest()==md5
        content=gzip.decompress(raw)
        magic,count=struct.unpack('>II',content[:8]); assert count==10000
        if 'images' in name:
            rows,cols=struct.unpack('>II',content[8:16]);assert magic==2051 and rows==cols==28 and len(content)==16+10000*28*28
        else:
            assert magic==2049 and len(content)==8+10000 and max(content[8:])==9
        entries.append({'path':str(path),'url':'https://storage.googleapis.com/cvdf-datasets/mnist/'+name,
            'bytes':len(raw),'md5':md5,'sha256':sha(path),'count':count,'idx_magic':magic})
    return {'status':'downloaded_and_verified_only','inference_performed':False,'files':entries}

def main():
    files={str(p.relative_to(P)).replace('\\','/'):sha(p) for p in sorted((P/'ottt_source').rglob('*.py'))}
    sources={'repository':'https://github.com/pkuxmq/OTTT-SNN',
        'commit':read(P/'ottt_commit.json')['sha'],'downloaded_source_sha256':files,
        'checkpoint':{'official_readme_folder':'https://drive.google.com/drive/folders/1eDn3mVgfBHTLBfb--WawgA5Qms4oFbZ4',
            'file_id':'1Zgp4UAaTKdbkQ2Xrff7G5DoCg7n2GHI0','path':str(P/'cifar10_ottta.pth'),'sha256':sha(P/'cifar10_ottta.pth')},
        'original_model':'online_spiking_vgg11_ws, vanilla OnlineLIF, tau=2, T=6, threshold1 with >= firing, immediate subtractive reset',
        'conversion':'FP32 synapses/readout; neuron currents RNE to unit1/256, ceil(U/2), threshold256, subtract256 reset; no retuning'}
    data_root=P.parents[1]/'public_model_trial'
    data_acceptance=read(data_root/'full_data_acceptance_v2.json')
    with np.load(data_root/'full_test10000.npz') as original:
        images,labels,indices=original['images'],original['labels'],original['indices']
        assert images.shape==(10000,32,32,3) and images.dtype==np.uint8
        assert np.array_equal(indices,np.arange(10000))
        assert hashlib.sha256(images.tobytes()).hexdigest()==data_acceptance['pixel_sha256']
        assert hashlib.sha256(labels.tobytes()).hexdigest()==data_acceptance['label_sha256']
    sources['dataset']={'canonical_url':'https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz',
        'original_archive_sha256':data_acceptance['original_archive_sha256'],
        'original_pixel_sha256':data_acceptance['pixel_sha256'],'original_label_sha256':data_acceptance['label_sha256'],
        'npz_sha256':sha(data_root/'full_test10000.npz'),
        'all10000_test_images_in_original_order':True,'preview_pilot_rejected':data_acceptance['preview_pilot_rejected']}
    (P/'ottt_source_manifest.json').write_text(json.dumps(sources,indent=2)+'\n')
    runs={f:check_run(f,n) for f,n in [('cifar10_T6_n64_a2',64),('profile16_a0',16),('cifar10_full10000_a0',10000)]}
    out={'status':'full_evaluation_passed' if runs['cifar10_full10000_a0']['status']=='passed' else 'full_evaluation_pending',
        'runs':runs,'public_mnist':mnist_manifest(),
        'iir_admission':read(P/'iir_admission_audit.json')['status'],
        'source_manifest_sha256':sha(P/'ottt_source_manifest.json'),
        'audit_source_sha256':sha(__file__),
        'scope':'Exact packing preserves the declared integer neuron. Accuracy vs unmodified FP32 evaluates conversion, not packing; tau2 needs no DSP.'}
    (P/'benchmark_acceptance.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
