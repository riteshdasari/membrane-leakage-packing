"""Read-only additive E4 comparison; retain E3/E5 v1 unchanged."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal
import datetime,hashlib,importlib.util,json,math,sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;out=P/'glif_scalar_tradeoff_v2.json'
assert not out.exists(),'Preserve prior comparison'
pins={}
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def pin(p):p=Path(p).resolve();pins[str(p)]=sha(p)
prior_path=P/'glif_scalar_tradeoff_v1.json';prior=read(prior_path)
assert prior['status']=='pass_independent_certified_GLIF_E3_E5_tradeoff'
for path,pinned in prior['source_artifact_sha256'].items():assert sha(path)==pinned,path
pin(prior_path);pin(__file__)
auditor_path=P/'audit_power16_12_certified.py';pin(auditor_path)
spec=importlib.util.spec_from_file_location('scalar_tradeoff_v2_certified',auditor_path)
auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
d=P/'hardware/power12_glif_e4_glif_remaining_a0_e4';saved=read(d/'power_audit.json')
assert saved['status']=='pass'and saved['engine']==4 and saved['auditor_sha256']==sha(auditor_path)
assert auditor.annotation(d)==saved,'E4 certified audit must independently reproduce identically'
evidence=read(d/'evidence.json');replay_path=Path(evidence['replay_dir'])/'replay_checks.json';replay=read(replay_path)
native=read(replay['native_check_file']);assert native['cohort']=='actual_glif'
cohort_path=Path(replay['cohort_expectation_file']);co_record=read(cohort_path);co=co_record['cohorts']['actual_glif']
expected_path=Path(co['expected_outputs_file']);e5=prior['records']['5']
assert sha(expected_path)==e5['expected_outputs_sha256']and sha(cohort_path)==e5['cohort_expectation_sha256']
N=saved['native_interval_audit']['scalar_updates'];duration=saved['native_interval_audit']['duration_ps'];assert N==262528
route_path=Path(saved['routed_hardware_file']);route=read(route_path)
assert sha(route_path)==saved['routed_hardware_sha256']and route['status']=='pass'
assert route['core']==saved['core_resources']and route['core']['DSP']==1
assert route['B']==16 and route['clock_period_ns']==12 and route['fixture_FF']==94 and route['latency_advancing_edges']==2
assert route['part']=='xc7a100tcsg324-1'and min(route[k]for k in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))>=0
tree=ET.parse(d/'power_xpe.xml').getroot()
dynamic=sum((Fraction(Decimal(x.attrib['voltage']))*Fraction(Decimal(x.attrib['icc']))for x in tree.findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')),Fraction(0))
energy=dynamic*duration/N;assert math.isclose(float(energy),saved['estimated_dynamic_energy_pJ_per_scalar_update'],rel_tol=1e-12)
e4={'audit_file':str(d/'power_audit.json'),'audit_reproduced_identically':True,'route_file':str(route_path),'route_sha256':sha(route_path),'expected_outputs_file':str(expected_path),'expected_outputs_sha256':sha(expected_path),'cohort_expectation_sha256':sha(cohort_path),'scalar_updates':N,'requests':saved['native_interval_audit']['requests'],'retirements':saved['native_interval_audit']['retirements'],'ROI_duration_ps':duration,'dynamic_power_W':float(dynamic),'pJ_per_scalar':float(energy),'energy_exact_fraction':{'numerator':energy.numerator,'denominator':energy.denominator},'core_resources':saved['core_resources'],'matched_physical_design_nets':saved['matched_physical_design_nets'],'physical_unknown_records':saved['physical_activity_unknown_records'],'export_serialization_energy_bound_pJ':saved['energy_rounding_bound_pJ_per_scalar_update'],'certified_export_audit':saved['certified_export_audit']}
for p in[d/'power_audit.json',d/'evidence.json',d/'power_xpe.xml',d/'power.rpt',replay_path,replay['native_check_file'],cohort_path,expected_path,route_path]:pin(p)
difference=e5['pJ_per_scalar']-e4['pJ_per_scalar'];bound=e5['export_serialization_energy_bound_pJ']+e4['export_serialization_energy_bound_pJ']
records={**prior['records'],'4':e4}
comparison={'energy_change_fraction':e5['pJ_per_scalar']/e4['pJ_per_scalar']-1,'energy_saving_fraction':1-e5['pJ_per_scalar']/e4['pJ_per_scalar'],'energy_change_pJ_per_scalar':difference,'dynamic_power_change_fraction':e5['dynamic_power_W']/e4['dynamic_power_W']-1,'request_count_reduction_fraction':1-e5['requests']/e4['requests'],'ROI_duration_reduction_fraction':1-e5['ROI_duration_ps']/e4['ROI_duration_ps'],'captured_result_rate_ratio_E5_to_E4':e4['ROI_duration_ps']/e5['ROI_duration_ps'],'core_resource_difference':{k:e5['core_resources'][k]-e4['core_resources'][k]for k in('LUT','FF','DSP')},'same_DSP_budget':True,'sum_export_serialization_energy_bounds_pJ':bound,'difference_exceeds_sum_export_rounding_bounds':abs(difference)>bound,'serialization_only_difference_interval_pJ':[difference-bound,difference+bound]}
result={'status':'pass_independent_certified_GLIF_E3_E4_E5_tradeoffs','review_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'v1_all_source_artifact_pins_revalidated':True,'E4_certified_audit_reproduced_identically':True,'same_expected_scalar_operands_and_outputs_sha256':True,'signed_state_bits':16,'clock_period_ns':12,'fixture_FF':94,'junction_temperature_C':25,'process':'typical','records':records,'E5_vs_E3':prior['E5_vs_E3'],'E5_vs_E4':comparison,'interpretation':'E5 offers higher captured scalar-result rate and lower estimated dynamic energy than one-scalar-DSP E4 at equal one-DSP budget, while consuming more fabric. Two-DSP E3 remains a competing point with fewer issues and near energy parity. Together with E1/E7 comparisons, the evidence supports a workload-scoped circuit/resource-energy trade-off, not universal dominance.','remaining_status':{'GLIF_E2':'running_or_pending_not_inferred','OTTT_stress_E2':'retained_failed_no_accepted_energy','full_all_attempted_control_completion':False},'limits':prior['limits']+['The ROI ratio is the observed no-stall primitive fixture result rate, not full-neuron, memory-aware or burst throughput. Same two-advancing-edge latency applies to individual requests.','Original E2 diagnosis and failed stressE2 evidence remain separately retained; these successful scalar controls do not retroactively accept them.'],'source_artifact_sha256':{**prior['source_artifact_sha256'],**pins}}
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'E4_pJ':e4['pJ_per_scalar'],'E5_pJ':e5['pJ_per_scalar'],'E5_vs_E4':comparison},indent=2))
