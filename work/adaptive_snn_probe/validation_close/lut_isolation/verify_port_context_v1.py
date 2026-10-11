"""Independently audit the one prepared port-shape control and optional result."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import sdf_structure_audit_v1 as parser
from verify_eof_only_sdf_derivative_v1 import verify
W = P / 'port_context_v1'
OLD = P / 'shadow_context_v5'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin_all(values):
    for path,pin in values.items():
        assert sha(path)==pin, path


def inspect_preparation():
    prep=json.loads((W/'preparation.json').read_text())
    for key in ['source_sha256','prepared_sha256']:
        pin_all(prep[key])
    verify(prep['original_SDF_structure_derivative']['certificate'])
    old=(OLD/'monitor_shadow.sv').read_bytes().decode()
    new=(W/'monitor_shadow.sv').read_bytes().decode()
    assert new.startswith(old[:-len('endmodule\n')]) and new.endswith('endmodule\n')
    assert 'if(got!==expected[slot])' in new and '$sdf_annotate' not in new
    flat,=re.findall(r' CARRY4 shadow\((.*?)\);',new,re.S)
    alias,=re.findall(r' CARRY4 alias_shadow\((.*?)\);',new,re.S)
    converted=alias.replace('.CO(alias_co),.O({alias_unused_o3,alias_product[19:17]})',
                            '.CO(shadow_co),.O(shadow_o)')
    assert re.sub(r'\s+','',converted)==re.sub(r'\s+','',flat)
    assert 'wire[3:0] alias_o={alias_unused_o3,alias_product[19:17]};' in new
    texts=[(d/'original_and_shadow_full.sdf').read_bytes().decode() for d in [OLD,W]]
    groups=[]
    for text in texts:
        roots,opened,_=parser.parse(text)
        assert len(roots)==1 and not opened
        groups.append(roots[0].direct('CELL'))
    before,after=groups
    assert len(before)==556 and len(after)==557
    assert all(texts[0][a.start:a.end]==texts[1][b.start:b.end] for a,b in zip(before,after))
    flat,=[c for c in before if parser.instance(c,texts[0])[0]=='shadow']
    alias=after[-1]
    assert parser.instance(alias,texts[1])[0]=='alias_shadow'
    def without_instance(text,cell):
        _,inst=parser.instance(cell,text)
        return text[cell.start:inst.start]+'(INSTANCE)'+text[inst.end:cell.end]
    assert without_instance(texts[0],flat)==without_instance(texts[1],alias)
    assert all((OLD/name).read_bytes()==(W/name).read_bytes() for name in ['CARRY4_vendor.v','run.tcl'])
    ast.parse((P/'run_port_context_v1.py').read_text())
    return prep,dict(all_saved_hashes_verified=True,all_556_existing_cells_byte_identical=True,
      added_timing_cell_identical_except_INSTANCE=True,only_shadow_O_connection_shape_differs=True,
      original_full_known_row_monitor_prefix_retained=True,original_vendor_source_and_runtime_unchanged=True)


def inspect_run(path,prep):
    path=Path(path).resolve()
    folder=path.parent
    assert folder.parent==W.resolve() and folder.name.startswith('run_zero_')
    saved=json.loads(path.read_text())
    provenance=json.loads((folder/'provenance.json').read_text())
    pin_all(provenance);pin_all(saved['artifact_sha256'])
    for name in ['CARRY4_vendor.v','monitor_shadow.sv','original_and_shadow_full.sdf','run.tcl']:
        assert (folder/name).read_bytes()==(W/name).read_bytes()
    jobs=[];logs=[];normalized=[]
    for i in range(5):
        job=json.loads((folder/f'tool_{i}.job.json').read_text())
        assert job['source_sha256']==provenance and job['returncode']==0
        assert Path(job['cwd']).resolve()==folder
        assert sha(folder/f'tool_{i}.log')==job['log_sha256']
        jobs.append(job);logs.append((folder/f'tool_{i}.log').read_text(errors='replace'))
        argv=[item.replace('\\','/') for item in job['argv']]
        assert not any(a in argv for a in ['-notimingchecks','-nospecify','-sdfnowarn','-sdfnoerror'])
        normalized.append([item.replace(str(folder).replace('\\','/'),'<WD>') for item in argv])
    argv=jobs[3]['argv']
    for key in ['-pulse_r','-pulse_int_r','-pulse_e','-pulse_int_e']:
        assert argv.count(key)==1 and argv[argv.index(key)+1]=='0'
    assert all(key in argv for key in ['-maxdelay','-transport_int_delays','-sdfmax'])
    assert all(value in jobs[4]['argv'] for value in [f'ROWS={prep["full_trace_rows"]}',
           f'ROI_LAST={prep["full_trace_rows"]}','ROI_FIRST=3'])
    baseline=OLD/'run_pulse0_a0'
    for i in range(5):
        previous=json.loads((baseline/f'tool_{i}.job.json').read_text())
        prior=[item.replace('\\','/').replace(str(baseline).replace('\\','/'),'<WD>') for item in previous['argv']]
        assert prior==normalized[i], (i,prior,normalized[i])
    annotation=[line for line in logs[3].splitlines() if 'SDF backannotation was successful' in line]
    gates=dict(one_complete_annotation=len(annotation)==1 and 'original_and_shadow_full.sdf' in annotation[0]
      and 'root module "tb_sequential_energy_replay"' in annotation[0],
      source_vendor_CARRY4_bound='Compiling module work.CARRY4' in logs[3],
      annotation_not_ignored='$sdf_annotate will be ignored' not in logs[3],
      no_compile_or_elaboration_warning=not any(re.search(r'\b(?:WARNING|ERROR):',text) for text in logs[:4]),
      no_timing_runtime_warning=not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation',logs[4]),
      delayed_canary_pass='CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS checks2' in logs[4],
      both_snapshot_sets_complete=all(marker in logs[4] for marker in ['CAUSAL_PROBE_SNAPSHOTS_COMPLETE','PORT_CONTEXT_PROBE_SNAPSHOTS_COMPLETE']))
    mismatches=[dict(row=int(row),got=got,expected=expected) for row,got,expected in
        re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)',logs[4])]
    assert mismatches==saved['replay_mismatches']
    observations=[]
    fields=[f'{prefix}_{signal}' for prefix in ['ORIG','FLAT','ALIAS'] for signal in ['AGE','S','CI','CY','DI','O','CO']]+['EXPECT_O','EXPECT_CO']
    for line in logs[4].splitlines():
        if not line.startswith('PORT_CONTEXT_SNAPSHOT '):continue
        values={}
        for key in fields:
            matches=re.findall(r'\b'+key+r'([^ ]+)',line)
            assert len(matches)==1
            values[key]=matches[0]
        known=all(re.fullmatch('[0-9a-fA-F]+',value) for key,value in values.items() if not key.endswith('AGE'))
        row=dict(line=line,known=known)
        if known:
            nums={key:int(value,16) for key,value in values.items() if not key.endswith('AGE')}
            carry=nums['ORIG_CI']|nums['ORIG_CY'];o=co=0
            for bit in range(4):
                s=(nums['ORIG_S']>>bit)&1;di=(nums['ORIG_DI']>>bit)&1
                o|=(s^carry)<<bit;carry=carry if s else di;co|=carry<<bit
            assert (o,co)==(nums['EXPECT_O'],nums['EXPECT_CO'])
            row|=dict(same_observed_inputs=all(nums['ORIG_'+key]==nums['FLAT_'+key]==nums['ALIAS_'+key] for key in ['S','CI','CY','DI']),
                all_stable_gt579ps=all(float(values[key+'_AGE'])>.579 for key in ['ORIG','FLAT','ALIAS']),
                original_wrong=(nums['ORIG_O'],nums['ORIG_CO'])!=(o,co),
                flat_wrong=(nums['FLAT_O'],nums['FLAT_CO'])!=(o,co),
                concatenation_wrong=(nums['ALIAS_O'],nums['ALIAS_CO'])!=(o,co))
        observations.append(row)
    assert observations==saved['observations']
    qualifying=[row for row in observations if row.get('same_observed_inputs') and row.get('all_stable_gt579ps')
                 and row.get('original_wrong') and not row.get('flat_wrong')]
    reproduced=any(row['row']==914 for row in mismatches)
    valid=all(gates.values()) and reproduced and bool(qualifying)
    if not valid:verdict='inconclusive_annotation_replay_or_control_gates_not_all_met'
    elif any(row['concatenation_wrong'] for row in qualifying):verdict='local_output_connection_shape_sensitivity_observed_exact_event_region_cause_unresolved'
    else:verdict='output_concatenation_shape_alone_insufficient_original_cause_unresolved'
    return dict(path=str(path),sha256=sha(path),gates=gates,observations=observations,mismatches=mismatches,
       verdict=verdict,original_discrepancy_resolved=False,hardware_or_energy_acceptance=False,
       every_normalized_vendor_command_identical_to_v5_zero=True,
       artifact_sha256={str(p.resolve()):sha(p) for p in [path,folder/'provenance.json',
         *[folder/f'tool_{i}.{extension}' for i in range(5) for extension in ['job.json','log']]]})


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--diagnostic')
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    target=Path(args.output).resolve()
    assert not target.exists()
    prep,gates=inspect_preparation()
    run=inspect_run(args.diagnostic,prep) if args.diagnostic else None
    result=dict(status='pass_source_only_output_port_control_not_run' if run is None else 'audited_bounded_output_port_control',
      source_gates=gates,run=run,vendor_tools_launched=False,original_discrepancy_resolved=False,
      hardware_or_energy_acceptance=False,
      source_sha256={str(p.resolve()):sha(p) for p in [Path(__file__),W/'preparation.json',P/'sdf_structure_audit_v1.py']})
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='run'},indent=2))


if __name__=='__main__':main()
