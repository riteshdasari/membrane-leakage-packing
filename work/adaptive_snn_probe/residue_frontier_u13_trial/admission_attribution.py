"""Runtime-value admission versus optimistic static interval admission.

This is a service-policy ablation, not another measured hardware implementation.
Static flags and their delivery are assigned zero cost, favoring the control.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import json,hashlib
import numpy as np
P=Path(__file__).resolve().parent
ledger_path=P/'original_if/reference_ledger.json'
d=json.loads(ledger_path.read_text())
models={}
for meta in d['metadata']:
    z=np.load(meta['weights_file'])
    bounds=[]
    for wname in ('w0','w1'):
        w=z[wname].astype(np.int64)
        lo=np.minimum(w,0).sum(axis=0);hi=np.maximum(w,0).sum(axis=0)
        bounds.append((lo,hi))
    models[meta['seed']]=dict(bounds=bounds,state_bounds=[(np.zeros(128,np.int64),np.zeros(128,np.int64)),
                                                      (np.zeros(10,np.int64),np.zeros(10,np.int64))])
policies=['fixed_full8','runtime_U8_tail','static_32step_U8_tail','static_timestep_interval_U8_tail']
records={name:dict(requests=0,groups=0,scalar_updates=0,take_histogram={str(k):0 for k in range(1,9)}) for name in policies}
seen={};dynamic_tails=static_tails=time_tails=0
for row in d['ledger']:
    seed,layer,t,image=row['seed'],row['layer'],row['t'],row['image']
    model=models[seed];lo,hi=model['bounds'][layer]
    if (seed,layer,t) not in seen:
        a,b=model['state_bounds'][layer]
        seen[(seed,layer,t)]=(a.copy(),b.copy())
        smin,smax=a+lo,b+hi;th=row['threshold']
        # Monotone on each side of threshold, with one downward jump.
        amin=np.where(smin>=th,smin-th,np.where(smax>=th,np.minimum(smin,0),smin))
        bmax=np.where(smax<th,smax,np.where(smin>=th,smax-th,np.maximum(th-1,smax-th)))
        model['state_bounds'][layer]=(amin,bmax)
    a,b=seen[(seed,layer,t)]
    u=np.array(row['postleak_U'],np.int64)
    assert np.all(u>=a) and np.all(u<=b)
    runtime=(u>=-128)&(u<=127)
    static=(31*lo>=-128)&(31*hi<=127)
    time_static=(a>=-128)&(b<=127)
    assert np.all(~static|runtime) and np.all(~time_static|runtime)
    masks={'runtime_U8_tail':runtime,'static_32step_U8_tail':static,'static_timestep_interval_U8_tail':time_static}
    for name in policies:
        rec=records[name];rec['groups']+=1;rec['scalar_updates']+=len(u)
        pos=0
        while pos<len(u):
            av=min(8,len(u)-pos)
            n=av if name=='fixed_full8' else min(5,av)
            if name!='fixed_full8':
                while n<av and masks[name][pos+n]:n+=1
            rec['requests']+=1;rec['take_histogram'][str(n)]+=1;pos+=n
    dynamic_tails+=int(runtime.sum());static_tails+=int(static.sum());time_tails+=int(time_static.sum())
for rec in records.values():rec['service_clocks']=rec['requests']+4*rec['groups']
native=json.loads((P/'results/native_models_0_a0/frontier_checks.json').read_text())
assert records['runtime_U8_tail']['requests']==native['rows'][5]['requests']
assert records['runtime_U8_tail']['service_clocks']==native['rows'][5]['service_clocks']
assert records['fixed_full8']['service_clocks']==native['rows'][2]['service_clocks']
result=dict(status='pass',policies=records,
    runtime_admissible_values=dynamic_tails,static32step_admissible_values=static_tails,
    timestep_interval_admissible_values=time_tails,
    static_control_has_zero_detection_flag_memory_or_delivery_cost=True,
    group_drain_clocks=4,original_IF_steps=32,neurons=635904,
    source_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in
                  (Path(__file__),ledger_path,P/'original_if/profile.json',P/'results/native_models_0_a0/frontier_checks.json')},
    scope='Same ordered5full+3narrow-tail admission policy. Static bounds use weights/timestep/threshold, not actual U. Service-only ablation with optimistic zero-cost static flags; no route, energy, reordering or best-static-hardware claim.')
out=P/'admission_attribution.json';assert not out.exists()
out.write_text(json.dumps(result,indent=2)+'\n')
print({name:(r['requests'],r['service_clocks']) for name,r in records.items()},flush=True)
