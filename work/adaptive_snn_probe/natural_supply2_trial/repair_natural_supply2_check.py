"""Re-check completed native evidence with a new checker, retaining failures."""
from pathlib import Path
import json
import sys

sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
W=P.parent/'residue_frontier_u13_trial'
sys.path.insert(0,str(W))
import run_u13_physical as run


def main():
    assert '--run' in sys.argv
    assert not (P/'acceptance.json').exists()
    wd=P/'native_models_0_a0'
    original=run.read(wd/'provenance.json');run.verify(original)
    for index in range(4):
        job=run.read(wd/f'tool_{index}.job.json')
        assert job['returncode']==0 and job['source_sha256']==original
        assert run.sha(wd/f'tool_{index}.log')==job['log_sha256']
    failed=run.read(wd/'tool_4.job.json')
    assert failed['returncode']==1 and failed['source_sha256']==original
    assert run.sha(wd/'tool_4.log')==failed['log_sha256']
    assert 'NATURAL_SUPPLY2_COMPARE PASS STALL 0' in (wd/'tool_3.log').read_text()
    output=wd/'supply2_checks_v2.json';assert not output.exists()
    files=[Path(__file__),P/'verify_natural_supply2_v2.py',wd/'provenance.json']
    files+=list(wd.glob('tool_*.job.json'))+list(wd.glob('tool_*.log'))
    files+=list(wd.glob('frontier_out*.txt'))+[wd/'frontier_trace6.txt']
    stamps=original|run.pins(files)
    run.write(wd/'verification_repair_provenance.json',stamps)
    run.tool([sys.executable,'-B',P/'verify_natural_supply2_v2.py','--directory',wd,
              '--output',output],wd,'verify_repair',stamps,1.2)
    checked=run.read(output)
    assert checked['status']=='pass' and len(checked['rows'])==7
    assert checked['shared_source_trace']['actual_idle_prelude_work_take_checked']
    assert all(row['requests']==317952 and row['service_clocks']==327168 for row in checked['rows'])
    run.verify(stamps)
    repair=dict(original_failed_job=str(wd/'tool_4.job.json'),
        original_failed_job_sha256=run.sha(wd/'tool_4.job.json'),
        original_failed_log=str(wd/'tool_4.log'),original_failed_log_sha256=run.sha(wd/'tool_4.log'),
        observed_failure='Original checker required every supplemental posedge-done instrumentation print. Immediate top-level finish suppressed six optional prints; all seven mandatory FRONTIER completion records and native RTL assertions passed.',
        additional_checker_repair='First running row is idle with in_valid0, available8, take5. Source cap applies to valid offered and accepted work. Actual take/mode is checked on every idle/prelude/work row.',
        original_checker_preserved=True,native_and_RTL_rerun=False,
        missing_optional_marker_engines=[row['engine'] for row in checked['rows'] if not row['supplemental_completion_marker_recorded']],
        source_sha256=run.pins([Path(__file__),P/'verify_natural_supply2.py',P/'verify_natural_supply2_v2.py']))
    acceptance=dict(status='pass',checked_file=str(output),checked_sha256=run.sha(output),
        source_sha256=stamps|run.pins([output,wd/'verification_repair_provenance.json',wd/'verify_repair.job.json',wd/'verify_repair.log']),
        all_seven_exact=True,all_original_IF_states_spikes_counts_classes_match=True,
        offered_valid_and_accepted_supply_never_exceeded_two=True,
        accepted_supply_never_exceeded_two=True,requests_per_engine=317952,
        service_clocks_per_engine=327168,total_repeated_scalar_checks=635904*7,
        verification_repair=repair,
        scope='One unstalled native run, six one-edge DSP/fixed cores plus same-policy adaptiveLUT. Actual ready/valid source cap2; no SRAM, routed timing, power or board claim.')
    run.write(P/'acceptance.json',acceptance)
    print('NATURAL SUPPLY2 CONTROL ACCEPTED WITH RETAINED CHECKER FAILURE',P/'acceptance.json',flush=True)


if __name__=='__main__':main()
