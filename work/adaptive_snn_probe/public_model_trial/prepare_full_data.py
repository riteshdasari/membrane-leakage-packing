"""Read only the verified original test member using a restricted unpickler."""
from pathlib import Path
import hashlib,json,pickle,tarfile,sys,time
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent
while not(P/'range_download_acceptance.json').exists():time.sleep(3)
record=json.loads((P/'range_download_acceptance.json').read_text());archive=Path(record['path'])
assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['sha256']
class CIFARUnpickler(pickle.Unpickler):
    def find_class(self,module,name):
        allowed={('numpy.core.multiarray','_reconstruct'):np._core.multiarray._reconstruct,
            ('numpy','ndarray'):np.ndarray,('numpy','dtype'):np.dtype,
            ('_codecs','encode'):__import__('codecs').encode}
        if (module,name)not in allowed:raise pickle.UnpicklingError((module,name))
        return allowed[module,name]
with tarfile.open(archive,'r:gz')as tar:
    member=tar.getmember('cifar-10-batches-py/test_batch');assert member.isfile()
    stream=tar.extractfile(member);data=CIFARUnpickler(stream,encoding='latin1').load()
raw=data['data'];assert raw.shape==(10000,3072)and raw.dtype==np.uint8
images=raw.reshape(10000,3,32,32).transpose(0,2,3,1).copy();labels=np.array(data['labels'],dtype=np.int64)
pilot=np.load(P/'pilot_test64.npz')
assert np.array_equal(images[:64],pilot['images'])and np.array_equal(labels[:64],pilot['labels'])
np.savez_compressed(P/'full_test10000.npz',images=images,labels=labels,indices=np.arange(10000))
result=dict(status='pass_original_test10000_and_pilot_pixel_identity',samples=10000,pilot_samples=64,
    original_archive_sha256=record['sha256'],pixel_sha256=hashlib.sha256(images.tobytes()).hexdigest(),
    label_sha256=hashlib.sha256(labels.tobytes()).hexdigest(),hf_pilot_exact_pixel_and_label_match=True,
    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(P/'full_data_acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print('FULL ORIGINAL CIFAR10 TEST DATA AND PILOT IDENTITY PASS',flush=True)
