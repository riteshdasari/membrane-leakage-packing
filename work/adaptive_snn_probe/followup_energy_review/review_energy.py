"""Independent read-only energy-chain review; writes only this review folder.

No native simulator, synthesis, routing or power tool is launched. Existing
strict auditor is independently re-run; its versioned fixture metadata repair
is checked without changing executed source or numerical evidence.
"""
from pathlib import Path
from collections import deque
import argparse
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
E=P.parent/'natural_energy_trial'
R=E/'results'


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()


def read(path):return json.loads(Path(path).read_text())


def trace_review(row,engine):
    path=Path(row['trace_file']);assert sha(path)==row['trace_sha256']
    cols=['idx','running','done','rst','iv','orr','av','U','I','ir','take','ov','count','data','mode','advance','accepted','retired']
    total=valid=invalid=accepted=retired=neurons=known_data=0
    queue=deque();advance=0;first=last=None
    for index,line in enumerate(path.open()):
        tokens=line.split();assert len(tokens)==18
        # Integer parsing itself demands fully known data on every native row,
        # including invalid rows; no replay output can use an unknown-data skip.
        values={key:int(value,16 if key in ('U','I','data') else 10)for key,value in zip(cols,tokens)}
        assert values['idx']==index and values['done']==0
        assert 0<=values['U']<2**88 and 0<=values['I']<2**88 and 0<=values['data']<2**96
        for key in ('running','done','rst','iv','orr','ir','ov','mode','advance','accepted','retired'):assert values[key] in (0,1)
        total+=1;known_data+=1;valid+=values['ov'];invalid+=1-values['ov']
        assert values['ir']==values['advance']==int(not(values['ov'] and not values['orr']))
        assert values['accepted']==int(not values['rst'] and values['iv'] and values['ir'] and values['av']!=0)
        assert values['retired']==int(not values['rst'] and values['ov'] and values['orr'])
        av=values['av'];assert 0<=av<=8
        legal=av
        if engine in (0,4):
            legal=min(av,5)
            while legal<av:
                raw=(values['U']>>(11*legal))&2047
                u=raw-2048 if raw>=1024 else raw
                if not -128<=u<=127:break
                legal+=1
        assert values['take']==legal and values['mode']==int(engine in (0,4) and legal>5)
        if not values['running']:continue
        assert values['rst']==0 and values['orr']==1
        if values['accepted']:
            count=values['take'];expected=0
            assert 1<=count<=av
            for lane in range(count):
                u=(values['U']>>(11*lane))&2047;i=(values['I']>>(11*lane))&2047
                u=u-2048 if u>=1024 else u;i=i-2048 if i>=1024 else i
                assert -128<=i<=127
                expected|=((u+i)&4095)<<(12*lane)
            queue.append((count,expected,advance));accepted+=1;neurons+=count
            if first is None:first=index
        if values['retired']:
            assert queue
            count,expected,issued=queue.popleft()
            assert values['count']==count and values['data']==expected and advance-issued==1
            retired+=1;last=index
        advance+=values['advance']
    assert not queue and total==row['trace_count'] and known_data==total
    assert accepted==retired==row['requests'] and neurons==row['neurons']==635904
    assert (first,last)==(row['first_accept_trace_index'],row['last_retire_trace_index'])
    assert last-first+1==row['service_clocks']
    return dict(engine=engine,trace_file=str(path),trace_sha256=sha(path),rows=total,
        known_data_rows=known_data,valid_rows=valid,invalid_rows=invalid,
        accepted_requests=accepted,retired_requests=retired,scalar_checks=neurons,
        first_accept=first,last_retire=last,service_clocks=last-first+1,
        idle_prelude_actual_take_checked=True,exact_U11_I8_sum_and_zero_tails_checked=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists(),'Preserve review attempts'
    assert args.output.resolve().parent==P.resolve(),'Write only this new review folder'
    old_auditor=(E/'audit_power.py').read_text()
    new_auditor=(E/'audit_power_v2.py').read_text()
    assert old_auditor.count('fixture_FF=338')==1 and old_auditor.count('common 338-FF')==1
    assert new_auditor==old_auditor.replace('fixture_FF=338','fixture_FF=290').replace('common 338-FF','common 290-FF')
    spec=importlib.util.spec_from_file_location('followup_strict_energy_audit_v2',E/'audit_power_v2.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    requirements={}
    record_files=[]
    def stamp(path,digest):
        key=str(Path(path).resolve());requirements.setdefault(key,set()).add(digest)
    def scan(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if isinstance(key,str) and re.match(r'^[A-Za-z]:[\\/]',key) and isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item):stamp(key,item)
                else:scan(item)
        elif isinstance(value,list):
            for item in value:scan(item)
    def load(path):
        path=Path(path).resolve();stamp(path,sha(path));record_files.append(str(path));data=read(path);scan(data);return data
    prep=load(E/'source_preparation.json')
    completion=load(E/'completion_progress.json')
    assert completion['status']=='completed_with_retained_failures'
    initial_repair=load(E/'repair_completion.json')
    v2=load(E/'repair_v2_completion.json')
    repair_prep=load(E/'repair_v2_preparation.json')
    assert v2['status']=='completed_with_retained_failures'
    assert {row['engine']for row in v2['accepted']}=={2,3,4}
    assert {row['engine']for row in v2['failures']}=={0,1}
    assert initial_repair['failures'][0]['engine']==0 and 'Changed evidence' in initial_repair['failures'][0]['reason']
    assert v2['retained_prior_attempt_sha256']==sha(E/'repair_completion.json')
    assert not repair_prep['gates_changed'] and v2['no_timing_gate_waiver']
    restored=repair_prep['source_restoration']
    assert sha(restored['path'])==restored['expected_and_restored_sha256']=='390c6cb743299d9bb7b695582e644d5c5754996f52542396524851218312a160'
    stamp(E/'audit_power.py',repair_prep['original_auditor_sha256'])
    stamp(E/'audit_power_v2.py',repair_prep['new_auditor_sha256'])
    load(E/'repair_v2_preparation.json')
    power_audits={row['engine']:Path(row['audit_file'])for row in v2['accepted']}
    for row in v2['accepted']:stamp(row['audit_file'],row['audit_sha256'])
    power_audits[0]=R/'power_e0_a0/power_audit_v2.json'
    traces=load(R/'native_trace_a0/trace_checks.json')
    assert traces['status']=='pass' and len(traces['rows'])==5
    trace_rows=[trace_review(row,engine)for engine,row in enumerate(traces['rows'])]
    tb=(E/'tb_replay.sv').read_text()
    assert 'got[106:101]!==expected[slot][106:101]' in tb
    assert 'got[100:97]!==expected[slot][100:97]' in tb
    assert 'got[0]!==expected[slot][0]' in tb
    assert 'known[slot][0] && got[96:1]!==expected[slot][96:1]' in tb
    assert '!$isunknown(data0)' in tb and 'if(n>=2)compare_row((n-2)%4)' in tb
    engines=[]
    for engine in range(5):
        wd=R/f'replay_e{engine}_a0'
        provenance=load(wd/'provenance.json')
        jobs=[]
        for number in range(4):
            job=load(wd/f'tool_{number}.job.json');assert job['returncode']==0
            assert job['source_sha256']==provenance
            stamp(wd/f'tool_{number}.log',job['log_sha256']);jobs.append(job)
        log=(wd/'tool_3.log').read_text()
        marker=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',log)
        fatals=re.findall(r'Fatal: ([^\n]+)',log)
        if engine==1:
            assert fatals and marker is None and not(wd/'replay_checks.json').exists()
            assert any('REPLAY data mismatch V1 row17' in failure for failure in fatals)
            engines.append(dict(engine=engine,status='timed_functional_failure',accepted_energy=False,
                fatal_messages=fatals,log_file=str(wd/'tool_3.log'),log_sha256=sha(wd/'tool_3.log'),
                retained_even_if_Tcl_prints_SAIF_close=True))
            continue
        assert marker and not fatals
        reviewed=trace_rows[engine]
        assert tuple(map(int,marker.groups()[:4]))==(engine,reviewed['rows'],reviewed['rows'],reviewed['valid_rows'])
        replay_file=wd/'replay_checks.json';record=load(replay_file)
        assert record['postprocessing_repair']['original_failure']['stage']=='replay'
        assert 'has no attribute' in record['postprocessing_repair']['original_failure']['reason']
        assert record['source_sha256'].items()>=provenance.items()
        interval=audit.replay(wd)
        assert interval['duration_ps']==(reviewed['service_clocks']+2)*6000
        assert interval['scalar_updates']==635904
        stored_file=power_audits[engine]
        powerdir=stored_file.parent
        # Existing accepted results are rerun through every strict interval and
        # physical alias gate, rather than trusting PASS strings.
        assert stored_file.exists(),('Wait for completed audited power',engine)
        stored=load(stored_file);load(powerdir/'evidence.json');load(powerdir/'provenance.json')
        current=audit.annotation(powerdir);assert current==stored
        hardware=load(Path(stored['routed_hardware_file']))
        assert hardware['slice_accounting']['fixture_FF']==290
        assert hardware['full_fixture']['FF']-hardware['core']['FF']==290
        assert current['fixture_FF']==290
        # Independently recalculate numeric energy from serialized rail currents
        # and exact elapsed SAIF interval, with static current excluded.
        dyn=sum(float(source['voltage'])*float(source['icc'])for source in current['voltage_sources'])
        energy=dyn*interval['duration_ps']/635904
        assert dyn==current['dynamic_power_W'] and energy==current['estimated_dynamic_energy_pJ_per_scalar_update']
        for path in powerdir.glob('*.job.json'):
            job=load(path);assert job['returncode']==0
            stamp(powerdir/f"{path.name.removesuffix('.job.json')}.log",job['log_sha256'])
        normalization=load(wd/'activity_named.names.json')
        stamp(wd/'activity.saif',normalization['source_sha256'])
        stamp(wd/'activity_named.saif',normalization['target_sha256'])
        engines.append(dict(engine=engine,status='strict_replay_and_physical_power_pass',accepted_energy=True,
            replay_rows_checked=reviewed['rows'],valid_rows_checked=reviewed['valid_rows'],
            invalid_rows_checked=reviewed['invalid_rows'],duration_ps=interval['duration_ps'],
            scalar_updates=635904,strict_physical_activity_mapping=current['matched_physical_design_nets'],
            physical_activity_unknown_records=current['physical_activity_unknown_records'],
            dynamic_power_W=dyn,estimated_dynamic_energy_pJ_per_scalar_update=energy,
            hardware_fixture_FF=290,reported_auditor_fixture_FF=290,
            fixture_metadata_correction='Versioned auditor source changes only two returned metadata fields, 338 to290; all strict gates and numerical calculations are byte-identical.',
            power_audit_file=str(stored_file),power_audit_sha256=sha(stored_file)))
    for path in E.glob('*completion*.json'):load(path)
    for path in E.glob('*provenance*.json'):load(path)
    for path in E.glob('*source*restor*.json'):load(path)
    # Recursively include all referenced JSON source/artifact maps. This covers
    # original native acceptance, route, export and immutable tool producers,
    # rather than closing only the immediate power records.
    inspected=set(record_files)
    while True:
        candidates=[path for path in requirements if path.lower().endswith('.json') and path not in inspected]
        if not candidates:break
        for path in candidates:
            inspected.add(path);load(path)
    failures=[];bytes_checked=0
    for path,digests in requirements.items():
        actual=sha(path);bytes_checked+=Path(path).stat().st_size
        if len(digests)!=1 or actual not in digests:failures.append(dict(file=path,expected=sorted(digests),actual=actual))
    assert not failures,failures
    result=dict(status='consolidated_energy_acceptance_pass_with_retained_failures',
        engines=engines,native_trace_rows=trace_rows,pinned_files=len(requirements),pinned_bytes=bytes_checked,
        recorded_pins={path:next(iter(digests))for path,digests in requirements.items()},
        retained_records=sorted(set(record_files)),reviewer_script_sha256=sha(__file__),
        accepted_energy_engines=[row['engine']for row in engines if row['accepted_energy']],
        rejected_energy_engines=[row['engine']for row in engines if not row['accepted_energy']],
        native_scalar_checks=sum(row['scalar_checks']for row in trace_rows),
        accepted_full_replay_rows_checked=sum(row.get('replay_rows_checked',0)for row in engines),
        retained_attempts=[dict(file=str(E/'completion_progress.json'),sha256=sha(E/'completion_progress.json'),failures=completion['failures']),
            dict(file=str(E/'repair_completion.json'),sha256=sha(E/'repair_completion.json'),failures=initial_repair['failures']),
            dict(file=str(E/'repair_v2_completion.json'),sha256=sha(E/'repair_v2_completion.json'),failures=v2['failures'])],
        E0_acceptance_recovery='Separately closed via complete_e0_report_record.py after exact source restoration; initial changed-evidence failure and V2 missing-record failure remain retained.',
        fixture_auditor_repair=dict(original_sha256=sha(E/'audit_power.py'),version2_sha256=sha(E/'audit_power_v2.py'),
            exact_source_delta='Two returned metadata fields only: fixture_FF338→290 and common338-FF→290-FF scope text',strict_gates_changed=False),
        all_native_data_known_including_invalid_rows=True,
        source_restoration_scope='Exact pinned runner bytes must match before acceptance; every present completion/source pin rehashed. No source gate waiver.',
        scope='Unstalled original shift3 integerLIF post-leak U+I trace; strict one-edge full routed replay and vendor fixture dynamic estimate. No core-only/board energy, whole-neuron, full accelerator or trained-accuracy improvement claim.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('FOLLOWUP ENERGY INDEPENDENT REVIEW PASS',result['accepted_energy_engines'],result['pinned_files'],flush=True)


if __name__=='__main__':main()
