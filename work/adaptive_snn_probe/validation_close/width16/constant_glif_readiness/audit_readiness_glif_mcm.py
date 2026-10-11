"""Independent read-only source/native/route/energy closure for shared GLIF MCM."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,re,sys
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;W=P.parent;ROOT=W.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b


def source_gate():
 prep=b.read(P/'preparation.json');b.verify(prep['source_sha256'])
 energy=b.read(P/'energy_preparation.json');b.verify(energy['source_sha256'])
 assert prep['exactness_arithmetic_model']==dict(cases=2162688,mismatches=0,RTL_not_yet_executed=True)
 assert prep['complete_representative_capture']['channel_previous_spike_coefficient_reconstruction']=='pass'
 assert prep['trained_channels']==3904 and prep['trained_coefficient_pairs']==149
 assert all(n>0 for n in prep['complete_representative_capture']['selected_beta_counts'].values())
 assert b.sha(P/'tb_energy_glif_mcm.sv')==b.sha(W/'tb_energy16_12.sv')
 assert b.sha(P/'export_energy_glif_mcm.tcl')==b.sha(W/'export16_12.tcl')
 old=(W/'lutceil_e7/audit_power16_lutceil_12.py').read_text()
 oldtail=old[old.index('def tcl_words(line):'):]
 for edit in energy['explicit_physical_audit_identity_changes']:
  assert oldtail.count(edit['before'])==1
  oldtail=oldtail.replace(edit['before'],edit['after'])
 expected=(P/'audit_energy_glif_mcm_header.py').read_text()+'\n\n'+oldtail+'\n\n'+(P/'audit_energy_glif_mcm_certificate.py').read_text()
 assert expected==(P/'audit_energy_glif_mcm.py').read_text()
 oldnodes=ast.parse(old).body;newnodes=ast.parse(expected).body
 for name in ('tcl_words','connectivity','normalization_audit'):
  a,=[n for n in oldnodes if isinstance(n,ast.FunctionDef)and n.name==name]
  z,=[n for n in newnodes if isinstance(n,ast.FunctionDef)and n.name==name]
  assert ast.dump(a,include_attributes=False)==ast.dump(z,include_attributes=False),name
 return prep,dict(status='pass',immutable_preparation_bindings=len(prep['source_sha256']),immutable_energy_bindings=len(energy['source_sha256']),
       physical_parser_and_connectivity_functions_AST_identical=True,complete_physical_annotation_changes_exactly_declared=True,
       known_pin_fixture_bench_and_export_bytes_identical=True,new_measurement_identity='engine9/top_sequential_leak16_glif_mcm')


def native_gate(path,cohort,stall,prep):
 path=Path(path).resolve();d=b.read(path);assert path.parent.parent==P/'hardware'
 assert (d['status'],d['B'],d['cohort'],d['stall'],d['label'])==('pass',16,cohort,stall,'shared_GLIF_checkpoint_MCM_LUT2')
 assert d['beta_domain']==prep['domain']['beta'];b.verify(d['source_sha256']);b.verify(d['artifact_sha256'])
 rows=np.loadtxt(path.parent/'out.txt',dtype=str,ndmin=2)
 cycles=rows[:,0].astype(np.int64);counts=rows[:,1].astype(np.int64);lat=rows[:,3].astype(np.int64)
 values=np.fromiter((int(x,16)for x in rows[:,2]),dtype=np.uint64,count=len(rows))
 assert np.all(np.diff(cycles)>0)and np.all((counts==1)|(counts==2))and np.all(lat>=2)
 total=int(counts.sum());start=np.cumsum(counts)-counts
 if cohort=='exhaustive':
  assert total==2162688 and len(rows)==1081344 and np.all(counts==2)
  pos=np.arange(total,dtype=np.int64);u=pos%65536-32768;coef=np.asarray(prep['domain']['beta'],dtype=np.int64)[pos//65536]
  reference=((u*coef+255)>>8)&65535
 else:
  assert total==262528 and len(rows)==131328
  inputs={key:val for key,val in np.load(W/'actual_glif_expected.npz').items()}
  # A separate exact shift form, independent of the bench's signed division.
  reference=((inputs['U']*inputs['beta']+255)>>8)&65535
  assert np.array_equal(reference,inputs['expected_leak']&65535)
  ends=np.repeat(np.cumsum(inputs['frame_lengths']),inputs['frame_lengths'])
  assert np.array_equal(counts,np.where(ends[start]-start>=2,2,1))
 expected=reference[start].astype(np.uint64)
 pair=counts==2;expected[pair]|=reference[start[pair]+1].astype(np.uint64)<<16
 assert np.array_equal(values,expected)
 fields=d['fields'];assert fields['requests']==fields['retirements']==len(rows)and fields['scalars']==total
 assert fields['first']==int(cycles[0]-lat[0])and fields['last']==int(cycles[-1])
 assert fields['min_latency']==int(lat.min())and fields['max_latency']==int(lat.max())
 if stall==0:assert np.all(lat==2)and fields['clocks']==len(rows)+2
 jobs=[b.read(p)for p in path.parent.glob('*.job.json')];assert len(jobs)==3 and all(j['returncode']==0 for j in jobs)
 logs='\n'.join(p.read_text(errors='replace')for p in path.parent.glob('*.log'))
 assert 'GLIF_MCM_NATIVE PASS'in logs and not re.search(r'FATAL|ERROR:',logs)
 return dict(status='pass',file=str(path),sha256=b.sha(path),cohort=cohort,stall=stall,scalars=total,requests=len(rows),full_raw_output_oracle='pass')


def route_gate(path,prep):
 path=Path(path).resolve();d=b.read(path);assert path.parent.parent==P/'hardware'
 assert d['status']=='pass'and d['top']=='top_sequential_leak16_glif_mcm'and d['label']=='shared_GLIF_checkpoint_MCM_LUT2'
 assert d['B']==16 and d['clock_period_ns']==12 and d['latency_advancing_edges']==2 and d['beta_domain']==prep['domain']['beta']
 assert d['part']=='xc7a100tcsg324-1';b.verify(d['source_sha256']);b.verify(d['artifact_sha256'])
 assert d['full_fixture']['DSP']==d['core']['DSP']==0 and d['full_fixture']['FF']-d['core']['FF']==94
 assert d['full_fixture']['LUT']==d['core']['LUT']
 a=d['slice_accounting'];assert(a['launch_FF'],a['capture_FF'],a['fixture_FF'])==(55,39,94)
 assert all(d[k]>=0 for k in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))
 return dict(status='pass',file=str(path),sha256=b.sha(path),core=d['core'],WNS_ns=d['WNS_ns'],WHS_ns=d['WHS_ns'])


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--native-attempt',default='a0');ap.add_argument('--route');ap.add_argument('--power-directory');ap.add_argument('--attempt',required=True)
 args=ap.parse_args();assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
 output=P/f'independent_readiness_{args.attempt}.json';assert not output.exists()
 prep,source=source_gate();rows=[];bindings=b.pins([Path(__file__),P/'preparation.json',P/'energy_preparation.json'])
 for cohort in ('exhaustive','actual_glif'):
  for stall in (0,1):
   path=P/'hardware'/f'native_{cohort}_s{stall}_{args.native_attempt}'/'acceptance.json'
   rows.append(native_gate(path,cohort,stall,prep));bindings|=b.pins([path])
 physical=route_gate(args.route,prep)if args.route else None
 if physical:bindings|=b.pins([Path(args.route)])
 power=None
 if args.power_directory:
  assert args.route
  wd=Path(args.power_directory).resolve();saved=b.read(wd/'power_audit.json')
  spec=importlib.util.spec_from_file_location('glif_mcm_readiness_energy_audit',P/'audit_energy_glif_mcm.py')
  audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit);power=audit.annotation(wd)
  assert power==saved and power['status']=='pass'and power['engine']==9
  assert Path(power['routed_hardware_file']).resolve()==Path(args.route).resolve()
  bindings|=b.pins([wd/'power_audit.json',wd/'evidence.json'])
 result=dict(status='pass',source_audit=source,native_audits=rows,route_audit=physical,energy_audit=power,
       source_sha256=bindings,scope='Independent full raw RTL output and source-equivalence recheck; measured route/energy included only when explicitly supplied. No first-ever novelty/board claim.')
 b.write(output,result);print(json.dumps(result|dict(source_sha256=f'{len(bindings)} bindings',energy_audit='reproduced'if power else None),indent=2))


if __name__=='__main__':main()
