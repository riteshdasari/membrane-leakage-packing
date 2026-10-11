"""Read-only exact-interval, physical-SAIF and power audit for frontier engines.

Only --output writes an audit result. No HDL, tool job or frozen evidence is
modified. All energies cover the common 290-FF registered measurement fixture.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
OLD = P.parent / 'selective_energy_trial'
ROOT = 'tb_natural_energy_replay/dut'
SCALARS = 635904
PERIOD_PS = 6000
AUDIT_SHA = 'd4cc05920fb7a2beada60d125bc885b39ad9eefd1a6aac68bb26cc258aa9ddf2'
NORMALIZER_SHA = '81d84539f84354b317e452de0f4ffe3858f4a32afa54baea37416497d1d7ff07'
TRACE_COLUMNS = ['idx','running','done','rst','in_valid','out_ready','available',
    'U','I','in_ready','take','out_valid','out_count','out_data','narrow_mode',
    'advance','accepted_thiscycle','retired_thiscycle']


def load_prior():
    import hashlib
    path = OLD / 'audit_selective_energy.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == AUDIT_SHA
    spec = importlib.util.spec_from_file_location('frontier_frozen_saif_audit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior = load_prior()
read, sha, verify = prior.read, prior.sha, prior.verify


def functional_checks(stamps, engine):
    """Require both the closed six-cohort U11 trial and exact captured replay."""
    assert engine in range(5) and stamps
    verify(stamps)
    original_file, = [Path(n) for n in stamps if Path(n).name == 'native_acceptance.json']
    original = read(original_file)
    assert original['status'] == 'pass' and len(original['cohorts']) == 6
    assert {(c['kind'],c['backpressure']) for c in original['cohorts']} == {
        (kind,stall) for kind in ('main','shift1','shift3') for stall in (False,True)}
    for key in ('source_sha256','artifact_sha256','prerequisites_sha256'):
        verify(original[key])
    for cohort in original['cohorts']:
        assert cohort['status'] == 'pass' and {r['engine'] for r in cohort['rows']} == set(range(5))
        assert all(r['status'] == 'pass' for r in cohort['rows'])
        verify(read(Path(cohort['check_file']).parent/'provenance.json'))
        verify(cohort['source_sha256']);verify(cohort['candidate_file_sha256'])
        if cohort['kind'] == 'main':assert cohort['exhaustive_scalar_pairs'] == 524288
        else:assert all(r['original_LIF_numeric_retirements_match'] for r in cohort['rows'])
    trace_file, = [Path(n) for n in stamps if Path(n).name == 'trace_checks.json']
    trace = read(trace_file)
    assert trace['status'] == 'pass' and trace['kind'] == 'shift3' and trace['backpressure'] is False
    verify(trace['source_sha256']);verify(trace['candidate_file_sha256'])
    assert len(trace['rows']) == 5 and all(r['status'] == 'pass' for r in trace['rows'])
    old, = [c for c in original['cohorts'] if c['kind'] == 'shift3' and not c['backpressure']]
    for a,b in zip(trace['rows'],old['rows']):
        for key in ('engine','requests','service_clocks','neurons','numeric_retirement_sha256','retirement_sha256'):
            assert a[key] == b[key], (key,a['engine'])
        assert a['neurons'] == SCALARS
        assert sha(a['trace_file']) == a['trace_sha256']
    return original['cohorts']


def replay(directory):
    directory = Path(directory).resolve()
    result = read(directory/'replay_checks.json')
    assert result['status'] in ('pass','timing_pass_activity_pending')
    engine = result['engine']
    assert engine in range(5) and result['clock_period_ns'] == 6
    verify(result['source_sha256']); verify(result['artifact_sha256'])
    functional_checks(result['functional_check_sha256'], engine)
    columns = result.get('trace_columns', TRACE_COLUMNS)
    assert columns == TRACE_COLUMNS, ('Unexpected trace schema', columns)
    row = result['native_row']
    native_check_file = Path(result['native_check_file']).resolve()
    assert sha(native_check_file) == result['native_check_sha256']
    assert result['source_sha256'][str(native_check_file)] == sha(native_check_file)
    # The simulated Verilog/SDF must come from the same DCP used for power.
    export_artifacts, = [Path(name) for name in result['source_sha256']
                         if Path(name).name == 'artifacts.json' and Path(name).parent.name.startswith('export_e')]
    exported = read(export_artifacts)
    verify(exported)
    export_provenance = export_artifacts.parent/'provenance.json'
    assert exported[str(export_provenance)] == sha(export_provenance)
    producer = read(export_provenance)
    verify(producer)
    hardware, = [name for name in producer if Path(name).name == 'hardware.json'
                  and read(name).get('top') == result['design_top']]
    dcp = str(Path(hardware).parent/'design.dcp')
    assert dcp in producer and dcp in result['source_sha256']
    assert producer[dcp] == result['source_sha256'][dcp] == sha(dcp)
    assert producer[hardware] == result['source_sha256'][hardware] == sha(hardware)
    for basename in ('routed.v','routed.sdf'):
        path = str(export_artifacts.parent/basename)
        assert exported[path] == result['source_sha256'][path] == sha(path)
    native_check = read(native_check_file)
    actual_row, = [item for item in native_check['rows'] if item['engine'] == engine]
    assert row == actual_row and row['engine'] == engine
    assert native_check['kind'] == 'shift3' and native_check['backpressure'] is False
    assert sha(row['trace_file']) == row['trace_sha256']
    first = last = None
    requests = retired = neurons = retired_neurons = total = 0
    with Path(row['trace_file']).open() as source:
        for index, line in enumerate(source):
            fields = line.split()
            assert len(fields) == len(columns) and int(fields[0]) == index
            values = {key:int(value,16 if key in ('U','I','out_data') else 10)
                      for key,value in zip(columns,fields)}
            total += 1
            assert 0 <= values['available'] <= 8 and 0 <= values['take'] <= 8
            if not values['running']:
                continue
            assert values['rst'] == 0
            accept = bool(values['in_valid'] and values['in_ready'] and values['available'])
            retire = bool(values['out_valid'] and values['out_ready'])
            assert values['accepted_thiscycle'] == accept
            assert values['retired_thiscycle'] == retire
            if accept:
                assert 1 <= values['take'] <= values['available']
                requests += 1; neurons += values['take']
                if first is None:
                    first = index
            if retire:
                assert 1 <= values['out_count'] <= 8
                retired += 1; retired_neurons += values['out_count']; last = index
    assert requests == retired > 0 and neurons == retired_neurons == SCALARS
    assert result['requests'] == requests and result['neurons'] == SCALARS
    assert total == result['replay_rows_checked'] == row['trace_count']
    assert (first,last) == (row['first_accept_trace_index'],row['last_retire_trace_index'])
    assert result['roi_start_ps'] == 126000 + PERIOD_PS*first - 1
    assert result['roi_end_ps'] == 126000 + PERIOD_PS*(last+3) - 1
    assert result['roi_duration_ps'] == PERIOD_PS*(last-first+3)
    assert result['roi_end_ps'] - result['roi_start_ps'] == result['roi_duration_ps']
    assert result['roi_extra_fixture_cycles'] == 2 and result['output_trace_row_offset'] == 2
    logs = [path for path in directory.glob('*.log') if path.is_file()]
    text = '\n'.join(path.read_text(errors='replace') for path in logs)
    assert 'SDF backannotation was successful' in text
    assert f'root module "{ROOT}"' in text
    assert not re.search(r'\b(?:Warning|ERROR|Fatal)\b.*(?:SDF|timing|setup|hold)|Timing violation|\$setuphold|\$recovery|\$recrem|\$width|REPLAY.*mismatch',text,re.I)
    assert f'FRONTIER_ROUTE_REPLAY PASS E{engine}' in text
    marker = f"FRONTIER_SAIF_CLOSED START_PS {result['roi_start_ps']} END_PS {result['roi_end_ps']} DURATION_PS {result['roi_duration_ps']}"
    assert marker in text
    jobs = list(directory.glob('tool_*.job.json'))
    assert jobs, 'Replay job provenance missing'
    for path in jobs:
        metadata = read(path)
        assert metadata['returncode'] == 0
        assert not re.search(r'notimingchecks|nospecify|sdfnoerrors|sdfnowarn',' '.join(metadata['argv']),re.I)
    elaboration, = [read(path) for path in jobs if Path(read(path)['argv'][0]).name == 'xelab.bat']
    options = elaboration['argv']
    assert '-transport_int_delays' in options and '-maxdelay' in options
    for name in ('-pulse_r', '-pulse_int_r', '-pulse_e', '-pulse_int_e'):
        assert options.count(name) == 1 and options[options.index(name)+1] == '0'
    assert not any(option in options for option in ('-mindelay','-typdelay','-notimingchecks',
        '-nosdfinterconnectdelays','-nospecify','-sdfnowarn','-sdfnoerror'))
    assert result['timing_simulation_method'] == 'AMD transport, zero pulse error and rejection, slow/max'
    raw = directory/'activity.saif'
    saif = raw.read_text()
    duration = int(re.search(r'\(DURATION\s+(\d+)\)',saif)[1])
    assert re.search(r'\(TIMESCALE\s+1\s+ps\)',saif)
    assert duration == result['roi_duration_ps']
    assert sha(raw) == result['saif']['saif_sha256']
    entries = re.findall(r'\(T0\s+(\d+)\)\s*\(T1\s+(\d+)\)\s*\(TX\s+(\d+)\)(?:\s*\(TZ\s+(\d+)\))?(?:\s*\(TB\s+(\d+)\))?\s*\(TC\s+(\d+)\)',saif)
    assert len(entries) == result['saif']['scalar_records'] > 0
    unknown = 0
    for a,b,x,z,tb,tc in entries:
        assert int(a)+int(b)+int(x)+int(z or 0) == duration and int(tb or 0) == 0
        unknown += bool(int(x) or int(z or 0))
    assert unknown == result['saif']['unknown_time_records']
    records = prior.saif_records(raw)
    clock = records[ROOT+'/clk']
    a,b,x,z,tb,tc = clock
    assert a == b == duration//2 and x == z == tb == 0 and tc == duration//3000
    return dict(status='pass',engine=engine,design_top=result['design_top'],directory=str(directory),
        auditor_sha256=sha(__file__),prior_auditor_sha256=AUDIT_SHA,
        replay_check_sha256=sha(directory/'replay_checks.json'),duration_ps=duration,
        scalar_updates=neurons,requests=requests,retirements=retired,
        clock_transitions=tc,service_clocks=last-first+1,
        raw_unknown_time_records=unknown,
        scope='Exact trace/interval/SDF/SAIF checks; raw internal unknowns need separate physical-net audit')


def tcl_words(line):
    """Parse Tcl [list] records without executing any Tcl substitutions."""
    words = []
    pos = 0
    while pos < len(line):
        while pos < len(line) and line[pos].isspace():
            pos += 1
        if pos == len(line):
            break
        if line[pos] == '{':
            depth = 1; pos += 1; start = pos
            while pos < len(line) and depth:
                if line[pos] == '\\':
                    pos += 2; continue
                if line[pos] == '{': depth += 1
                if line[pos] == '}': depth -= 1
                pos += 1
            assert depth == 0, ('Unclosed Tcl list',line)
            words.append(line[start:pos-1])
        else:
            value = []
            while pos < len(line) and not line[pos].isspace():
                if line[pos] == '\\':
                    pos += 1; assert pos < len(line)
                value.append(line[pos]); pos += 1
            words.append(''.join(value))
        assert pos == len(line) or line[pos].isspace()
    return words


def connectivity(directory):
    refs = {}
    for line in (directory/'cell_ref_names.tsv').read_text().splitlines():
        if not line.strip(): continue
        cell,ref = tcl_words(line)
        assert cell not in refs; refs[cell] = ref
    assert refs
    nets = {}; pin_nets = {}
    for line in (directory/'net_connectivity.jsonl').read_text().splitlines():
        if not line.strip(): continue
        name,pins,ports = tcl_words(line)
        assert name not in nets
        pins,ports = tcl_words(pins),tcl_words(ports)
        nets[name] = dict(pins=pins,ports=ports)
        for pin in pins:
            pin_nets.setdefault(pin,[]).append(name)
    assert nets
    parents = {name:name for name in nets}
    def find(name):
        while parents[name] != name:
            parents[name] = parents[parents[name]]; name = parents[name]
        return name
    for aliases in pin_nets.values():
        for name in aliases[1:]:
            parents[find(name)] = find(aliases[0])
    groups = {}
    for name in nets:
        groups.setdefault(find(name),[]).append(name)
    clocks = set(); constants = {}
    for name,item in nets.items():
        if 'clk' in item['ports']: clocks.add(find(name))
        for pin in item['pins']:
            owner,port = pin.rsplit('/',1)
            if refs.get(owner) == 'GND' and port == 'G': constants[find(name)] = 0
            if refs.get(owner) == 'VCC' and port == 'P': constants[find(name)] = 1
    assert len(clocks) == 1
    # A static FF value is proved from its primitive pins and enabled clock,
    # rather than accepting names that happen to contain 'constant' or 'mode'.
    settled_ff = {}
    for _ in range(4):
        for cell,ref in refs.items():
            if ref not in ('FDRE','FDSE','FDCE','FDPE'): continue
            def connected(port):
                aliases = pin_nets.get(cell+'/'+port,[])
                return find(aliases[0]) if aliases else None
            d,ce,c,q = (connected(port) for port in ('D','CE','C','Q'))
            reset = connected({'FDRE':'R','FDSE':'S','FDCE':'CLR','FDPE':'PRE'}[ref])
            if d in constants and constants.get(ce) == 1 and c in clocks and constants.get(reset) == 0 and q:
                constants[q] = constants[d]
                settled_ff[cell] = dict(value=constants[d],primitive=ref)
    return refs,nets,pin_nets,groups,find,clocks,constants,settled_ff


def normalization_audit(named, replay_dir):
    normalization = read(named.with_suffix('.names.json'))
    raw = Path(normalization['source'])
    assert raw.resolve() == Path(replay_dir).resolve()/'activity.saif'
    assert sha(raw) == normalization['source_sha256']
    assert sha(named) == normalization['target_sha256']
    assert normalization['script_sha256'] == sha(OLD/'normalize_saif_names.py') == NORMALIZER_SHA
    original,corrected = raw.read_text(),named.read_text()
    state = r'\(T0\s+\d+\).*?\(TC\s+\d+\)'
    assert re.findall(state,original) == re.findall(state,corrected)
    assert re.findall(r'\((?:TIMESCALE|DURATION).*?\)',original) == re.findall(r'\((?:TIMESCALE|DURATION).*?\)',corrected)
    assert [x for x in original.splitlines() if '(INSTANCE' in x] == [x for x in corrected.splitlines() if '(INSTANCE' in x]
    assert len(normalization['changes']) == normalization['changed_net_tokens']
    assert all(item['new'] == item['old'][2:-1] for item in normalization['changes'])
    return prior.saif_records(named)


def annotation(directory):
    directory = Path(directory).resolve()
    evidence = read(directory/'evidence.json')
    engine = evidence['engine']; assert engine in range(5)
    verify(evidence['source_sha256']); verify(evidence['artifact_sha256'])
    check = replay(evidence['replay_dir'])
    assert check['engine'] == engine and check['design_top'] == evidence['design_top']
    records = normalization_audit(Path(evidence['saif_file']),evidence['replay_dir'])
    log = (directory/'annotation.log').read_text()
    matched = re.search(r'Design nets matched = (\d+) of (\d+)',log)
    assert matched and matched[1] == matched[2], 'Not all physical design nets mapped'
    unmatched = (directory/'unmatched.rpt').read_text()
    assert '--- Unmatched design nets ---' in unmatched
    assert not unmatched.split('--- Unmatched design nets ---')[-1].strip()
    assert not re.search(r'CRITICAL WARNING|ERROR:',log)
    assert all('[Power 33-330]' in line for line in log.splitlines() if line.startswith('WARNING:'))
    assert f'FRONTIER_ANNOTATION_POWER PASS E{engine}' in log
    hardware_file = Path(evidence['hardware_file']).resolve()
    assert evidence['source_sha256'][str(hardware_file)] == sha(hardware_file)
    hardware = read(hardware_file)
    verify(hardware['source_sha256']); verify(hardware['artifact_sha256'])
    assert hardware['status'] == 'pass' and hardware['engine'] == engine
    assert hardware['top'] == evidence['design_top']
    assert hardware['clock_period_ns'] == 6 and hardware['part'] == 'xc7a100tcsg324-1'
    accounting = hardware['slice_accounting']
    assert accounting['fixture_FF'] == 290 and accounting['launch_FF'] == 183 and accounting['capture_FF'] == 107
    assert hardware['full_fixture']['FF'] - hardware['core']['FF'] == 290
    assert hardware['WNS_ns'] >= 0 and hardware['WHS_ns'] >= 0
    replay_sources = read(Path(evidence['replay_dir'])/'replay_checks.json')['source_sha256']
    dcp = hardware_file.parent/'design.dcp'
    assert evidence['source_sha256'][str(dcp)] == replay_sources[str(dcp)] == sha(dcp)
    refs,nets,pin_nets,groups,find,clocks,constants,settled_ff = connectivity(directory)
    dsps = [cell for cell,ref in refs.items() if ref == 'DSP48E1']
    assert len(dsps) == hardware['core']['DSP'] == hardware['full_fixture']['DSP']
    assert len(dsps) == (1 if engine < 3 else 0)
    activity = {}; types = {}
    pattern = re.compile(r'^(.*?):\s+static probability = ([\d.eE+-]+) \((\w)\)\s+signal rate = ([\d.eE+-]+) \((\w)\)\s+toggle rate = ([\d.eE+-]+) \((\w)\)')
    for line in (directory/'switching_activity.rpt').read_text().splitlines():
        if not line.strip(): continue
        match = pattern.fullmatch(line.strip()); assert match, ('Unexpected activity',line)
        name,sp,a,rate,b,toggle,c = match.groups()
        assert a == b == c and name in nets and name not in activity
        sp,rate,toggle = float(sp),float(rate),float(toggle)
        activity[name] = dict(static_probability=sp,signal_rate_Mtransitions_per_s=rate,toggle_rate_percent=toggle,source=a)
        types[a] = types.get(a,0)+1
        if a == 'S':
            assert ROOT+'/'+name in records, ('Missing physical SAIF alias',name)
            t0,t1,tx,tz,tb,tc = records[ROOT+'/'+name]
            assert tx == tz == tb == 0, ('Unknown physical activity',name)
            expected_sp = t1/check['duration_ps']
            expected_rate = tc/(check['duration_ps']*1e-12)/1e6
            assert abs(sp-expected_sp) <= 0.000001
            assert abs(rate-expected_rate) <= max(0.00001,expected_rate*0.00001)
        elif a == 'C':
            assert find(name) in clocks and sp == 0.5 and abs(rate-1000/3) < 0.001
        elif a == 'D':
            assert find(name) in constants, ('Unaudited default/constant',name)
            assert sp == constants[find(name)] and rate == toggle == 0
        else:
            raise AssertionError(('Unverified activity source',name,a))
    assert set(activity) == set(nets), 'Every physical alias must be reported'
    dsp_activity = {}
    for dsp in dsps:
        ports = {}
        for port in ('CLK','CEA2','CEB2','CEC','CEP'):
            aliases = pin_nets[dsp+'/'+port]
            assert aliases
            if port == 'CLK':
                assert all(find(name) in clocks for name in aliases)
            else:
                assert all(activity[name]['source'] == 'S' or find(name) in constants for name in aliases)
            ports[port] = {name:activity[name] for name in aliases}
        dsp_activity[dsp] = ports
    xpe = ET.parse(directory/'power_xpe.xml').getroot()
    assert xpe.attrib['design'] == evidence['design_top']
    device = xpe.find('ENVIRONMENT/DEVICE')
    assert device.attrib == dict(part='xc7a100t',grade='commercial',package='csg324',speed='-1',process='typical',vid='No')
    sources = xpe.findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')
    assert {x.attrib['name']:float(x.attrib['voltage']) for x in sources} == dict(Vccbram=1.0,Vccint=1.0,Vccaux=1.8,Vccadc=1.8)
    dynamic = sum(float(x.attrib['voltage'])*float(x.attrib['icc']) for x in sources)
    static = sum(float(x.attrib['voltage'])*float(x.attrib['iccq']) for x in sources)
    rounding = sum(abs(float(x.attrib['voltage']))*0.5e-6+abs(float(x.attrib['icc']))*0.5e-6+0.25e-12 for x in sources)
    coarse = float(re.search(r'\| Dynamic \(W\)\s*\|\s*([\d.]+)',(directory/'power.rpt').read_text())[1])
    assert abs(dynamic-coarse) <= 0.0005+rounding
    thermal = {item.tag:item.attrib for item in xpe.find('ENVIRONMENT/THERMAL')}
    assert thermal['USER_JUNCTION']['value'] == '25.0 (C)'
    energy = dynamic*check['duration_ps']/SCALARS
    return dict(status='pass',engine=engine,design_top=evidence['design_top'],directory=str(directory),
        auditor_sha256=sha(__file__),prior_auditor_sha256=AUDIT_SHA,
        matched_physical_design_nets=int(matched[1]),physical_activity_source_counts=types,
        physical_activity_unknown_records=0,raw_unknown_records=check['raw_unknown_time_records'],
        excluded_unknown_scope='Only simulator internal/optimized aliases outside fully verified physical activity; inferred constants proved from primitive connectivity and ROI settling',
        native_interval_audit=check,critical_dsp_activity=dsp_activity,settled_constant_ffs=settled_ff,
        dynamic_power_W=dynamic,device_static_W=static,dynamic_power_rounding_bound_W=rounding,
        dynamic_energy_J=dynamic*check['duration_ps']*1e-12,
        estimated_dynamic_energy_pJ_per_scalar_update=energy,
        energy_rounding_bound_pJ_per_scalar_update=rounding*check['duration_ps']/SCALARS,
        voltage_sources=[x.attrib for x in sources],device_settings=device.attrib,thermal_settings=thermal,
        clock_period_ns=6,fixture_FF=290,power_xpe_sha256=sha(directory/'power_xpe.xml'),
        routed_hardware_file=str(hardware_file),routed_hardware_sha256=sha(hardware_file),
        core_resources=hardware['core'],WNS_ns=hardware['WNS_ns'],WHS_ns=hardware['WHS_ns'],
        scope='Vendor estimated dynamic energy of complete common 290-FF OOC fixture; not core-only energy, board energy or complete SNN-update energy',
        uncertainty_scope='Rounding bound describes export serialization only; it does not bound vendor-model or physical measurement error')


def self_check():
    assert tcl_words('{net[1]} {a/I b/O} {}') == ['net[1]','a/I b/O','']
    assert tcl_words('x\\ y {z {nested}}') == ['x y','z {nested}']
    assert sha(OLD/'normalize_saif_names.py') == NORMALIZER_SHA
    # Reuse frozen parser against an already audited complete SAIF. No jobs run.
    reference = OLD/'results'/'replay_v3_a0'/'activity.saif'
    records = prior.saif_records(reference)
    assert records['tb_selective_route_replay/dut/clk'][5] == 664272000//3000
    return dict(status='pass',tcl_parser_checked=True,frozen_saif_parser_checked=True,
        auditor_sha256=sha(__file__),prior_auditor_sha256=AUDIT_SHA,normalizer_sha256=NORMALIZER_SHA,
        scope='Parser/import checks only; forthcoming frontier evidence still requires per-engine audit')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--replay-dir',type=Path)
    group.add_argument('--power-dir',type=Path)
    group.add_argument('--self-check',action='store_true')
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    result = self_check() if args.self_check else annotation(args.power_dir) if args.power_dir else replay(args.replay_dir)
    if args.output:
        assert not args.output.exists(), 'Refusing to overwrite an audit'
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__': main()
