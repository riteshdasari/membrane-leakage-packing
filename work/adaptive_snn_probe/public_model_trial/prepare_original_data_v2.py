"""Use original checksum-verified CIFAR10, retain and reject lossy preview pilot."""
from pathlib import Path
import hashlib,json,pickle,tarfile,sys
sys.dont_write_bytecode=True
import numpy as np
from PIL import Image
P=Path(__file__).resolve().parent
record=json.loads((P/'range_download_acceptance.json').read_text());archive=Path(record['path'])
assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['sha256']=='6d958be074577803d12ecdefd02955f39262c83c16fe9348329d7fe0b5c001ce'
class CIFARUnpickler(pickle.Unpickler):
    def find_class(self,module,name):
        allowed={('numpy.core.multiarray','_reconstruct'):np._core.multiarray._reconstruct,
            ('numpy','ndarray'):np.ndarray,('numpy','dtype'):np.dtype,('_codecs','encode'):__import__('codecs').encode}
        if (module,name)not in allowed:raise pickle.UnpicklingError((module,name))
        return allowed[module,name]
with tarfile.open(archive,'r:gz')as tar:
    member=tar.getmember('cifar-10-batches-py/test_batch');assert member.isfile()
    data=CIFARUnpickler(tar.extractfile(member),encoding='latin1').load()
raw=data['data'];assert raw.shape==(10000,3072)and raw.dtype==np.uint8
images=raw.reshape(10000,3,32,32).transpose(0,2,3,1).copy();labels=np.array(data['labels'],dtype=np.int64)
pilot=np.load(P/'pilot_test64.npz');delta=np.abs(images[:64].astype(np.int16)-pilot['images'].astype(np.int16))
preview=dict(status='rejected_as_original_CIFAR10_benchmark',labels_equal=bool(np.array_equal(labels[:64],pilot['labels'])),
    pixel_entries_different=int((delta!=0).sum()),total_pixel_entries=delta.size,max_pixel_difference=int(delta.max()),
    mean_absolute_pixel_difference=float(delta.mean()),preview_encoding=Image.open(P/'pilot_images/00000.png').format,
    old_pilot_kept=True,old_float_observer_arithmetic_results_scope='Lossy viewer images only; not original CIFAR10 benchmark or hardware evidence.',
    rejected_files=['pilot_results.json','pilot_interpretation.json','static_range_screen_v2.json','pilot_test64.npz','pilot_logits.npz'])
(P/'preview_pilot_rejection.json').write_text(json.dumps(preview,indent=2)+'\n')
assert preview['pixel_entries_different']>0 and preview['preview_encoding']=='JPEG'
for path in(P/'full_test10000.npz',P/'original_test64.npz'):assert not path.exists()
np.savez_compressed(P/'full_test10000.npz',images=images,labels=labels,indices=np.arange(10000))
np.savez_compressed(P/'original_test64.npz',images=images[:64],labels=labels[:64],indices=np.arange(64))
plan=json.loads((P/'pilot_plan.json').read_text());plan['dataset']='Original CIFAR10 official test_batch';plan['source_archive_sha256']=record['sha256']
plan['supersedes_rejected_lossy_preview_pilot']=True
(P/'original_pilot_plan_v2.json').write_text(json.dumps(plan,indent=2)+'\n')
result=dict(status='pass_original_test10000_integrity',samples=10000,original_archive_sha256=record['sha256'],
    pixel_sha256=hashlib.sha256(images.tobytes()).hexdigest(),label_sha256=hashlib.sha256(labels.tobytes()).hexdigest(),
    preview_pilot_rejected=True,primary_test64_exact_slice_of_primary_test10000=True,
    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(P/'full_data_acceptance_v2.json').write_text(json.dumps(result,indent=2)+'\n')
print('ORIGINAL CIFAR10 FULL TEST DATA PASS; LOSSY PREVIEW PILOT REJECTED',flush=True)
