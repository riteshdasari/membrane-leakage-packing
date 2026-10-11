"""Read-only validation of full-test counts, public pins and rejected-preview gate."""
from pathlib import Path
import json,hashlib,sys
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;OUT=P.parents[2]/'outputs';STEM='membrane_public_model_check'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
manifest=read(OUT/f'{STEM}.manifest.json')
for name,record in manifest['files'].items():
    p=Path(name);assert p.stat().st_size==record['bytes']and sha(p)==record['sha256'],name
summary=read(OUT/f'{STEM}.summary.json');full=summary['full_test'];pilot=summary['original_pilot']
tree=read(P/'tree.json');entries={r['path']:r for r in tree['tree']}
for name,record in summary['source']['records'].items():
    if name not in entries:continue
    p=Path(record['path']);git=hashlib.sha1(f'blob {p.stat().st_size}\0'.encode())
    with p.open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):git.update(b)
    assert git.hexdigest()==entries[name]['sha'],name
model=summary['source']['model_tree_entry'];p=P/'assets/glif_cifar10_T2.pth.tar'
git=hashlib.sha1(f'blob {p.stat().st_size}\0'.encode())
with p.open('rb')as f:
    for b in iter(lambda:f.read(1024*1024),b''):git.update(b)
assert git.hexdigest()==model['sha']and p.stat().st_size==model['size']
archive=read(P/'range_download_acceptance.json');assert sha(Path(archive['path']))==archive['sha256']=='6d958be074577803d12ecdefd02955f39262c83c16fe9348329d7fe0b5c001ce'
assert sha(OUT/f'{STEM}.md')==manifest['report_sha256']and sha(OUT/f'{STEM}.summary.json')==manifest['summary_sha256']
data=np.load(P/'full_test10000.npz');prediction=np.load(P/'full_test_logits_v3.npz')
assert np.array_equal(data['labels'],prediction['labels'])and np.array_equal(data['indices'],np.arange(10000))
assert np.array_equal(prediction['predictions'],prediction['logits'].argmax(1))
assert full['correct']==int((prediction['predictions']==data['labels']).sum())
assert full['accuracy_percent']==full['correct']/100 and full['full_test']and full['samples']==10000
first=np.load(P/'original_pilot_logits_v2.npz');assert np.array_equal(prediction['logits'][:64],first['logits'])
assert np.array_equal(first['labels'],data['labels'][:64])and pilot['correct']==int((first['predictions']==first['labels']).sum())
assert pilot['observer_float_state_disagreements']==pilot['observer_spike_disagreements']==0
assert pilot['neuron_updates']==sum(r['updates']for r in pilot['rows'])==159383552
assert sum(r['spikes']for r in pilot['rows'])==pilot['spikes']
assert [r['scale']for r in summary['operand_screen']['rows']]==[16,64,256,1024]
for row in summary['operand_screen']['rows']:
    assert row['I_fits_i8']+row['current_outside_i8']==row['updates']==pilot['neuron_updates']
    assert row['U8_fraction']==row['U_fits_i8']/row['updates']
assert summary['rejected_preview_pilot']['status']=='rejected_as_original_CIFAR10_benchmark'
preview=np.load(P/'pilot_test64.npz');delta=np.abs(data['images'][:64].astype(np.int16)-preview['images'].astype(np.int16))
assert int((delta!=0).sum())==summary['rejected_preview_pilot']['pixel_entries_different']==183349
assert not summary['integer_neuron_contract_declared']and not summary['public_model_RTL_replayed']and not summary['public_model_hardware_benefit_demonstrated']
assert summary['coefficient_scope_screen']['covered_by_old_near_identity_full_width_regime']==0
assert len(summary['real_arithmetic_envelope_screen']['rows'])==17
assert summary['prior_hardware']['0']['LUT']==121 and summary['prior_hardware']['2']['LUT']==87
print(json.dumps(dict(status='pass_independent_public_stage_verification',files_verified=len(manifest['files']),
    full_original_test_samples=10000,accuracy_percent=full['accuracy_percent'],exact_observer_updates=159383552,
    rejected_lossy_preview_pixels=183349,public_integer_RTL_validated=False,
    manifest_sha256=sha(OUT/f'{STEM}.manifest.json')),indent=2),flush=True)
