"""Read-only source review and small arithmetic checks; never invokes tools/inference."""
from pathlib import Path
import ast, hashlib, json, re, sys
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent; ABL=P/'static9_e8'; ALT=P/'lutceil_e7'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''):h.update(c)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def verify(d):
    for key in ('source_sha256','artifact_sha256'):
        for p,s in d.get(key,{}).items():assert sha(p)==s,('source changed',p)
def line(p,needle):
    return next(i for i,s in enumerate(Path(p).read_text().splitlines(),1) if needle in s)
def post(p):
    t=Path(p).read_text()
    return t.split('begin:post',1)[1].split('end else if(E==1)',1)[0].strip()

def main():
    sourcepaths=[P/'run_energy_closure_sequence.py',P/'run_energy16_12.py',P/'aggregate_hardwareclosure.py',
                 ALT/'run_native16_lutceil_v2.py',ALT/'run_energy16_lutceil_12.py',ALT/'run_route16_lutceil.py',
                 ABL/'run_native_static9.py',ABL/'run_route_static9.py',ABL/'tb_static9.sv',
                 P/'leak_core16.sv',ABL/'leak_core_static9.sv',ABL/'route_static9.tcl',ABL/'timing_static9.sv',
                 ABL/'preparation.json',ABL/'scalar_cohort.json']
    for f in sourcepaths:
        if f.suffix=='.py':ast.parse(f.read_text(),filename=str(f))
    prep=read(ABL/'preparation.json'); scalar=read(ABL/'scalar_cohort.json');verify(prep);verify(scalar)
    assert prep['B']==16 and prep['legal_state_domain_bits']==9 and prep['fixture_FF']==94
    assert prep['native_engine_indices']==[5,8] and prep['scalar_mismatches']==0
    assert post(P/'leak_core16.sv')==post(ABL/'leak_core_static9.sv')
    cohorts=[]
    for name,stem,want in [('pair','narrow',prep['native_expected_requests_by_index']),('scalar','scalar',scalar['expected_requests_by_native_index'])]:
        with np.load(ABL/f'{stem}_expected.npz') as z:
            u=z['U'];beta=z['beta'];expected=z['expected_leak'];lengths=z['frame_lengths']
            assert np.all((-256<=u)&(u<=255)) and np.all((0<=beta)&(beta<=256))
            assert np.all(expected == -np.floor_divide(-(u.astype(np.int64)*beta.astype(np.int64)),256))
            ends=np.repeat(np.cumsum(lengths),lengths);pos=0;requests=0
            while pos<len(u):
                pair=pos+1<ends[pos] and beta[pos]==beta[pos+1]
                pos+=2 if pair else 1;requests+=1
            assert want==[requests,requests]
            if name=='scalar':assert len(u)==512*257 and np.all(lengths==1)
            cohorts.append(dict(cohort=name,operations=len(u),independent_requests=requests,arithmetic_mismatches=0,signed9_range=True))
    sequence=P/'run_energy_closure_sequence.py';energy=P/'run_energy16_12.py';aggregate=P/'aggregate_hardwareclosure.py'
    findings=[
      dict(priority='required',file=str(sequence),line=line(sequence,"route= b.read"),issue='Hardcoded original a0 aggregate cannot represent accepted mixed original/retry routes.',proposal='Add --resolved-route-acceptance. Verify the immutable manifest, its original acceptance pin, and exactly one accepted hardware.json per engine0..6. Allow a0 successes plus source-identical a1 retry directories; never overwrite original a0 evidence.'),
      dict(priority='required',file=str(sequence),line=line(sequence,'route_template='),issue='One a0 route template forces all engines to use the same route attempt.',proposal='For each selected route, dispatch one-engine energy invocation with a route template whose engine token is retained and whose suffix matches that selected directory. Use unique child attempt per workload/engine or distinct attempt per grouping, because the child progress filename omits engine.'),
      dict(priority='required',file=str(sequence),line=line(sequence,'if rc:'),issue='Child energy runners catch failures and return zero; process status alone does not establish closure.',proposal='After each step require its exact expected acceptance/progress status, verify pins and required rows, and save the acceptance path+SHA in the sequence. For energy require progress status pass, zero failures and all four stage records plus each power_audit.json. Skip dependent stages when prerequisites fail; continue independent branches.'),
      dict(priority='required',file=str(sequence),line=line(sequence,"('aggregate'"),issue='Final aggregation is invoked without its strict-complete option.',proposal='Invoke --strict-complete and independently inspect output JSON. Keep primary comparison closure and original-E2 discrepancy resolution as distinct statuses: E7 acceptance cannot close the original E2 diagnostic.'),
      dict(priority='required_if_reporting_E8',file=str(aggregate),line=line(aggregate,'for root in(P/'),issue='Aggregator scans main/E7 only and excludes E8 native and route evidence.',proposal='Add explicit separate E8 closure gate or a versioned ablation aggregator requiring pair/scalar stalled+unstalled native plus matched12ns route. Check legal_state_signed_bits9, mapping5/8→0/1, and94FF/1DSP. Do not add E8 to the full16 baseline set.'),
      dict(priority='report_binding',file=str(aggregate),line=line(aggregate,'selected_power={}'),issue='Latest route and latest power are selected independently, although every power audit binds a specific routed hardware file.',proposal='For final selected comparison use the explicit resolved route manifest and require power.routed_hardware_file+SHA equal the chosen route. Snapshot all unselected attempts separately. Do not combine area from one route attempt with power from another without identifying both.'),
      dict(priority='low_standalone_provenance',file=str(ABL/'run_native_static9.py'),line=line(ABL/'run_native_static9.py','stamps=prep'),issue='Standalone E8 native pins arithmetic sources through preparation but does not directly pin common job runner or installed glbl.v; parent sequence currently pins both.',proposal='For standalone provenance completeness add these to a versioned E8 native runner, or record parent sequence provenance as required context. This does not invalidate the signed9 arithmetic source gate.'),
      dict(priority='cosmetic',file=str(ABL/'run_route_static9.py'),line=1,issue='Docstring calls E8 an optimized LUT route although it is a one-DSP signed9 cost ablation.',proposal='Correct the label in a future version; current accepted record fields correctly identify1DSP/signed9-only.')
    ]
    result=dict(status='source_review_complete_no_vendor_or_inference',contract=dict(B=16,coefficient_domain=[0,256],clock_ns=12,fixture_FF=94),
                cli_mapping='E7 native6 toengine7; E8 native0/1 toengine5/8; E6 beta128 only',
                e8_checks=dict(preparation_pins_pass=True,scalar_cohort_pins_pass=True,post_correction_source_body_identical=True,cohorts=cohorts,
                               scope='Signed9 cost ablation; range admission and full16 fallback removed. No wide-domain claim. E5minusE8 area is combined admission/widesupport cost, not isolated controller cost.'),
                findings=findings,source_sha256={str(f):sha(f) for f in sourcepaths})
    out=P/'energy_sequence_source_review_v1.json';md=P/'energy_sequence_source_review_v1.md'
    assert not out.exists() and not md.exists(),'Retain earlier reviews.'
    out.write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Fixed16 serial closure source review','', 'Source-only review. No vendor tools, model inference, source mutations or acceptance waivers were performed.','',
           'Engine mappings are consistent: E7 is native index6; E8 native indices0/1 correspond to E5/E8. E8 retains the identical exact post-correction body, and independently recomputed signed9 outputs/counts match both prepared cohorts.','',
           'Required changes to the root-owned sequence:','']
    for f in findings:lines += [f"- [{f['priority']}] {Path(f['file']).name}:{f['line']}: {f['issue']} {f['proposal']}"]
    lines+=['','Resolved route manifest proposal:','',
            'Keep a new immutable JSON with status pass, B16, clock12, fixture94, part, an engine-keyed selected_routes mapping to absolute hardware.json path and SHA256, original_route_acceptance_file+SHA, retained_attempts, source_sha256 and artifact_sha256. Each selected hardware file must pass setup/hold and boundary checks, match top and expected DSP count, and prove source-identical arithmetic/constraints. A retry must retain checkpoint_origin.json and its original DCP pin.','',
            'Record sequence post-stage acceptance hashes, not just child return codes. Original E2 delayed-replay failure, E2 route opt_design error and E7 exact alternate topology are different evidence categories. An E7 pass cannot retrospectively accept original E2.','',f'Exact snapshot: {out.name}.']
    md.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],e8=result['e8_checks'],findings=len(findings),report=str(md))))
if __name__=='__main__':main()
