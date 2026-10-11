"""Acquire the reference framework locally without changing an environment."""
from pathlib import Path
from urllib.request import urlopen
import hashlib,json,zipfile,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;url='https://pypi.org/pypi/spikingjelly/0.0.0.0.10/json'
with urlopen(url,timeout=60)as r:raw=r.read()
(P/'spikingjelly_pypi_metadata.json').write_bytes(raw)
items=json.loads(raw)['urls'];item=next(x for x in items if x['filename'].endswith('.whl'))
with urlopen(item['url'],timeout=60)as r:wheel=r.read()
assert hashlib.sha256(wheel).hexdigest()==item['digests']['sha256']
path=P/'assets'/item['filename'];assert not path.exists();path.write_bytes(wheel)
dest=P/'deps';dest.mkdir(exist_ok=True)
with zipfile.ZipFile(path)as z:
    for info in z.infolist():
        target=(dest/info.filename).resolve()
        assert target.is_relative_to(dest.resolve())
        if info.is_dir():target.mkdir(parents=True,exist_ok=True)
        else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info))
record=dict(status='pass_distribution_hash',package='spikingjelly',version='0.0.0.0.10',
    url=item['url'],path=str(path),sha256=item['digests']['sha256'],bytes=len(wheel),environment_modified=False)
(P/'framework_acquisition.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2),flush=True)
