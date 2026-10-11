"""Complete still-absent future slots; never replace retained range files."""
from pathlib import Path
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,time,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;plan=json.loads((P/'range_download_plan.json').read_text());folder=P/'dataset_ranges_v4';folder.mkdir()
def one(i):
    target=P/'dataset_ranges'/f'{i:03d}.bin';assert not target.exists()
    start=i*plan['chunk_bytes'];n=min(plan['chunk_bytes'],plan['bytes']-start);path=folder/f'{i:03d}.bin'
    for attempt in range(6):
        try:
            url=plan['url']+f'?packing_assist={i}&attempt={attempt}'
            with urlopen(Request(url,headers={'Range':f'bytes={start}-{start+n-1}'}),timeout=60)as r:
                assert r.status==206 and r.headers['Content-Range']==f'bytes {start}-{start+n-1}/{plan["bytes"]}'
                with path.open('wb')as f:
                    while b:=r.read(128*1024):f.write(b)
                assert path.stat().st_size==n
            if not target.exists():path.rename(target);accepted=target
            else:accepted=path
            print('ASSIST RANGE COMPLETE',i,flush=True)
            return dict(index=i,path=str(accepted),bytes=n,sha256=hashlib.sha256(accepted.read_bytes()).hexdigest())
        except Exception as error:
            print('ASSIST RETRY',i,attempt,type(error).__name__,flush=True)
            if attempt==5:raise
            time.sleep(2)
with ThreadPoolExecutor(max_workers=4)as ex:rows=list(ex.map(one,[31,32,33,34]))
(P/'range_assistance_v4.json').write_text(json.dumps(dict(status='transport_complete_not_full_archive_acceptance',rows=rows),indent=2)+'\n')
