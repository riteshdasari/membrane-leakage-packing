"""Pin public source and metadata; no downloaded code is executed here."""
from pathlib import Path
from urllib.request import Request,urlopen
import hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
def get(url):
    with urlopen(Request(url,headers={'User-Agent':'SNN-packing-research'}),timeout=60)as f:return f.read()
def save(name,raw):
    p=P/name;p.parent.mkdir(parents=True,exist_ok=True)
    assert not p.exists();p.write_bytes(raw)
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
api='https://api.github.com/repos/CAS-CLab/Gated-LIF'
commitraw=get(api+'/commits/master');commit=json.loads(commitraw)['sha']
records={'commit_response.json':save('commit_response.json',commitraw)}
tree=get(api+'/git/trees/'+commit+'?recursive=1')
records['tree.json']=save('tree.json',tree)
for name in('README.md','LICENSE','layers.py','blocks.py','networks_for_CIFAR.py','train.py','data_builder.py','utils.py'):
    url=f'https://raw.githubusercontent.com/CAS-CLab/Gated-LIF/{commit}/{name}'
    records[name]=save('sources/'+name,get(url))|{'url':url}
model='trained models/resCifar18stand-CIFAR10-step2-CW.pth.tar'
entry=next(x for x in json.loads(tree)['tree']if x['path']==model)
record=dict(status='source_acquired_not_executed',repository='https://github.com/CAS-CLab/Gated-LIF',
    commit=commit,selected_model=model,model_tree_entry=entry,records=records,
    scope='GLIF trained checkpoint is a gated learned-LIF variant, not a vanilla LIF or FireFly reproduction.')
(P/'source_acquisition.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items()if k!='records'},indent=2),flush=True)
