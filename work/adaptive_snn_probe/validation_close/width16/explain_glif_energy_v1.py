"""Read-only certified-audit reproduction and serialized component explanation."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import datetime, hashlib, importlib.util, json, math, sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
auditor_path=P/'audit_power16_12_certified.py'
spec=importlib.util.spec_from_file_location('glif_explanation_certified',auditor_path)
auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
directories={5:P/'hardware/power12_glif_e5_recovery_a0_e5',1:P/'hardware/power12_glif_e1_profiled_all_a0_e1'}
out=P/'glif_energy_explanation_v1.json';assert not out.exists(),'Preserve earlier explanations'
pins={};records={}
def sha(path):
    path=Path(path).resolve();h=hashlib.sha256()
    with path.open('rb')as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()
def pin(path):
    path=Path(path).resolve();pins[str(path)]=sha(path);return str(path)
def read(path):return json.loads(Path(path).read_text())
def fraction(value):return Fraction(Decimal(value))
pin(__file__);pin(auditor_path)
for e,d in directories.items():
    saved=read(d/'power_audit.json')
    assert saved['status']=='pass'and saved['engine']==e
    assert saved['auditor_sha256']==sha(auditor_path)
    actual=auditor.annotation(d)
    assert actual==saved,'Certified audit did not independently reproduce'
    evidence=read(d/'evidence.json');replay=read(Path(evidence['replay_dir'])/'replay_checks.json')
    expectation_path=Path(replay['cohort_expectation_file']);expectation=read(expectation_path)
    native=read(replay['native_check_file']);co=expectation['cohorts'][native['cohort']]
    expected_path=Path(co['expected_outputs_file']);assert native['cohort']=='actual_glif'
    interval=actual['native_interval_audit'];duration=interval['duration_ps'];N=interval['scalar_updates']
    assert N==262528 and co['operations']==N
    tree=ET.parse(d/'power_xpe.xml').getroot()
    voltage_sources=tree.findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')
    dynamic=sum((fraction(x.attrib['voltage'])*fraction(x.attrib['icc'])for x in voltage_sources),Fraction(0))
    energy=dynamic*duration/N
    assert math.isclose(float(dynamic),saved['dynamic_power_W'],rel_tol=1e-12)
    assert math.isclose(float(energy),saved['estimated_dynamic_energy_pJ_per_scalar_update'],rel_tol=1e-12)
    components={};blocks=[]
    for node in tree.findall('BLOCKDETAILS/BYTYPE/BLOCKTYPE'):
        if node.attrib['name']=='Clocks':
            components['clocks_W']=sum((fraction(x.attrib['power'])for x in node.findall('CLOCK')),Fraction(0))
        elif node.attrib['name']=='LOGIC':
            for x in node.findall('LOGIC'):
                kind='register'if'ffs'in x.attrib else'combinational'
                components[kind+'_logic_W']=components.get(kind+'_logic_W',Fraction(0))+fraction(x.attrib['power'])
                components[kind+'_signals_W']=components.get(kind+'_signals_W',Fraction(0))+fraction(x.attrib['sp'])
                blocks.append({'kind':kind,**x.attrib})
        elif node.attrib['name']=='DSP':
            components['DSP_W']=sum((fraction(x.attrib['power'])for x in node.findall('.//DSP48E1')),Fraction(0))
            blocks.extend({'kind':'DSP',**x.attrib}for x in node.findall('.//DSP48E1'))
    components['unassigned_serialized_component_residual_W']=dynamic-sum(components.values(),Fraction(0))
    for p in[d/'power_audit.json',d/'power.xml',d/'power_xpe.xml',d/'power.rpt',d/'power_xpe.rpt',d/'evidence.json',Path(evidence['replay_dir'])/'replay_checks.json',replay['native_check_file'],expectation_path,expected_path,saved['routed_hardware_file']]:pin(p)
    records[str(e)]={'audit_file':str(d/'power_audit.json'),'audit_reproduced_identically':True,'route_file':saved['routed_hardware_file'],'route_sha256':saved['routed_hardware_sha256'],'expected_outputs_file':str(expected_path),'expected_outputs_sha256':sha(expected_path),'cohort_expectation_sha256':sha(expectation_path),'scalar_updates':N,'requests':interval['requests'],'retirements':interval['retirements'],'ROI_duration_ps':duration,'dynamic_power_W':float(dynamic),'pJ_per_scalar':float(energy),'dynamic_power_exact_fraction':{'numerator':dynamic.numerator,'denominator':dynamic.denominator},'energy_exact_fraction':{'numerator':energy.numerator,'denominator':energy.denominator},'components_W':{k:float(v)for k,v in components.items()},'components_pJ_per_scalar':{k:float(v*duration/N)for k,v in components.items()},'serialized_block_details':blocks,'core_resources':saved['core_resources'],'matched_physical_design_nets':saved['matched_physical_design_nets'],'physical_unknown_records':saved['physical_activity_unknown_records'],'physical_activity_sources':saved['physical_activity_source_counts'],'DSP_clock_enable_activity':saved['critical_dsp_activity'],'export_serialization_energy_bound_pJ':saved['energy_rounding_bound_pJ_per_scalar_update'],'certified_export_audit':saved['certified_export_audit']}
    print('REPRODUCED',e,flush=True)
a,b=records['5'],records['1']
assert a['expected_outputs_sha256']==b['expected_outputs_sha256']
assert a['cohort_expectation_sha256']==b['cohort_expectation_sha256']
assert a['scalar_updates']==b['scalar_updates']==262528
component_energy_saving={k:b['components_pJ_per_scalar'][k]-a['components_pJ_per_scalar'][k]for k in a['components_W']}
total=b['pJ_per_scalar']-a['pJ_per_scalar']
assert math.isclose(sum(component_energy_saving.values()),total,abs_tol=1e-9)
result={'status':'pass_independent_certified_GLIF_comparison_explanation','review_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'same_expected_scalar_operands_and_outputs_sha256':True,'signed_state_bits':16,'clock_period_ns':12,'fixture_FF':94,'junction_temperature_C':25,'process':'typical','records':records,'energy_reduction_fraction':1-a['pJ_per_scalar']/b['pJ_per_scalar'],'average_dynamic_power_reduction_fraction':1-a['dynamic_power_W']/b['dynamic_power_W'],'adaptive_request_penalty_fraction':a['requests']/b['requests']-1,'adaptive_ROI_penalty_fraction':a['ROI_duration_ps']/b['ROI_duration_ps']-1,'energy_saving_pJ_per_scalar':total,'serialized_component_energy_savings_pJ_per_scalar':component_energy_saving,'interpretation':'The model predicts less fabric logic, signal and clock-network dynamic energy for the smaller E5 datapath, despite a longer ROI. The single-DSP power also differs with actual operand activity. Component decomposition is observational vendor-model attribution, not an isolated causal experiment.','limits':['Complete common fixture dynamic estimate, not core-only or measured board/full-neuron energy.','Bounded distribution-gated64-image GLIF arithmetic capture after shared zero filtering, not full-stream/fullnetwork energy.','XML component values are serialized rounded reports; residual is explicitly retained and no unrounded precision is implied.','Same94FF fixture does not guarantee identical fixture switching or clock-tree loading; per-design source/result encoding and route differ.','FPGA area resource counts alone do not mathematically determine power; accepted physical switching provides the activity input.','Serialization rounding bound does not bound vendor-model/physical uncertainty.','This result does not establish all-baseline or model-specializedconstant superiority.'],'source_artifact_sha256':pins}
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k]for k in('status','energy_reduction_fraction','average_dynamic_power_reduction_fraction','adaptive_ROI_penalty_fraction','energy_saving_pJ_per_scalar','serialized_component_energy_savings_pJ_per_scalar')},indent=2),flush=True)
