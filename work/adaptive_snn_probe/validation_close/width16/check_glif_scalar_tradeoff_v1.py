"""Read-only certified E3 audit and matched E3/E5 resource/energy trade-off."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal
import datetime,hashlib,importlib.util,json,math,sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
out=P/'glif_scalar_tradeoff_v1.json';assert not out.exists(),'Preserve prior record'
pins={}
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def pin(p):p=Path(p).resolve();pins[str(p)]=sha(p)
prior_path=P/'glif_energy_explanation_v1.json';prior=read(prior_path)
assert prior['status']=='pass_independent_certified_GLIF_comparison_explanation'
for path,pinned in prior['source_artifact_sha256'].items():assert sha(path)==pinned,path
pin(prior_path);pin(__file__)
auditor_path=P/'audit_power16_12_certified.py';pin(auditor_path)
spec=importlib.util.spec_from_file_location('scalar_tradeoff_certified',auditor_path)
auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
d=P/'hardware/power12_glif_e3_glif_remaining_a0_e3';saved=read(d/'power_audit.json')
assert saved['status']=='pass'and saved['engine']==3 and saved['auditor_sha256']==sha(auditor_path)
actual=auditor.annotation(d);assert actual==saved,'E3 certified audit must independently reproduce identically'
evidence=read(d/'evidence.json');replay_path=Path(evidence['replay_dir'])/'replay_checks.json';replay=read(replay_path)
native=read(replay['native_check_file']);assert native['cohort']=='actual_glif'
cohort_path=Path(replay['cohort_expectation_file']);co_record=read(cohort_path);co=co_record['cohorts']['actual_glif']
expected_path=Path(co['expected_outputs_file']);e5=prior['records']['5']
assert sha(expected_path)==e5['expected_outputs_sha256']and sha(cohort_path)==e5['cohort_expectation_sha256']
N=saved['native_interval_audit']['scalar_updates'];duration=saved['native_interval_audit']['duration_ps'];assert N==262528
route_path=Path(saved['routed_hardware_file']);route=read(route_path)
assert sha(route_path)==saved['routed_hardware_sha256']and route['status']=='pass'
assert route['core']==saved['core_resources']and route['core']['DSP']==2
assert route['B']==16 and route['clock_period_ns']==12 and route['fixture_FF']==94 and route['latency_advancing_edges']==2
assert route['part']=='xc7a100tcsg324-1'and min(route[k]for k in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))>=0
tree=ET.parse(d/'power_xpe.xml').getroot()
dynamic=sum((Fraction(Decimal(x.attrib['voltage']))*Fraction(Decimal(x.attrib['icc']))for x in tree.findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')),Fraction(0))
energy=dynamic*duration/N;assert math.isclose(float(energy),saved['estimated_dynamic_energy_pJ_per_scalar_update'],rel_tol=1e-12)
e3={'audit_file':str(d/'power_audit.json'),'audit_reproduced_identically':True,'route_file':str(route_path),'route_sha256':sha(route_path),'expected_outputs_file':str(expected_path),'expected_outputs_sha256':sha(expected_path),'cohort_expectation_sha256':sha(cohort_path),'scalar_updates':N,'requests':saved['native_interval_audit']['requests'],'retirements':saved['native_interval_audit']['retirements'],'ROI_duration_ps':duration,'dynamic_power_W':float(dynamic),'pJ_per_scalar':float(energy),'energy_exact_fraction':{'numerator':energy.numerator,'denominator':energy.denominator},'core_resources':saved['core_resources'],'matched_physical_design_nets':saved['matched_physical_design_nets'],'physical_unknown_records':saved['physical_activity_unknown_records'],'export_serialization_energy_bound_pJ':saved['energy_rounding_bound_pJ_per_scalar_update'],'certified_export_audit':saved['certified_export_audit']}
for p in[d/'power_audit.json',d/'evidence.json',d/'power_xpe.xml',d/'power.rpt',replay_path,replay['native_check_file'],cohort_path,expected_path,route_path]:pin(p)
difference=e5['pJ_per_scalar']-e3['pJ_per_scalar'];bound=e5['export_serialization_energy_bound_pJ']+e3['export_serialization_energy_bound_pJ']
result={'status':'pass_independent_certified_GLIF_E3_E5_tradeoff','review_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'v1_all_source_artifact_pins_revalidated':True,'same_expected_scalar_operands_and_outputs_sha256':True,'signed_state_bits':16,'clock_period_ns':12,'fixture_FF':94,'junction_temperature_C':25,'process':'typical','records':{'3':e3,'5':e5},'E5_vs_E3':{'energy_change_fraction':e5['pJ_per_scalar']/e3['pJ_per_scalar']-1,'energy_change_pJ_per_scalar':difference,'dynamic_power_change_fraction':e5['dynamic_power_W']/e3['dynamic_power_W']-1,'request_count_change_fraction':e5['requests']/e3['requests']-1,'ROI_duration_change_fraction':e5['ROI_duration_ps']/e3['ROI_duration_ps']-1,'core_resource_difference':{k:e5['core_resources'][k]-e3['core_resources'][k]for k in('LUT','FF','DSP')},'DSP_count_reduction_fraction':1-e5['core_resources']['DSP']/e3['core_resources']['DSP'],'sum_export_serialization_energy_bounds_pJ':bound,'difference_exceeds_sum_export_rounding_bounds':abs(difference)>bound,'serialization_only_difference_interval_pJ':[difference-bound,difference+bound]},'interpretation':'E3 is a legitimate competing point: slightly lower estimated dynamic energy and fewer issues with two DSPs and fewer LUTs. E5 halves DSP count at higher LUT count, lower FF count and near energy parity in this bounded workload. Neither dominates the complete resource/issue/energy vector.','remaining_status':{'E4':'running_or_pending_not_inferred','full_control_completion':False},'limits':['Vendor-estimated complete94FFfixture dynamic energy, not core-only or measured board/full-neuron energy.','Serialization bound quantifies report rounding only; this~1% estimate separation is not a physical statistical significance claim.','Requests are primitive issues, not measured complete-neuron burst latency. E3 can issue independent coefficients; E5 pair admission requires matching coefficients and signed9 values.','A second DSP can be a binding system budget, but no complete accelerator replication/bandwidth/energy consequence is measured here.','No invented weighted FPGA area score is used; LUT,FF,DSP costs remain separate.','Bounded distribution-gated64-image GLIF arithmetic after common zero filtering; no universal workload/model-specializedconstant win.'],'source_artifact_sha256':{**prior['source_artifact_sha256'],**pins}}
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'E3_pJ':e3['pJ_per_scalar'],'E5_pJ':e5['pJ_per_scalar'],'E5_vs_E3':result['E5_vs_E3']},indent=2))
