"""Additive certified E7 comparison; preserve v1 and all raw records."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import datetime, hashlib, importlib.util, json, math, sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ALT=P/'lutceil_e7'
prior_path=P/'glif_energy_explanation_v1.json';out=P/'glif_energy_explanation_v2.json'
assert not out.exists(),'Preserve prior explanation'
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
pins={}
def pin(p):p=Path(p).resolve();pins[str(p)]=sha(p)
def fraction(s):return Fraction(Decimal(s))
prior=read(prior_path);assert prior['status']=='pass_independent_certified_GLIF_comparison_explanation'
for path,expected in prior['source_artifact_sha256'].items():assert sha(path)==expected,path
records=prior['records'];pin(prior_path);pin(__file__)
auditor_path=ALT/'audit_power16_lutceil_12_certified.py';pin(auditor_path)
spec=importlib.util.spec_from_file_location('e7_explanation_certified',auditor_path)
auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
d=ALT/'hardware/power12_glif_e7_profiled_all_a0_e7';saved=read(d/'power_audit.json')
assert saved['status']=='pass'and saved['engine']==7 and saved['auditor_sha256']==sha(auditor_path)
actual=auditor.annotation(d);assert actual==saved,'Certified E7 audit did not independently reproduce'
evidence=read(d/'evidence.json');replay_path=Path(evidence['replay_dir'])/'replay_checks.json';replay=read(replay_path)
native=read(replay['native_check_file']);assert native['cohort']=='actual_glif'
expectation_path=Path(replay['cohort_expectation_file']);expectation=read(expectation_path)
co=expectation['cohorts']['actual_glif'];expected_path=Path(co['expected_outputs_file'])
assert sha(expected_path)==records['5']['expected_outputs_sha256']==records['1']['expected_outputs_sha256']
assert sha(expectation_path)==records['5']['cohort_expectation_sha256']==records['1']['cohort_expectation_sha256']
interval=saved['native_interval_audit'];N=interval['scalar_updates'];duration=interval['duration_ps'];assert N==262528
route_path=Path(saved['routed_hardware_file']);route=read(route_path)
assert sha(route_path)==saved['routed_hardware_sha256']
assert route['core']==saved['core_resources']and route['core']['DSP']==0
assert route['B']==16 and route['clock_period_ns']==12 and route['fixture_FF']==94
assert route['latency_advancing_edges']==2 and route['part']=='xc7a100tcsg324-1'
assert route['WNS_ns']>=0 and route['WHS_ns']>=0
tree=ET.parse(d/'power_xpe.xml').getroot()
dynamic=sum((fraction(x.attrib['voltage'])*fraction(x.attrib['icc'])for x in tree.findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')),Fraction(0))
energy=dynamic*duration/N
assert math.isclose(float(dynamic),saved['dynamic_power_W'],rel_tol=1e-12)
assert math.isclose(float(energy),saved['estimated_dynamic_energy_pJ_per_scalar_update'],rel_tol=1e-12)
components={};blocks=[]
for node in tree.findall('BLOCKDETAILS/BYTYPE/BLOCKTYPE'):
    if node.attrib['name']=='Clocks':components['clocks_W']=sum((fraction(x.attrib['power'])for x in node.findall('CLOCK')),Fraction(0))
    elif node.attrib['name']=='LOGIC':
        for x in node.findall('LOGIC'):
            kind='register'if'ffs'in x.attrib else'combinational'
            for key,attribute in[(kind+'_logic_W','power'),(kind+'_signals_W','sp')]:components[key]=components.get(key,Fraction(0))+fraction(x.attrib[attribute])
            blocks.append({'kind':kind,**x.attrib})
    elif node.attrib['name']=='DSP':components['DSP_W']=sum((fraction(x.attrib['power'])for x in node.findall('.//DSP48E1')),Fraction(0))
components.setdefault('DSP_W',Fraction(0))
components['unassigned_serialized_component_residual_W']=dynamic-sum(components.values(),Fraction(0))
for p in[d/'power_audit.json',d/'power.xml',d/'power_xpe.xml',d/'power.rpt',d/'evidence.json',replay_path,replay['native_check_file'],expectation_path,expected_path,route_path]:pin(p)
records['7']={'audit_file':str(d/'power_audit.json'),'audit_reproduced_identically':True,'route_file':str(route_path),'route_sha256':sha(route_path),'expected_outputs_file':str(expected_path),'expected_outputs_sha256':sha(expected_path),'cohort_expectation_sha256':sha(expectation_path),'scalar_updates':N,'requests':interval['requests'],'retirements':interval['retirements'],'ROI_duration_ps':duration,'dynamic_power_W':float(dynamic),'pJ_per_scalar':float(energy),'dynamic_power_exact_fraction':{'numerator':dynamic.numerator,'denominator':dynamic.denominator},'energy_exact_fraction':{'numerator':energy.numerator,'denominator':energy.denominator},'components_W':{k:float(v)for k,v in components.items()},'components_pJ_per_scalar':{k:float(v*duration/N)for k,v in components.items()},'serialized_block_details':blocks,'core_resources':saved['core_resources'],'matched_physical_design_nets':saved['matched_physical_design_nets'],'physical_unknown_records':saved['physical_activity_unknown_records'],'physical_activity_sources':saved['physical_activity_source_counts'],'DSP_clock_enable_activity':saved['critical_dsp_activity'],'export_serialization_energy_bound_pJ':saved['energy_rounding_bound_pJ_per_scalar_update'],'certified_export_audit':saved['certified_export_audit']}
comparisons={}
for ea,eb in[(5,1),(5,7),(1,7)]:
    a,b=records[str(ea)],records[str(eb)]
    comparisons[f'E{ea}_versus_E{eb}']={'energy_reduction_fraction':1-a['pJ_per_scalar']/b['pJ_per_scalar'],'dynamic_power_reduction_fraction':1-a['dynamic_power_W']/b['dynamic_power_W'],'issue_count_change_fraction':a['requests']/b['requests']-1,'ROI_duration_change_fraction':a['ROI_duration_ps']/b['ROI_duration_ps']-1,'energy_saved_pJ_per_scalar':b['pJ_per_scalar']-a['pJ_per_scalar'],'serialized_component_energy_savings_pJ_per_scalar':{k:b['components_pJ_per_scalar'][k]-a['components_pJ_per_scalar'][k]for k in a['components_W']}}
result={'status':'pass_independent_certified_GLIF_E5_E1_E7_comparison','review_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'v1_all_source_artifact_pins_revalidated':True,'E7_certified_audit_reproduced_identically':True,'same_expected_scalar_operands_and_outputs_sha256':True,'signed_state_bits':16,'clock_period_ns':12,'fixture_FF':94,'junction_temperature_C':25,'process':'typical','records':records,'comparisons':comparisons,'limits':prior['limits']+['E7 is a validated general two-lane LUT control, not every possible constant-specific FPGA circuit. E7 passing does not resolve original E2 diagnostic.'],'source_artifact_sha256':{**prior['source_artifact_sha256'],**pins}}
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'comparisons':comparisons},indent=2),flush=True)
