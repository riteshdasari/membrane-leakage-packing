"""Write an additive concise diagnostic report from the pinned bounded audits."""
from pathlib import Path
import hashlib
import json

P=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(word):
    n=int(word,16);data=(n>>1)&0xffffff
    def signed12(value):return value-4096 if value&2048 else value
    return dict(data_hex=f'{data:06x}',lane0=signed12(data&4095),lane1=signed12(data>>12),
                controls=dict(in_ready=(n>>30)&1,take=(n>>28)&3,out_valid=(n>>27)&1,
                              out_count=(n>>25)&3,narrow_mode=n&1))


def main():
    output=P/'bounded_causal_diagnostic_v1'
    assert not output.with_suffix('.json').exists() and not output.with_suffix('.md').exists()
    pair_path=P/'shadow_context_v5/paired_pulse_audit_v1.json'
    hist_path=P/'historical_discrepancy_fields_v1.json'
    source_path=P/'port_context_v1/source_checks_v1.json'
    pair,hist,source=[json.loads(path.read_text()) for path in [pair_path,hist_path,source_path]]
    assert all(pair['gates'].values()) and hist['same_discrepancy_in_all_three_contexts']
    assert all(source['source_gates'].values())
    for value in [pair,hist,source,pair['zero'],pair['hundred']]:
        for key in ['source_sha256','artifact_sha256']:
            assert all(sha(path)==pin for path,pin in value.get(key,{}).items())
    rows=[]
    for key in ['zero','hundred']:
        for item in pair[key]['mismatches']:
            got,expected=decode(item['got']),decode(item['expected'])
            assert got['controls']==expected['controls']
            rows.append(dict(policy_percent=pair[key]['pulse_limit_percent'],row=item['row'],
                 got=got,expected=expected,lane0_error=got['lane0']-expected['lane0'],
                 lane1_error=got['lane1']-expected['lane1']))
    assert len(rows)==2
    assert (rows[0]['row'],rows[0]['lane0_error'],rows[0]['lane1_error'])==(914,512,0)
    assert (rows[1]['row'],rows[1]['lane0_error'],rows[1]['lane1_error'])==(5701,0,-512)
    result=dict(status='bounded_causal_diagnostic_complete_original_numerical_issue_unresolved',
      discrepancies=rows,all_replay_control_fields_equal=True,
      same_error_in_historical_raw_and_EOF_only_balanced=True,
      exactly_four_pulse_limit_arguments_changed=True,
      zero_original_only_settled_error_under_matching_live_shadow_inputs=True,
      pulse100_full_replay_still_fails=True,
      next_control_source_only=str((P/'port_context_v1/preparation.json').resolve()),
      timing_checks_waived=False,original_raw_evidence_modified=False,
      original_discrepancy_resolved=False,hardware_or_energy_acceptance=False,
      scope='The E2 delayed replay diagnosis remains open. Separately audited E7 energy and fixed16 packing evidence must retain their own acceptance gates.',
      bounded_conclusions=pair['bounded_conclusions'],
      source_sha256={str(p.resolve()):sha(p) for p in [Path(__file__),pair_path,hist_path,source_path]},
      unclosed_gates=['Exact simulator event-region/port-path cause has not been identified.',
        'No original full known-row delayed replay passes under either tested policy.',
        'The local output concatenation control is prepared and source-checked but not executed.',
        'Representative model energy and final selected energy require separate accepted closures.',
        'Four inaccessible complete prior methods retain the previously declared novelty limit; no first-ever claim is established.'])
    prose=(
      'The original LUT delayed replay remains numerically unresolved. Closing the three proven terminal SDF forms preserves every raw timing token and does not remove the row914 error: the low lane is509 instead of−3, while the high lane66 and all handshake fields match. This is the same discrepancy as the original saved internal replay.\n\n'
      'The matched combined-root controls verify all annotation, vendor binding, delayed-canary and observation gates. Their normalized command lists differ only in the four explicit pulse percentages. Under zero limits the original cell produces a settled wrong output while a flat live-input shadow is correct under matching observed inputs, both stable beyond the maximum579ps path delay. This bounds the problem to a context or port-path/event-treatment difference; it does not prove a particular event-region cause.\n\n'
      'Changing the four limits to100 removes the first row914 error but the full replay then fails at row5701: the high lane is−519 instead of−7, while low lane−9 and all controls match. Pulse-policy sensitivity is established; a complete numerical repair is not. Neither control replaces the failed original evidence.\n\n'
      'One source-only follow-up retains all556 prior timing CELL strings, the original full known-row monitor and vendor primitive, then adds a matching live-input shadow whose O port uses concatenated sliced nets. The557CELL combined SDF and source transformation pass independent checks. Execution is pending; this local control can test whether the connection shape is sufficient under the observed stream. It cannot reproduce every original topology or establish an exact simulator delta region.\n\n'
      'The fair E7 LUT energy baseline and fixed16 arithmetic/area evidence remain separate. Their accepted closures may support bounded leakage-packing tradeoffs, but this report grants no numerical, hardware or energy acceptance for the original E2 delayed replay. Prior-work equivalence also retains four complete-method access gaps, so it does not establish a first-ever or publication-strength claim.\n')
    output.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    output.with_suffix('.md').write_text(prose,encoding='utf-8')
    print(json.dumps(dict(status=result['status'],json=str(output.with_suffix('.json').resolve()),
                         markdown=str(output.with_suffix('.md').resolve())),indent=2))


if __name__=='__main__':main()
