"""Published AdEx single-neuron software applicability, without quantizing ODEs.

Independent Euler implementations in physical mV/pA/ms/pF/nS units. Brian2 is
not installed: this is not a Brian2 execution or a validated SNN accelerator.
"""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
SOURCE='https://brian2.readthedocs.io/en/stable/examples/frompapers.Naud_et_al_2008_adex_firing_patterns.html'
# C,g,EL,VT,Delta,a,tauw,b,Vreset,I; published values unchanged.
CASES={
 'tonic spiking':[200,10,-70,-50,2,2,30,0,-58,500],
 'adaptation':[200,12,-70,-50,2,2,300,60,-58,500],
 'initial burst':[130,18,-58,-50,2,4,150,120,-50,400],
 'regular bursting':[200,10,-58,-50,2,2,120,100,-46,210],
 'delayed accelerating':[200,12,-70,-50,2,-10,300,0,-58,300],
 'delayed regular bursting':[100,10,-65,-50,2,-10,90,30,-47,110],
 'transient spiking':[100,10,-65,-50,2,10,90,100,-47,180],
 'irregular spiking':[100,12,-60,-50,2,-11,130,30,-48,160],
}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
assert not(P/'results.json').exists()
write(P/'plan.json',dict(status='prepared',source_url=SOURCE,parameters=CASES,
    units=['pF','nS','mV','mV','mV','nS','ms','pA','mV','pA'],
    dt_ms=.1,steps=6000,initial='V=EL,w=0',threshold='after simultaneous Euler update V>0mV',
    reset='V=Vr,w+=b; no clipping of dynamics',
    comparison='Scalar math.exp versus vector NumPy Euler, both use old V/w in both derivatives',
    illustrative_monitor_units_mV=[1,.25],
    scope='No trained network/accuracy, no Brian2 runtime comparison, no fixed-point exactness, no range proof, no fabricated eight-lane scheduling or resource/energy result',source_sha256={str(Path(__file__).resolve()):sha(__file__)}))
names=list(CASES);params=np.array(list(CASES.values()),dtype=np.float64)
C,g,EL,VT,D,a,tau,b,Vr,I=params.T
V=EL.copy();W=np.zeros(8);vector=[];vector_spikes=[[]for _ in names]
for t in range(6000):
    X=V+.1/C*(g*(EL-V)+g*D*np.exp((V-VT)/D)-W)
    J=.1/C*I;S=X+J
    Wn=W+.1/tau*(a*(V-EL)-W)
    assert np.all(np.isfinite(X))and np.all(np.isfinite(Wn))
    fired=S>0
    vector.append(np.stack((V,W,X,J,S,Wn,fired),axis=1))
    for k in np.flatnonzero(fired):vector_spikes[k].append(t)
    V=np.where(fired,Vr,S);W=Wn+b*fired
vector=np.array(vector)
rows=[];failures=[]
for k,name in enumerate(names):
    c,gg,e,vt,d,aa,tw,bb,vr,ii=CASES[name]
    v=e;w=0.;trace=[];spikes=[]
    for t in range(6000):
        # Different evaluation grouping, same declared simultaneous Euler method.
        sv=v+(.1/c)*(gg*(e-v)+gg*d*math.exp((v-vt)/d)+ii-w)
        sw=w+(.1/tw)*(aa*(v-e)-w)
        fire=sv>0
        trace.append((v,w,sv,sw,fire))
        if fire:spikes.append(t);v=vr;w=sw+bb
        else:v=sv;w=sw
    scalar=np.array(trace);vv=vector[:,k,:]
    max_v_error=float(np.max(np.abs(scalar[:,2]-vv[:,4])))
    max_w_error=float(np.max(np.abs(scalar[:,3]-vv[:,5])))
    spike_match=spikes==vector_spikes[k]
    # This is a stated cross-implementation numerical check, not bit identity.
    numerical_pass=spike_match and max_v_error<1e-6 and max_w_error<1e-6
    if not numerical_pass:failures.append(name)
    monitor=[]
    for unit in(1.,.25):
        stored_narrow=(vv[:,0]/unit>=-128)&(vv[:,0]/unit<=127)
        intrinsic_narrow=(vv[:,2]/unit>=-128)&(vv[:,2]/unit<=127)
        wrong=np.flatnonzero(stored_narrow&~intrinsic_narrow)
        monitor.append(dict(unit_mV=unit,stored_V_narrow_samples=int(stored_narrow.sum()),
            intrinsic_X_narrow_samples=int(intrinsic_narrow.sum()),
            V_narrow_but_X_wide_samples=len(wrong),
            first_counterexample=None if not len(wrong)else dict(step=int(wrong[0]),
                V_mV=float(vv[wrong[0],0]),w_pA=float(vv[wrong[0],1]),X_mV=float(vv[wrong[0],2]))))
    file=P/f'case{k}_trace.npz';np.savez_compressed(file,vector=vv,scalar=scalar)
    rows.append(dict(name=name,parameters=CASES[name],samples=6000,spike_count=len(spikes),
        scalar_vector_spike_steps_equal=spike_match,numerical_check_pass=numerical_pass,
        max_Vstar_difference_mV=max_v_error,max_wstar_difference_pA=max_w_error,
        observed_V_range_mV=[float(vv[:,0].min()),float(vv[:,0].max())],
        observed_intrinsic_X_range_mV=[float(vv[:,2].min()),float(vv[:,2].max())],
        observed_pre_reset_sum_range_mV=[float(vv[:,4].min()),float(vv[:,4].max())],
        current_contribution_J_mV=float(vv[0,3]),
        observed_w_range_pA=[float(vv[:,1].min()),float(vv[:,1].max())],
        minimum_abs_threshold_distance_mV=float(np.min(np.abs(vv[:,4]))),
        monitor_examples=monitor,trace_file=str(file),trace_sha256=sha(file)))
    print('ADEX COMPONENT',name,'SPIKES',len(spikes),'CHECK',numerical_pass,'X_RANGE',rows[-1]['observed_intrinsic_X_range_mV'],flush=True)
write(P/'results.json',dict(status='pass_software_component_screen'if not failures else'completed_with_retained_numerical_failures',
    rows=rows,failures=failures,source_url=SOURCE,plan_sha256=sha(P/'plan.json'),
    source_sha256={str(Path(__file__).resolve()):sha(__file__)},
    conclusion='V-only eligibility can be unsafe for the intrinsic intermediate; current exact integer core applies only after a declared numeric contract. Observed float ranges do not certify integer widths.',
    scope='Published eight independent single-neuron parameter cases, unchanged Euler dynamics; no runtime Brian2 validation, training/classification, integer accuracy, packed group speed, hardware or energy claim.'))
