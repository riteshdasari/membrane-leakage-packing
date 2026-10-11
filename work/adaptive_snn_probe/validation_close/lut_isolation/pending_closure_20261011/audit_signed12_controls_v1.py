"""Independent matched-command/event audit; no vendor launch or acceptance."""
from pathlib import Path
import json,re,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent.parent))
import prepare_fixed16_final_report_v1 as e


def load(folder):
    wd=P/folder/'a0'
    d=e.read(wd/'diagnostic.json',{'completed_optimization_diagnostic'})
    provenance=e.read(wd/'provenance.json')
    logs=[];jobs=[]
    for i in range(5):
        j=e.read(wd/f'tool_{i}.job.json')
        assert j['source_sha256']==provenance and j['returncode']==0
        text=e.bind(wd/f'tool_{i}.log',j['log_sha256']).read_text()
        assert not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation',text)
        jobs.append(j);logs.append(text)
    assert all(d['gates'].values()) and not d['full_original_known_row_replay_pass']
    assert 'root module "tb_sequential_energy_replay"' in logs[3]
    assert '$sdf_annotate will be ignored' not in logs[3]
    assert 'CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS checks2' in logs[4]
    for name in ['CARRY4_vendor.v','original_and_shadow_full.sdf','run.tcl']:
        assert (wd/name).read_bytes()==(P.parent/'shadow_context_v5'/name).read_bytes()
    return wd,d,jobs,logs


def norm(jobs,wd):
    path=str(wd.resolve()).replace('\\','/')
    return [[arg.replace(path,'<RUN>') for arg in j['argv']] for j in jobs]


def events(text,signal):
    found=[]
    for line in text.splitlines():
        m=re.match(r'CAUSAL_EVENT SEQ\d+ T([^ ]+) ROW(\d+) SCOPEoriginal SIGNAL([^ ]+) BIT(\d+) VALUE([01xz])',line)
        if m and m[3]==signal:found.append(dict(time_ns=m[1],row=int(m[2]),bit=int(m[4]),value=m[5]))
    return found


def main():
    target=P/'signed12_controls_independent_audit_v1.json';md=P/'signed12_controls_independent_audit_v1.md'
    assert not target.exists() and not md.exists()
    default=load('run_default_');o0=load('run_o0_')
    unmasked=load('run_ci_unmasked_');masked=load('run_ci_mask_')
    a,b=norm(default[2],default[0]),norm(o0[2],o0[0])
    assert b[3][1]=='--O0'
    b[3].pop(1);assert a==b
    a,b=norm(unmasked[2],unmasked[0]),norm(masked[2],masked[0])
    assert b[4][-2:]==['-testplusarg','MASK_CI']
    b[4]=b[4][:-2];assert a==b
    assert default[1]['replay_mismatches']==o0[1]['replay_mismatches']==unmasked[1]['replay_mismatches']==[dict(row=914,got='6c0843fa',expected='6c085ffa')]
    assert masked[1]['replay_mismatches']==[dict(row=2836,got='6dfec486',expected='6dfec086')]
    old=(P.parent/'shadow_context_v5/monitor_shadow.sv').read_text()
    new=(P/'ci_control_prepared/monitor_shadow.sv').read_text()
    prefix,suffix=new.split(' // Bounded causal intervention only.',1)
    assert prefix.rstrip()==old.rsplit('endmodule',1)[0].rstrip()
    assert suffix.count('force ')==1 and suffix.count('release ')==1
    assert "force dut.fixture.core.\\lut.lane[0].r_reg[11]_i_4 .CI=1'b0;" in suffix
    assert '#11098.000;' in suffix and '#9.000;' in suffix
    assert new==(unmasked[0]/'monitor_shadow.sv').read_text()==(masked[0]/'monitor_shadow.sv').read_text()
    sa,sb=unmasked[3][4],masked[3][4]
    comparisons={}
    for signal in ['S_port','S_in','DI_port']:
        ea,eb=events(sa,signal),events(sb,signal)
        assert ea==eb
        comparisons[signal]=dict(identical=True,event_count_each=len(ea),events=ea)
    assert len(events(sa,'S_port'))==28
    expected=[dict(time_ns='11099.374',row=914,bit=0,value='1'),dict(time_ns='11099.374',row=914,bit=0,value='0')]
    for signal in ['CI_port','CI_in']:
        assert events(sa,signal)==expected and events(sb,signal)==[]
    for row in masked[1]['observations']:
        if 'T11105.999' in row['line']:
            assert 'ORIG_O7 SHADOW_O7 EXPECT_O7' in row['line']
    assert 'CI_INTERVENTION_BEGIN T11098.000 PRE_CI0' in sb and 'CI_INTERVENTION_END T11107.000 CI0' in sb
    route=P.parent.parent.parent/'sequential_paper_trial/hardware/export12_e2_a0/routed.v'
    rv=e.bind(route).read_text()
    occurrences=[dict(line=i,text=line.strip()) for i,line in enumerate(rv.splitlines(),1) if '\\lut.lane[0].r_reg[8]_i_2_n_0 ' in line]
    assert len(occurrences)==3
    assert any('.CI(' in row['text'] for row in occurrences) and any('.CO({' in row['text'] for row in occurrences)
    vendor=e.bind(P.parent/'CARRY4_vendor.v').read_text()
    assert 'assign CO_fb = {CO[2:0], CI_in || CYINIT_in};' in vendor
    assert 'assign O = S_in ^ CO_fb;' in vendor
    assert 'assign CO = (S_in & CO_fb) | (~S_in & DI_in);' in vendor
    for path in [Path(__file__),P/'prepare_ci_control.py',P/'ci_control_prepared/preparation.json']:
        e.bind(path)
    record=dict(status='audited_signed12_optimization_and_connected_CI_intervention',
      matched_optimization_difference_only='xelab --O0',optimization_disabled_first_failure_unchanged=True,
      matched_mask_difference_only='xsim -testplusarg MASK_CI',
      exact_same_bench_SDF_vendor_trace_and_comparisons=True,mask_window_ns=[11098,11107],
      observed_target_S_port_and_S_in_sequences_identical=comparisons,
      observed_DI_has_zero_transitions=True,observed_CI_port_and_internal_same_timestamp_pulse_removed=expected,
      first_wrong_settled_O_and_row914_disappear_under_connected_CI_mask=True,
      later_first_failure_row=2836,full_original_replay_pass=False,
      force_is_proven_pin_local=False,upstream_net_occurrences=occurrences,
      port_net_collapse_caveat='The forced CI is a wire connected to the upstream CARRY4 CO[3] and the live shadow CI. Force may propagate through collapsed nets or change path scheduling. This run did not independently log the upstream CO[3] signal; pin-local isolation is not established.',
      relevant_static_boundary='The parent net is declared once and appears only as upstream CO[3] and target CI in the original netlist. CO[3] is excluded from the upstream model CO_fb={CO[2:0],CI}, but this does not prove simulator isolation of the force.',
      supported_causal_claim='Suppressing the target CI-connected net in this window is sufficient to prevent the first settled output discrepancy and row914 failure, with identical observed S/DI events. This implicates the CI path/pulse treatment as the trigger within this diagnostic context; it does not uniquely identify a simulator event-region defect or prove physical FPGA correctness.',
      exact_pulse_necessary_cause_unconditionally_established=False,
      hardware_energy_acceptance=False,original_evidence_modified=False,vendor_jobs_launched=False,
      checked_hash_count=len(e.PINS),evidence_sha256=e.PINS)
    target.write_text(json.dumps(record,indent=2)+'\n')
    md.write_text('Disabling elaboration optimizations changes only xelab --O0 and leaves the original row914 failure unchanged. The independent CI pair uses the exact same bench, SDF, vendor model, trace and comparison; its only command difference is the MASK_CI plusarg. All recorded jobs, hashes, annotation, timing and delayed-canary gates pass.\n\n'
      'The intervention forces the target CI-connected wire to zero over11098–11107ns. The observed S_port and S_in event sequences are identical (28 events each), DI has no transition, and the same-timestamp CI0→1→0 events at11099.374ns disappear. The original cell is then correct at the settled snapshots, and row914 passes; the run still fails atrow2836. No complete replay repair is established.\n\n'
      'The force is not proven pin-local. Original netlist source connects that wire to upstream CARRY4 CO[3] and the live shadow also reads it; net collapse or force-specific scheduling can affect the intervention. The upstream CO[3] was not independently observed in this matched pair. Although CO[3] is excluded from the upstream behavioral feedback expression, this source fact does not prove local simulator isolation.\n\n'
      'The supported conclusion is that suppressing this connected CI net is sufficient to remove the first failure under otherwise identical observed target S/DI events. It implicates the CI path/pulse handling in this context. An unconditional claim that a pin-local zero-duration pulse is the unique necessary physical cause, a particular simulator bug, or a final fix exceeds the evidence. Timing checks and original rejected energy evidence remain unchanged.\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k in ['status','checked_hash_count','force_is_proven_pin_local','supported_causal_claim']},indent=2))


if __name__=='__main__':main()
