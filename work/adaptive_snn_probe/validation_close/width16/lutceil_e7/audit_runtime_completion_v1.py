"""Read-only audit of the formerly slow E7 replay, not an energy acceptance."""
from pathlib import Path
import hashlib
import json
import re

P=Path(__file__).resolve().parent
W=P/'hardware/replay12_glif_e7_profiled_all_a0_e7'
OUT=P/'runtime_inspection_a0'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    target=OUT/'completion_audit_v1.json'
    assert not target.exists() and not (OUT/'completion_audit_v1.md').exists()
    provenance_path=W/'provenance.json'
    provenance=json.loads(provenance_path.read_text())
    assert all(sha(path)==pin for path,pin in provenance.items())
    jobs=[];logs=[]
    for i in range(4):
        job_path=W/f'tool_{i}.job.json';log_path=W/f'tool_{i}.log'
        job=json.loads(job_path.read_text())
        assert Path(job['cwd']).resolve()==W.resolve() and job['returncode']==0
        profile=W/f'tool_{i}.memory_profile.json'
        assert job['source_sha256']=={**provenance,str(profile.resolve()):sha(profile)}
        assert job['log_sha256']==sha(log_path)
        assert not any(value in job['argv'] for value in ['-notimingchecks','-nospecify','-sdfnowarn','-sdfnoerror'])
        jobs.append(job);logs.append(log_path.read_text())
    assert not any(re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation',text) for text in logs)
    argv=jobs[2]['argv']
    assert '-maxdelay' in argv and '-transport_int_delays' in argv
    for key in ['-pulse_r','-pulse_int_r','-pulse_e','-pulse_int_e']:
        assert argv.count(key)==1 and argv[argv.index(key)+1]=='0'
    annotations=[line for line in logs[2].splitlines() if 'SDF backannotation was successful' in line]
    assert len(annotations)==1 and '/export12_glif_e7_profiled_all_a0_e7/routed.sdf' in annotations[0]
    assert 'root module "tb_sequential_energy_replay16/dut"' in annotations[0]
    replay=re.findall(r'^FRONTIER_ROUTE_REPLAY PASS E7 ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)$',logs[3],re.M)
    assert len(replay)==1 and tuple(map(int,replay[0][:3]))==(262533,262533,131328)
    close=re.findall(r'^FRONTIER_SAIF_CLOSED START_PS (\d+) END_PS (\d+) DURATION_PS (\d+)$',logs[3],re.M)
    assert len(close)==1 and tuple(map(int,close[0]))==(167999,1576151999,1575984000)
    cpu=re.findall(r'Simulation Memory Usage: (\d+) KB \(Peak: (\d+) KB\), Simulation CPU Usage: (\d+) ms',logs[3])
    assert len(cpu)==1
    saif=W/'activity.saif'
    assert saif.stat().st_size>0
    before=json.loads((OUT/'snapshot_1.json').read_text())
    after=json.loads((OUT/'snapshot_2.json').read_text())
    assert before['job_receipt_present'] is False and after['job_receipt_present'] is True
    assert after['processes'] is None and before['processes']
    assert any('FRONTIER_ROUTE_REPLAY PASS' in line for line in after['last_log_lines'])
    monitor=P/'tb_energy16_12.sv'
    text=monitor.read_text()
    assert 'checked!=rows' in text and 'if(got!==expected[slot])' in text
    displays=re.findall(r'\$display\("([^\"]*)',text)
    assert displays==['REPLAY ROI_START V%0d TIME_NS %0.3f ROW %0d',
                       'FRONTIER_ROUTE_REPLAY PASS E%0d ROWS %0d CHECKED %0d VALID_ROWS %0d TIME_NS %0.3f']
    record=dict(status='pass_completed_slow_E7_timing_replay_and_SAIF_close_runtime_audit',
      full_original_rows_checked=262533,valid_rows=131328,final_simulation_time_ns=replay[0][3],
      saif_start_ps=167999,saif_end_ps=1576151999,saif_duration_ps=1575984000,
      saif_bytes=saif.stat().st_size,wall_seconds=jobs[3]['seconds'],
      kernel_cpu_seconds=int(cpu[0][2])/1000,kernel_peak_memory_KB=int(cpu[0][1]),
      sampled_peak_tool_tree_RSS_sum_GiB=jobs[3]['sampled_peak_tool_tree_RSS_sum_GiB'],
      sampled_min_free_GiB=jobs[3]['sampled_min_free_GiB'],
      source_hash_count=len(provenance),all_source_receipt_log_hashes_verified=True,
      annotation_success_verified=True,timing_checks_waived=False,
      observer_performed_process_control=False,vendor_tools_launched_by_observer=False,
      event_livelock_established=False,
      bounded_conclusion='The long E7 simulation finished normally and checked every known row. CPU activity during the run alone did not prove simulated-time progress; the completed full replay and exact SAIF closure now establish completion.',
      progress_limit='The frozen monitor emits only ROI start and final replay pass. Its buffered running artifacts supplied no verified intermediate row or simulation-time progress. No proprietary WDB content or debugger API was inferred.',
      hardware_or_energy_acceptance=False,
      remaining_gate='SAIF normalization, complete physical annotation, power report and energy audit remain separate requirements.',
      memory_limit='One-second descendant RSS sums may double-count shared pages and miss short peaks. The xsim gate was an empirical launch reserve, not a peak memory bound.',
      artifact_sha256={str(path.resolve()):sha(path) for path in [Path(__file__),provenance_path,monitor,
          OUT/'snapshot_1.json',OUT/'snapshot_2.json',W/'activity.tcl',saif,
          *[W/f'tool_{i}.{ext}' for i in range(4) for ext in ['job.json','log']]]})
    target.write_text(json.dumps(record,indent=2)+'\n')
    (OUT/'completion_audit_v1.md').write_text(
      'E7 completed its full delayed replay normally:262,533 rows checked,131,328 valid rows, final simulation time3,150,542ns. The exact SAIF interval closed at1,576,151,999ps with duration1,575,984,000ps, producing10,347,652bytes. The source, receipt and completed log hashes pass independent rechecking.\n\n'
      'The job took1,044.63s wall time and reported1,013.859s kernel CPU time, with1,711,424KB peak kernel memory. The one-second descendant RSS sum peaked at1.8423GiB and sampled free RAM reached0.3652GiB; these are empirical process measurements with the stated sampling/shared-page limits.\n\n'
      'Before completion, CPU and memory growth established activity but could not prove simulated-time advancement. The frozen monitor emits only ROI start and final pass; buffered artifacts and proprietary WDB content were not treated as intermediate progress. The completed pass and SAIF close now rule out an unfinished event livelock for this run. No running process was stopped, signaled or reprogrammed.\n\n'
      'This runtime audit does not grant energy acceptance. SAIF normalization, physical activity annotation, power reporting and the final energy audit retain their separate gates.\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='artifact_sha256'},indent=2))


if __name__=='__main__':main()
