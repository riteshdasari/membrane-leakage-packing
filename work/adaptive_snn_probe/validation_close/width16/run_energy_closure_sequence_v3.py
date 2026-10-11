"""Serial fixed16 closure; reuse verified E7 prefix and cached original E8 outputs.

New attempts retain all old source/evidence files. --validate-only performs only
read-only source/receipt checks and never launches a vendor tool or model.
"""
from pathlib import Path
import argparse, copy, importlib.util, math, re, subprocess, sys, time
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ALT = P / 'lutceil_e7'
ABL = P / 'static9_e8'
ROOT = P.parent.parent
sys.path.insert(0, str(ROOT / 'selective_energy_trial'))
import run_selective_energy as b
RECEIPTS = []
E7_PREFIX = ('E7_general_s0', 'E7_general_s1', 'E7_actual_glif_s0', 'E7_route12')


def accepted(path, status='pass'):
    path = Path(path).resolve()
    d = b.read(path)
    assert d['status'] == status, (str(path), d['status'])
    b.verify(d.get('source_sha256', {}))
    b.verify(d.get('artifact_sha256', {}))
    RECEIPTS.append(dict(path=str(path), sha256=b.sha(path), status=status))
    return d


def template(directory, engine):
    directory = Path(directory)
    name = re.sub(rf'e{engine}(?=_)', 'e{engine}', directory.name)
    assert '{engine}' in name
    return str(directory.parent / name)


def e7_native_gate(path, cohort, stall, capture):
    path = Path(path).resolve()
    assert path.is_relative_to(ALT / 'hardware')
    d = accepted(path)
    assert (d['B'], d['cohort'], d['stall'], d['capture']) == (16, cohort, stall, capture)
    assert [(r['native_index'], r['engine']) for r in d['rows']] == [(i, 7 if i == 6 else i) for i in range(7)]
    domainfile = P / 'domain_acceptance_glif_v2.json'
    domain = b.read(domainfile)
    assert domain['arithmetic_mismatches'] == 0
    b.verify(domain['source_sha256'])
    co = domain['cohorts'][cohort]
    b.verify(co['artifact_sha256'])
    assert d['source_sha256'][str(domainfile)] == b.sha(domainfile)
    expected = co['expected_requests_by_engine'][:6] + [co['expected_requests_by_engine'][2]]
    for row, requests in zip(d['rows'], expected):
        assert row['requests'] == row['retirements'] == requests and row['neurons'] == co['operations']
        assert row['min_latency'] >= 2
        if stall == 0:
            assert row['min_latency'] == row['max_latency'] == 2 and row['service_clocks'] == requests + 2
        if capture:
            trace = path.parent / f"trace{row['native_index']}.txt"
            assert d['artifact_sha256'][str(trace)] == b.sha(trace)
    return d


def e7_route_gate(path, native):
    path, native = Path(path).resolve(), Path(native).resolve()
    assert path.is_relative_to(ALT / 'hardware')
    d = accepted(path)
    assert (d['B'], d['engine'], d['clock_period_ns'], d['top']) == (16, 7, 12, 'top_sequential_leak16_lutceil_e7')
    assert d['part'] == 'xc7a100tcsg324-1' and d['latency_advancing_edges'] == 2
    a = d['slice_accounting']
    assert (a['launch_FF'], a['capture_FF'], a['fixture_FF']) == (55, 39, 94)
    assert d['fixture_FF'] == d['full_fixture']['FF'] - d['core']['FF'] == 94
    assert d['full_fixture']['LUT'] == d['core']['LUT'] and d['full_fixture']['DSP'] == d['core']['DSP'] == 0
    assert all(math.isfinite(d[k]) and d[k] >= 0 for k in ('WNS_ns', 'WHS_ns', 'boundary_WNS_ns', 'boundary_WHS_ns'))
    assert d['source_sha256'][str(native)] == b.sha(native)
    assert d['artifact_sha256'][str(path.parent / 'design.dcp')] == b.sha(path.parent / 'design.dcp')
    return d


def resume_prefix(sequencefile, routefile):
    """Verify old global pins, every recorded log/gate, then semantic E7 gates."""
    sequencefile, routefile = Path(sequencefile).resolve(), Path(routefile).resolve()
    old = b.read(sequencefile)
    assert old['B'] == 16 and Path(old['route_acceptance']).resolve() == routefile
    assert old['source_sha256'][str(routefile)] == b.sha(routefile)
    b.verify(old['source_sha256'])
    b.verify(old.get('artifact_sha256', {}))
    assert len(old['steps']) >= 4 and tuple(s['label'] for s in old['steps'][:4]) == E7_PREFIX
    origins = [sequencefile]
    for step in old['steps']:
        if 'log_file' in step:
            log = Path(step['log_file']).resolve()
            assert b.sha(log) == step['log_sha256']
            origins.append(log)
        for gate in step.get('acceptance_gates', []):
            path = Path(gate['path']).resolve()
            assert b.sha(path) == gate['sha256']
            accepted(path, gate['status'])
            origins.append(path)
    paths = {}
    for step in old['steps'][:4]:
        assert step['status'] == 'accepted_stage_gate' and step['returncode'] == 0
        assert len(step['acceptance_gates']) == 1 and step['acceptance_gates'][0]['status'] == 'pass'
        paths[step['label']] = Path(step['acceptance_gates'][0]['path']).resolve()
    e7_native_gate(paths[E7_PREFIX[0]], 'general', 0, 0)
    e7_native_gate(paths[E7_PREFIX[1]], 'general', 1, 0)
    e7_native_gate(paths[E7_PREFIX[2]], 'actual_glif', 0, 1)
    e7_route_gate(paths[E7_PREFIX[3]], paths[E7_PREFIX[0]])
    original_sha = b.sha(sequencefile)
    reused = []
    for original in old['steps'][:4]:
        step = copy.deepcopy(original)
        step.update(reused_from_sequence=True, reused_sequence_file=str(sequencefile),
                    reused_sequence_sha256=original_sha, vendor_jobs_rerun=False,
                    original_record=copy.deepcopy(original))
        reused.append(step)
    return old, reused, paths, b.pins(origins)


def e8_native_gate(path, cohort, stall, capture=0, imported=False):
    path = Path(path).resolve()
    assert path.is_relative_to(ABL / 'hardware')
    d = accepted(path)
    assert (d['B'], d['legal_state_signed_bits'], d['cohort'], d['stall'], d['capture']) == (16, 9, cohort, stall, capture)
    assert [(r['native_index'], r['engine']) for r in d['rows']] == [(0, 5), (1, 8)]
    if imported:
        importer = ABL / 'import_completed_native_cached.py'
        original = ABL / 'run_native_static9.py'
        assert d['producer_runner_file'] == str(original) and d['producer_runner_sha256'] == b.sha(original)
        assert d['postprocess_auditor_file'] == str(importer) and d['source_sha256'][str(importer)] == b.sha(importer)
        assert d['cached_array_loads'] == 4 and path.name.startswith('acceptance_cached_')
    # Existing read-only oracle checks every raw output, order, cycle and boundary.
    spec = importlib.util.spec_from_file_location('static9_sequence_native_gate', ABL / 'audit_closure_static9.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    prep, scalar = b.read(ABL / 'preparation.json'), b.read(ABL / 'scalar_cohort.json')
    audit.verify(prep)
    audit.verify(scalar)
    return audit.native(path, cohort, stall, prep, scalar)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--attempt', required=True)
    ap.add_argument('--route-acceptance', required=True)
    ap.add_argument('--resume-sequence')
    ap.add_argument('--pair0-import', help='Explicit cached independent acceptance receipt of completed original E8 pair/s0 outputs.')
    ap.add_argument('--validate-only', action='store_true')
    args = ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+', args.attempt)
    routefile = Path(args.route_acceptance).resolve()
    route = accepted(routefile)
    assert route['B'] == 16 and route['period_ns'] == 12 and set(route['selected_routes']) == set(map(str, range(7)))
    for e, directory in route['selected_routes'].items():
        hw = accepted(Path(directory) / 'hardware.json')
        assert hw['engine'] == int(e) and hw['B'] == 16 and hw['clock_period_ns'] == 12
    old, reused, oldpaths, originpins = {}, [], {}, {}
    if args.resume_sequence:
        old, reused, oldpaths, originpins = resume_prefix(args.resume_sequence, routefile)
    pair0 = Path(args.pair0_import).resolve() if args.pair0_import else None
    if pair0:
        assert args.resume_sequence, 'A completed-original import requires its explicit original sequence snapshot.'
        e8_native_gate(pair0, 'pair', 0, imported=True)
        imported = b.read(pair0)
        original_runner = str(ABL / 'run_native_static9.py')
        assert imported['producer_runner_sha256'] == old['source_sha256'][original_runner]
        # Require the actual native payload and supplemental launch sources. E7
        # scripts/driver pins are separately verified context, not native payload.
        native_sources = [ABL/'run_native_static9.py', P/'leak_core16.sv',
                          ABL/'leak_core_static9.sv', ABL/'leak_dsp.sv', ABL/'tb_static9.sv',
                          ROOT/'selective_energy_trial/run_selective_energy.py', b.VIVADO/'data/verilog/src/glbl.v']
        for source in native_sources:
            filename = str(source.resolve())
            assert imported['source_sha256'][filename] == b.sha(source)
        for filename in imported['source_sha256'].keys() & old['source_sha256'].keys():
            assert imported['source_sha256'][filename] == old['source_sha256'][filename]
        originpins |= b.pins([pair0])
    scripts = [ALT / 'run_native16_lutceil_v2.py', ALT / 'run_route16_lutceil.py',
               ABL / 'run_native_static9_v2.py', ABL / 'run_route_static9.py',
               ABL / 'audit_closure_static9.py', ABL / 'import_completed_native_cached.py',
               P / 'run_energy16_12.py', ALT / 'run_energy16_lutceil_12.py', P / 'aggregate_hardwareclosure.py']
    stamps = b.pins([Path(__file__), P / 'run_energy_closure_sequence_v2.py', routefile,
                     ROOT / 'selective_energy_trial/run_selective_energy.py', b.VIVADO / 'data/verilog/src/glbl.v', *scripts]) | originpins
    progress = P / f'energy_closure_sequence_{args.attempt}.json'
    assert not progress.exists(), 'Use a fresh attempt label; retain the prior sequence.'
    if args.validate_only:
        b.verify(stamps)
        print('ENERGY CLOSURE V3 READ-ONLY VALIDATION PASS', dict(attempt=args.attempt,
              reused_E7_stages=list(oldpaths), pair0_import=str(pair0) if pair0 else None,
              future_progress_file=str(progress), vendor_jobs_launched=False), flush=True)
        return
    state = dict(status='running', B=16, steps=reused, failures=[], source_sha256=stamps,
                 route_acceptance=str(routefile), resume_sequence_file=str(Path(args.resume_sequence).resolve()) if args.resume_sequence else None,
                 resume_sequence_sha256=b.sha(args.resume_sequence) if args.resume_sequence else None,
                 prior_state_at_resume=old.get('status'), retained_prior_tail=copy.deepcopy(old.get('steps', [])[4:]),
                 retained_prior_failures=copy.deepcopy(old.get('failures', [])), pair0_import=str(pair0) if pair0 else None)
    success = {s['label']: True for s in reused}
    attempt = args.attempt

    def run(label, script, argv, gate, dependencies=()):
        b.verify(stamps)
        state['current_stage'] = label
        b.write(progress, state)
        if any(not success.get(dep, False) for dep in dependencies):
            record = dict(label=label, status='skipped_failed_prerequisite', dependencies=list(dependencies))
            success[label] = False
            state['steps'].append(record)
            state['failures'].append(record)
            b.write(progress, state)
            return False
        log = P / f'energy_closure_{label}_{attempt}.log'
        assert not log.exists()
        start = time.time()
        with log.open('w', encoding='utf-8') as stream:
            rc = subprocess.run([sys.executable, '-B', str(script), *argv], cwd=P, stdout=stream, stderr=subprocess.STDOUT).returncode
        record = dict(label=label, returncode=rc, seconds=time.time()-start, log_file=str(log), log_sha256=b.sha(log))
        receipt_start = len(RECEIPTS)
        try:
            assert rc == 0, ('child returncode', rc)
            gate()
            b.verify(stamps)
            record['status'] = 'accepted_stage_gate'
            success[label] = True
        except Exception as exc:
            record['status'] = 'retained_stage_failure'
            record['reason'] = repr(exc)
            success[label] = False
            state['failures'].append(record)
            print(log.read_text(errors='replace')[-2200:], flush=True)
        record['acceptance_gates'] = RECEIPTS[receipt_start:]
        state['steps'].append(record)
        b.write(progress, state)
        print('ENERGY CLOSURE STEP', label, record['status'], 'seconds', round(record['seconds'], 1), flush=True)
        return success[label]

    e7native, e8native = {}, {}
    for cohort, stall, capture in [('general',0,0), ('general',1,0), ('actual_glif',0,1)]:
        label = f'E7_{cohort}_s{stall}'
        if label in oldpaths:
            e7native[label] = oldpaths[label]
            continue
        name = f'native_{cohort}_s{stall}_{attempt}'
        out = ALT / 'hardware' / name / 'acceptance.json'
        e7native[label] = out
        run(label, ALT / 'run_native16_lutceil_v2.py', ['--cohort',cohort,'--stall',str(stall),'--capture',str(capture),'--attempt',name],
            lambda out=out,cohort=cohort,stall=stall,capture=capture:e7_native_gate(out,cohort,stall,capture))

    def routed_ablation(root, engine, script, native, label, dependencies):
        directory = root / 'hardware' / f'route12_e{engine}_{attempt}'
        ok = run(label, script, ['--native-acceptance',str(native),'--attempt',attempt], lambda:accepted(directory/'hardware.json'), dependencies)
        if (not ok and directory.exists() and (directory/'synth/design.dcp').exists() and (directory/'route.log').exists()
            and 'ERROR: [Synth 20-411]' in (directory/'route.log').read_text(errors='replace') and all(success.get(dep,False) for dep in dependencies)):
            retry, olddirectory = attempt+'_checkpoint', directory
            directory = root / 'hardware' / f'route12_e{engine}_{retry}'
            ok = run(label+'_checkpoint', script, ['--native-acceptance',str(native),'--attempt',retry,'--resume-synth-from',str(olddirectory)],
                     lambda:accepted(directory/'hardware.json'), dependencies)
            success[label] = ok
        return directory, ok

    if 'E7_route12' in oldpaths:
        e7route, e7ok = oldpaths['E7_route12'].parent, True
    else:
        e7route, e7ok = routed_ablation(ALT,7,ALT/'run_route16_lutceil.py',e7native['E7_general_s0'],'E7_route12',('E7_general_s0','E7_general_s1'))
    for cohort in ('pair','scalar'):
        for stall in (0,1):
            label = f'E8_{cohort}_s{stall}'
            if cohort == 'pair' and stall == 0 and pair0:
                e8native[label] = pair0
                start, receipt_start = time.time(), len(RECEIPTS)
                audit = e8_native_gate(pair0,'pair',0,imported=True)
                b.verify(stamps)
                state['steps'].append(dict(label=label,status='accepted_stage_gate',seconds=time.time()-start,
                    reused_cached_native=True,vendor_jobs_rerun=False,imported_acceptance_file=str(pair0),imported_acceptance_sha256=b.sha(pair0),
                    independent_native_gate=audit,acceptance_gates=RECEIPTS[receipt_start:]))
                success[label] = True
                b.write(progress,state)
                continue
            name = f'native_{cohort}_s{stall}_{attempt}'
            out = ABL / 'hardware' / name / 'acceptance.json'
            e8native[label] = out
            run(label,ABL/'run_native_static9_v2.py',['--cohort',cohort,'--stall',str(stall),'--capture','0','--attempt',name],
                lambda out=out,cohort=cohort,stall=stall:e8_native_gate(out,cohort,stall))
    e8route,e8ok = routed_ablation(ABL,8,ABL/'run_route_static9.py',e8native['E8_pair_s0'],'E8_route12',tuple(e8native))

    def energy(workload,engine,root,script,native,directory,dependencies=()):
        tag, label = f'{attempt}_e{engine}', f'{workload.upper()}_energy_e{engine}'
        prog = root / f'energy12_{workload}_{tag}_golden_export_replay_power_progress.json'
        auditfile = root / 'hardware' / f'power12_{workload}_e{engine}_{tag}' / 'power_audit.json'
        def gate():
            d = accepted(prog)
            assert not d['failures'] and d['engines'] == [engine]
            a = accepted(auditfile)
            assert a['engine'] == engine and a['clock_period_ns'] == 12 and a['fixture_FF'] == 94 and a['physical_activity_unknown_records'] == 0
        return run(label,script,['--workload',workload,'--native-acceptance',str(native),'--route-dir-template',template(directory,engine),
                   '--engines',str(engine),'--attempt',tag],gate,dependencies)

    for e in (5,1,2,0,3,4):
        energy('glif',e,P,P/'run_energy16_12.py',P/'hardware/native_actual_glif_s0_a0/acceptance.json',route['selected_routes'][str(e)])
    energy('glif',7,ALT,ALT/'run_energy16_lutceil_12.py',e7native['E7_actual_glif_s0'],e7route,('E7_actual_glif_s0','E7_route12'))
    for e in (5,1,2,6,0,3,4):
        energy('ottt',e,P,P/'run_energy16_12.py',P/'hardware/native_actual128_s0_a0/acceptance.json',route['selected_routes'][str(e)])
    aggregatefile = P / f'hardwareclosure_measured_{attempt}.json'
    run('aggregate',P/'aggregate_hardwareclosure.py',['--label','measured_'+attempt,'--strict-complete'],
        lambda:accepted(aggregatefile,'pass_complete_fixed16_hardware_closure'))
    state['status'] = 'completed_with_retained_failures' if state['failures'] else 'pass'
    state['E8_complete'] = e8ok and all(success.get(k,False) for k in e8native)
    state['E8_native_acceptance'] = {k:str(v) for k,v in e8native.items()}
    state['E8_hardware_file'] = str(e8route/'hardware.json')
    state['artifact_sha256'] = b.pins([Path(item['log_file']) for item in state['steps'] if 'log_file' in item])
    b.verify(stamps)
    b.write(progress,state)


if __name__ == '__main__':
    main()
