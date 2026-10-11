"""Read-only explicit-path E8 cost-ablation audit; no vendor tools or inference."""
from pathlib import Path
import argparse,hashlib,json,math,re,sys
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;W=P.parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def verify(record):
    for key in('source_sha256','artifact_sha256'):
        for path,pin in record.get(key,{}).items():assert sha(path)==pin,('changed evidence',path)
def accepted(path):
    path=Path(path).resolve();d=read(path);assert d['status']=='pass',(str(path),d['status']);verify(d);return d
def post(path):
    return Path(path).read_text().split('begin:post',1)[1].split('end else if(E==1)',1)[0].strip()

def native(path,cohort,stall,prep,scalar):
    path=Path(path).resolve();d=accepted(path)
    assert(d['B'],d['legal_state_signed_bits'],d['cohort'],d['stall'])==(16,9,cohort,stall)
    assert d['capture']in(0,1) and[(r['native_index'],r['engine'])for r in d['rows']]==[(0,5),(1,8)]
    stem='narrow'if cohort=='pair'else'scalar';expected_file=P/f'{stem}_expected.npz'
    assert d['source_sha256'].get(str(expected_file))==sha(expected_file)
    with np.load(expected_file)as a:
        u=a['U'];beta=a['beta'];want=a['expected_leak'];ends=np.repeat(np.cumsum(a['frame_lengths']),a['frame_lengths'])
        assert np.all((-256<=u)&(u<=255))and np.all((0<=beta)&(beta<=256))
        assert np.array_equal(want,-np.floor_divide(-(u.astype(np.int64)*beta.astype(np.int64)),256))
        desired=prep['native_expected_requests_by_index']if cohort=='pair'else scalar['expected_requests_by_native_index']
        independent=[]
        for index,e in enumerate((5,8)):
            output=path.parent/f'out{index}.txt';assert d['artifact_sha256'].get(str(output))==sha(output)
            pos=requests=0;low=10**9;high=0;first_cycle=last_cycle=None
            with output.open()as stream:
                for line in stream:
                    fields=line.split();assert len(fields)==4
                    cycle,count,value,latency=int(fields[0]),int(fields[1]),int(fields[2],16),int(fields[3])
                    assert pos<len(u);pair=pos+1<ends[pos]and beta[pos]==beta[pos+1]
                    assert count==(2 if pair else 1)and latency>=2
                    expected=int(want[pos])&65535
                    if pair:expected|=(int(want[pos+1])&65535)<<16
                    assert value==expected,(e,pos,value,expected)
                    if last_cycle is not None:assert cycle>last_cycle
                    if first_cycle is None:first_cycle=cycle
                    last_cycle=cycle;pos+=count;requests+=1;low=min(low,latency);high=max(high,latency)
            row=d['rows'][index];assert pos==len(u)and requests==desired[index]
            assert row['neurons']==pos and row['requests']==row['retirements']==requests
            assert row['min_latency']==low and row['max_latency']==high and row['last_retire']==last_cycle
            assert row['service_clocks']==row['last_retire']-row['first_accept']+1
            if stall==0:assert low==high==2 and row['service_clocks']==requests+2
            independent.append(dict(engine=e,operations=pos,requests=requests,min_latency=low,max_latency=high,output_file=str(output),output_sha256=sha(output)))
    return dict(acceptance_file=str(path),acceptance_sha256=sha(path),cohort=cohort,stall=stall,rows=independent)

def route(path,engine):
    path=Path(path).resolve();d=accepted(path);top='top_sequential_leak_static9_e8'if engine==8 else'top_sequential_leak16_e5'
    assert d['B']==16 and d['engine']==engine and d['top']==top and d['clock_period_ns']==12
    assert d['part']=='xc7a100tcsg324-1'and d['latency_advancing_edges']==2
    if engine==8:assert d['legal_state_signed_bits']==9
    acc=d['slice_accounting'];assert(acc['launch_FF'],acc['capture_FF'],acc['fixture_FF'])==(55,39,94)
    assert d['fixture_FF']==94 and d['full_fixture']['FF']-d['core']['FF']==94
    assert d['full_fixture']['LUT']==d['core']['LUT']and d['full_fixture']['DSP']==d['core']['DSP']==1
    for key in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'):assert math.isfinite(d[key])and d[key]>=0
    return d

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in('pair-s0','pair-s1','scalar-s0','scalar-s1','e8-hardware','e5-hardware'):ap.add_argument('--'+name,required=True)
    ap.add_argument('--label',required=True);args=ap.parse_args();assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.label)
    out=P/f'closure_{args.label}.json';md=P/f'closure_{args.label}.md';assert not out.exists()and not md.exists(),'Retain all prior audits.'
    prep=read(P/'preparation.json');scalar=read(P/'scalar_cohort.json');verify(prep);verify(scalar)
    assert prep['B']==16 and prep['legal_state_domain_bits']==9 and prep['scalar_mismatches']==0
    assert post(W/'leak_core16.sv')==post(P/'leak_core_static9.sv'),'E5/E8 exact post-correction source differs.'
    selected=[Path(getattr(args,name.replace('-','_'))).resolve()for name in('pair-s0','pair-s1','scalar-s0','scalar-s1')]
    assert len(set(selected))==4
    records=[native(path,cohort,stall,prep,scalar)for path,(cohort,stall)in zip(selected,[('pair',0),('pair',1),('scalar',0),('scalar',1)])]
    e5file=Path(args.e5_hardware).resolve();e8file=Path(args.e8_hardware).resolve();e5=route(e5file,5);e8=route(e8file,8)
    assert e8['source_sha256'].get(str(selected[0]))==sha(selected[0]),'E8 route not bound to explicit accepted pair/s0 cohort.'
    assert e5['source_sha256'].get(str(W/'leak_core16.sv'))==sha(W/'leak_core16.sv')
    assert e8['source_sha256'].get(str(P/'leak_core_static9.sv'))==sha(P/'leak_core_static9.sv')
    delta={key:e5['core'][key]-e8['core'][key]for key in('LUT','FF','DSP')}
    result=dict(status='pass_narrow_domain_cost_ablation',B=16,legal_E8_signed_bits=9,coefficient_domain=[0,256],clock_ns=12,fixture_FF=94,
                selection_policy='Explicit paths only; no latest-attempt or best-resource selection.',native=records,
                selected_E5_hardware_file=str(e5file),selected_E5_hardware_sha256=sha(e5file),selected_E8_hardware_file=str(e8file),selected_E8_hardware_sha256=sha(e8file),
                E5_core=e5['core'],E8_core=e8['core'],E5_minus_E8_resources=delta,
                exact_post_correction_source_body_identical=True,
                interpretation='Combined cost of actual membrane-range admission plus full signed16 fallback support. Synthesis can merge logic; this subtraction is not isolated controller-only area.',
                limitations=['E8 accepts only signed9 operands signextended on16-bitports; wide operands are unsupported.',
                             'E8 is a restricted-domain cost ablation and cannot replace fixed full16 baselines.',
                             'This audit establishes native correctness and matched route/STA area; E8 energy is not measured.',
                             'Full accelerator, memory traffic, board power and complete-neuron latency are outside this fixture.'],
                source_sha256={str(Path(__file__)):sha(Path(__file__)),str(P/'preparation.json'):sha(P/'preparation.json'),str(P/'scalar_cohort.json'):sha(P/'scalar_cohort.json')},
                artifact_sha256={str(f):sha(f)for f in[*selected,e5file,e8file]})
    out.write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Signed9 static packing cost ablation','',
           'All four explicit E8 native cohorts and the selected E5/E8 matched routes passed independent source and artifact verification. Both routes use16-bitports,12ns and94 fixtureFFs; E8 input values must signextend from9bits.','',
           f"E5 core: {e5['core']['LUT']} LUT, {e5['core']['FF']} FF,1 DSP. E8 core: {e8['core']['LUT']} LUT, {e8['core']['FF']} FF,1 DSP.",'',
           f"E5−E8: {delta['LUT']:+d} LUT, {delta['FF']:+d} FF, {delta['DSP']:+d} DSP. This is the combined admission/full-width-support cost; it is not literal controller-only overhead.",'',
           'E8 is a narrow-domain ablation. It has no wide fallback and supplies no full16 baseline or energy result.','',
           f'E5 route: `{e5file}`. E8 route: `{e8file}`.','',f'Exact evidence: `{out}`.']
    md.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps(dict(status=result['status'],delta=delta,report=str(md))))
if __name__=='__main__':main()
