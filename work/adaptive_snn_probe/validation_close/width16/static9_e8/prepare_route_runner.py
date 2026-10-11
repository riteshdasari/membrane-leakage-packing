"""Reuse reviewed E7 route plumbing for the one-DSP narrow-only E8 ablation."""
from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent;E7=P.parent/'lutceil_e7'
assert not(P/'run_route_static9.py').exists()
source=(E7/'run_route16_lutceil.py').read_text()
start=source.index('def sources(nativefile):');end=source.index('def main():')
new='''def sources(nativefile):
    prep=read(P/'preparation.json');verify(prep['source_sha256']);verify(prep['artifact_sha256'])
    scalar=read(P/'scalar_cohort.json');verify(scalar['source_sha256']);verify(scalar['artifact_sha256'])
    native=read(nativefile);assert native['status']=='pass'and native['B']==16 and native['legal_state_signed_bits']==9 and native['cohort']=='pair'and native['stall']==0
    verify(native['source_sha256']);verify(native['artifact_sha256'])
    row,=[r for r in native['rows']if r['engine']==8];assert row['native_index']==1
    return prep['source_sha256']|prep['artifact_sha256']|scalar['source_sha256']|scalar['artifact_sha256']|pins([Path(__file__),nativefile,P/'preparation.json',P/'scalar_cohort.json',ROOT/'selective_energy_trial/run_selective_energy.py',ROOT/'common_layout_trial/run_guard_add_selective_route.py'])
'''
source=source[:start]+new+source[end:]
source=source.replace('E7','E8').replace('engine=7','engine=8').replace("'route12_e7_","'route12_e8_").replace("'route_e7_","'route_e8_")
source=source.replace('top_sequential_leak16_lutceil_e7','top_sequential_leak_static9_e8')
source=source.replace('leak_core16_lutceil.sv','leak_core_static9.sv').replace('timing16_lutceil.sv','timing_static9.sv').replace('route16_lutceil.tcl','route_static9.tcl')
source=source.replace("==0\n        assert full['occupied_slices']","==1\n        assert full['occupied_slices']")
source=source.replace("label='optimized_LUT2_exact_quotient_ceil'","label='static_signed9_pair_narrow_domain_cost_ablation',legal_state_signed_bits=9")
source=source.replace("scope='Matched exactgeneralbeta fixed16 optimized LUT leakage OOC route; common94FF excludedarea; originalE2retained; noenergyclaimwithoutstrictSDF/SAIF.'", "scope='NARROW-DOMAIN staticpair costablation only: signed9legallysignextendedon16bitports, coefficients0..256. NoactualUrangecheckorfull16fallback. E5minusE8measurescombinedadmission/widesupportcost, notliteralcontroller-onlyoverhead.'")
ast.parse(source);(P/'run_route_static9.py').write_text(source,encoding='utf-8')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
record=dict(status='prepared_unexecuted',engine=8,native_index=1,legal_state_signed_bits=9,full_port_bits=16,fixture_FF=94,expected_DSP=1,
            source_sha256={str(p):sha(p)for p in[Path(__file__),E7/'run_route16_lutceil.py',P/'preparation.json',P/'scalar_cohort.json']},
            artifact_sha256={str(P/'run_route_static9.py'):sha(P/'run_route_static9.py')},
            command='run_route_static9.py --native-acceptance ABS_PAIR_NATIVE_ACCEPTANCE --attempt a0; optional --resume-synth-from FAILED_ROUTE_DIR')
(P/'route_runner_preparation.json').write_text(json.dumps(record,indent=2)+'\n');print('E8 route runner prepared, NO vendorjobs',flush=True)
