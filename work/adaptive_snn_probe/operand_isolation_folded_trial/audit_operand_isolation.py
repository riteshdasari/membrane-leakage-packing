"""Read-only operand-isolation timing, physical-activity and energy audit.

The earlier timing/SAIF arithmetic verifier is imported from its pinned,
unchanged file. This audit adds the isolated design contract, functional
equivalence evidence, connectivity-based physical checks and frozen references.
No HDL/Vivado jobs or baseline edits are performed.
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
TOP = 'top_guard_add_selective_isolated_v3'
ROOT = 'tb_selective_route_replay/dut'
AUDIT_SHA = 'd4cc05920fb7a2beada60d125bc885b39ad9eefd1a6aac68bb26cc258aa9ddf2'
NORMALIZER_SHA = '81d84539f84354b317e452de0f4ffe3858f4a32afa54baea37416497d1d7ff07'
TRACE_SHA = '58f2772ee413cec8ed34d2ff3bd8ab0722fb95cce4c71efb01736ebdaeeca97d'
BASELINES = {
    'fixed': ('annotated_power_v2_a1', 'd87b9465b489aa9bdc6138d25ca8515ad752e8e6bba8148a822400d06185736e'),
    'adaptive': ('annotated_power_v3_a0', 'd1587282fcc7d01cc55dca48bbb535e3d19770a7a015cf86c7ab79747fd8f1a5'),
}


def load_prior():
    import hashlib
    path = OLD / 'audit_selective_energy.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == AUDIT_SHA, 'Prior audit changed'
    spec = importlib.util.spec_from_file_location('frozen_selective_audit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior = load_prior()
read, sha, verify = prior.read, prior.sha, prior.verify


def replay(directory):
    directory = Path(directory).resolve()
    result = read(directory / 'replay_checks.json')
    assert result['design_top'] == TOP and result['variant'] == 3
    assert result['native_row']['trace_sha256'] == TRACE_SHA
    functional = result['functional_check_sha256']
    assert len(functional) == 4, 'Four stress/model/backpressure comparisons required'
    verify(functional)
    tested = set()
    for path in functional:
        check = read(path)
        assert check['status'] == 'pass', ('Functional comparison failed', path)
        verify(check['source_sha256'])
        verify(check['candidate_file_sha256'])
        assert sha(check['log_file']) == check['log_sha256']
        assert sha(check['archived_check_file']) == check['archived_check_sha256']
        assert sha(check['archived_retirement_file']) == check['archived_retirement_sha256']
        assert check['policy'] == 1
        assert all(check[key] for key in ('matched_archived_retirement_bytes',
            'matched_reference_retirement_bytes',
            'output_controls_and_internal_service_cycle_identical',
            'reset_and_backpressure_preludes_checked'))
        tested.add((check['kind'],check['backpressure']))
        if (check['kind'],check['backpressure']) == ('models',False):
            trace = check['trace']
            assert trace and trace['matched_all_eighteen_columns']
            assert sha(trace['file']) == trace['sha256'] == TRACE_SHA
            assert sha(trace['reference']) == trace['reference_sha256'] == TRACE_SHA
            assert check['physical_service']['clocks'] == 110710
    assert tested == {('main',False),('main',True),('models',False),('models',True)}
    audited = prior.replay(directory)
    assert audited['duration_ps'] == 664272000
    assert audited['scalar_updates'] == 635904
    assert audited['correction_steps'] == 1008 and audited['correction_freezes'] == 114
    audited.update(design_top=TOP, functional_check_sha256=functional,
                   auditor_sha256=sha(__file__), prior_auditor_sha256=AUDIT_SHA)
    return audited


def tcl_words(line):
    """Parse strings produced by Tcl [list], without executing substitutions."""
    words = []
    pos = 0
    while pos < len(line):
        while pos < len(line) and line[pos].isspace():
            pos += 1
        if pos == len(line):
            break
        start = pos
        if line[pos] == '{':
            depth = 1
            pos += 1
            start = pos
            while pos < len(line) and depth:
                if line[pos] == '\\':
                    pos += 2
                    continue
                if line[pos] == '{':
                    depth += 1
                if line[pos] == '}':
                    depth -= 1
                pos += 1
            assert depth == 0, ('Unclosed Tcl list', line)
            words.append(line[start:pos-1])
        else:
            value = []
            while pos < len(line) and not line[pos].isspace():
                if line[pos] == '\\':
                    pos += 1
                    assert pos < len(line)
                value.append(line[pos])
                pos += 1
            words.append(''.join(value))
        assert pos == len(line) or line[pos].isspace(), ('Malformed Tcl list', line)
    return words


def connectivity(directory):
    refs = {}
    for line in (directory / 'cell_ref_names.tsv').read_text().splitlines():
        if not line.strip():
            continue
        cell, ref = tcl_words(line)
        assert cell not in refs
        refs[cell] = ref
    assert refs and list(refs.values()).count('DSP48E1') == 1
    nets = {}
    pin_nets = {}
    for line in (directory / 'net_connectivity.jsonl').read_text().splitlines():
        if not line.strip():
            continue
        name, pins, ports = tcl_words(line)
        pins, ports = tcl_words(pins), tcl_words(ports)
        assert name not in nets
        nets[name] = dict(pins=pins, ports=ports)
        for pin in pins:
            pin_nets.setdefault(pin, []).append(name)
    # A hierarchical pin occurs on both aliases of the same physical connection.
    parents = {name:name for name in nets}
    def find(name):
        while parents[name] != name:
            parents[name] = parents[parents[name]]
            name = parents[name]
        return name
    for aliases in pin_nets.values():
        for name in aliases[1:]:
            parents[find(name)] = find(aliases[0])
    groups = {}
    for name in nets:
        groups.setdefault(find(name), []).append(name)
    clock = set()
    constants = {}
    for name, item in nets.items():
        if 'clk' in item['ports']:
            clock.add(find(name))
        for pin in item['pins']:
            owner, port = pin.rsplit('/',1)
            if refs.get(owner) == 'GND' and port == 'G':
                constants[find(name)] = 0
            if refs.get(owner) == 'VCC' and port == 'P':
                constants[find(name)] = 1
    assert len(clock) == 1, 'Exactly one physical input clock required'
    # The sink narrow_mode FF has a constant D and enabled 6 ns clock. It has
    # settled long before the ROI. Infer this via pins, rather than a net name.
    for _ in range(3):
        for cell, ref in refs.items():
            if ref not in ('FDRE','FDSE','FDCE','FDPE'):
                continue
            def connected(port):
                aliases = pin_nets.get(cell+'/'+port, [])
                return find(aliases[0]) if aliases else None
            d, ce, c, q = (connected(port) for port in ('D','CE','C','Q'))
            reset = connected('R' if ref == 'FDRE' else 'S' if ref == 'FDSE' else 'CLR' if ref == 'FDCE' else 'PRE')
            if d in constants and constants.get(ce) == 1 and c in clock and constants.get(reset) == 0 and q:
                constants[q] = constants[d]
    return refs, nets, pin_nets, groups, find, clock, constants


def annotation(directory):
    directory = Path(directory).resolve()
    evidence = read(directory/'evidence.json')
    assert evidence['design_top'] == TOP and evidence['variant'] == 3
    verify(evidence['source_sha256'])
    verify(evidence['artifact_sha256'])
    check = replay(evidence['replay_dir'])
    named = Path(evidence['saif_file'])
    normalization = read(named.with_suffix('.names.json'))
    raw = Path(normalization['source'])
    assert raw.resolve() == Path(evidence['replay_dir']).resolve()/'activity.saif'
    assert sha(raw) == normalization['source_sha256']
    assert sha(named) == normalization['target_sha256']
    assert normalization['script_sha256'] == sha(OLD/'normalize_saif_names.py') == NORMALIZER_SHA
    original, corrected = raw.read_text(), named.read_text()
    state = r'\(T0\s+\d+\).*?\(TC\s+\d+\)'
    assert re.findall(state,original) == re.findall(state,corrected)
    assert re.findall(r'\((?:TIMESCALE|DURATION).*?\)',original) == re.findall(r'\((?:TIMESCALE|DURATION).*?\)',corrected)
    assert [x for x in original.splitlines() if '(INSTANCE' in x] == [x for x in corrected.splitlines() if '(INSTANCE' in x]
    assert len(normalization['changes']) == normalization['changed_net_tokens']
    for change in normalization['changes']:
        assert change['new'] == change['old'][2:-1]
    records = prior.saif_records(named)
    log = (directory/'annotation.log').read_text()
    matched = re.search(r'Design nets matched = (\d+) of (\d+)',log)
    assert matched and matched[1] == matched[2], 'Not all physical design nets mapped'
    unmatched = (directory/'unmatched.rpt').read_text()
    assert '--- Unmatched design nets ---' in unmatched
    assert not unmatched.split('--- Unmatched design nets ---')[-1].strip()
    assert not re.search(r'CRITICAL WARNING|ERROR:',log)
    warns = [line for line in log.splitlines() if line.startswith('WARNING:')]
    assert all('[Power 33-330]' in line for line in warns), warns
    refs, nets, pin_nets, groups, find, clock, constants = connectivity(directory)
    hardware_paths = [Path(path) for path in evidence['source_sha256']
                      if Path(path).name == 'hardware.json' and P in Path(path).parents]
    assert len(hardware_paths) == 1
    hardware = read(hardware_paths[0])
    verify(hardware['source_sha256'])
    verify(hardware['artifact_sha256'])
    assert hardware['status'] == 'pass' and hardware['top'] == TOP
    assert hardware['clock_period_ns'] == 6 and hardware['part'] == 'xc7a100tcsg324-1'
    assert hardware['slice_accounting']['fixture_FF'] == 219
    assert hardware['WNS_ns'] >= 0 and hardware['WHS_ns'] >= 0
    replay_sources = read(Path(evidence['replay_dir'])/'replay_checks.json')['source_sha256']
    dcp = hardware_paths[0].parent/'design.dcp'
    assert str(dcp) in evidence['source_sha256'] and str(dcp) in replay_sources
    assert evidence['source_sha256'][str(dcp)] == replay_sources[str(dcp)] == sha(dcp)
    activity, types = {}, {}
    pattern = re.compile(r'^(.*?):\s+static probability = ([\d.eE+-]+) \((\w)\)\s+signal rate = ([\d.eE+-]+) \((\w)\)\s+toggle rate = ([\d.eE+-]+) \((\w)\)')
    for line in (directory/'switching_activity.rpt').read_text().splitlines():
        if not line.strip():
            continue
        match = pattern.fullmatch(line.strip())
        assert match, ('Unexpected activity report',line)
        name, sp, a, rate, b, toggle, c = match.groups()
        assert a == b == c and name in nets
        sp, rate, toggle = float(sp),float(rate),float(toggle)
        activity[name] = dict(static_probability=sp,signal_rate_Mtransitions_per_s=rate,toggle_rate_percent=toggle,source=a)
        types[a] = types.get(a,0)+1
        if a == 'S':
            assert ROOT+'/'+name in records, ('Missing SAIF alias',name)
            t0,t1,tx,tz,tb,tc = records[ROOT+'/'+name]
            assert tx == tz == tb == 0, ('Unknown physical activity',name)
            expected_sp = t1/check['duration_ps']
            expected_rate = tc/(check['duration_ps']*1e-12)/1e6
            assert abs(sp-expected_sp) <= 0.000001, ('Mapped state mismatch',name)
            assert abs(rate-expected_rate) <= max(0.00001,expected_rate*0.00001), ('Mapped rate mismatch',name)
        elif a == 'C':
            assert find(name) in clock and sp == 0.5 and abs(rate-1000/3) < 0.001
        elif a == 'D':
            assert find(name) in constants, ('Unaudited constant/default',name)
            assert sp == constants[find(name)] and rate == toggle == 0
        else:
            raise AssertionError(('Unverified activity source',name,a))
    assert set(activity) == set(nets), 'Switching report must cover every routed net alias'
    dsp = next(cell for cell, ref in refs.items() if ref == 'DSP48E1')
    dsp_activity = {}
    for port in ('CEA2','CEB2','CEC','CEP'):
        aliases = pin_nets[dsp+'/'+port]
        assert aliases and all(activity[name]['source'] == 'S' for name in aliases)
        dsp_activity[port] = {name:activity[name] for name in aliases}
    semantic = {name:item for name,item in activity.items()
                if re.search(r'corrected_high|isolat|selected_hu|selected_hi|work_mask|bad_mask|correction_step|busy',name,re.I)}
    # This selection is descriptive. Coverage and zero-X checks above include
    # every physical net regardless of whether synthesis retained source names.
    xpe = ET.parse(directory/'power_xpe.xml').getroot()
    assert xpe.attrib['design'] == TOP
    device = xpe.find('ENVIRONMENT/DEVICE')
    assert device.attrib == dict(part='xc7a100t',grade='commercial',package='csg324',speed='-1',process='typical',vid='No')
    sources = xpe.findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')
    assert {x.attrib['name']:float(x.attrib['voltage']) for x in sources} == dict(Vccbram=1.0,Vccint=1.0,Vccaux=1.8,Vccadc=1.8)
    dynamic = sum(float(x.attrib['voltage'])*float(x.attrib['icc']) for x in sources)
    rounding = sum(abs(float(x.attrib['voltage']))*0.5e-6+abs(float(x.attrib['icc']))*0.5e-6+0.25e-12 for x in sources)
    static = sum(float(x.attrib['voltage'])*float(x.attrib['iccq']) for x in sources)
    coarse = float(re.search(r'\| Dynamic \(W\)\s*\|\s*([\d.]+)',(directory/'power.rpt').read_text())[1])
    assert abs(dynamic-coarse) <= 0.0005+rounding
    thermal = {item.tag:item.attrib for item in xpe.find('ENVIRONMENT/THERMAL')}
    assert thermal['USER_JUNCTION']['value'] == '25.0 (C)'
    energy = dynamic*check['duration_ps']/635904
    result = dict(status='pass',variant=3,design_top=TOP,directory=str(directory),
        auditor_sha256=sha(__file__),prior_auditor_sha256=AUDIT_SHA,
        matched_physical_design_nets=int(matched[1]),physical_activity_source_counts=types,
        physical_activity_unknown_records=0,raw_unknown_records=check['raw_unknown_time_records'],
        excluded_unknown_scope='Only simulator internals/optimized aliases absent from verified physical S activity; D constants proved via primitive connectivity and settling',
        native_interval_audit=check,critical_dsp_activity=dsp_activity,
        semantic_activity_candidates=semantic,
        semantic_activity_note='Source-name examples only; isolation retention requires mapped connectivity review. Full physical activity coverage is independent of these names.',
        dynamic_power_W=dynamic,dynamic_power_rounding_bound_W=rounding,device_static_W=static,
        dynamic_energy_J=dynamic*check['duration_ps']*1e-12,
        estimated_dynamic_energy_pJ_per_scalar_update=energy,
        energy_rounding_bound_pJ_per_scalar_update=rounding*check['duration_ps']/635904,
        voltage_sources=[x.attrib for x in sources],device_settings=device.attrib,
        thermal_settings=thermal,clock_period_ns=6,power_xpe_sha256=sha(directory/'power_xpe.xml'),
        routed_hardware_file=str(hardware_paths[0]),routed_hardware_sha256=sha(hardware_paths[0]),
        core_resources=hardware['core'],WNS_ns=hardware['WNS_ns'],WHS_ns=hardware['WHS_ns'],
        scope='Vendor estimated dynamic energy of complete 219-FF OOC fixture; not board measurement or core-only result')
    result['frozen_reference_comparisons'] = comparisons(result)
    return result


def comparisons(result):
    comparisons = {}
    for name,(folder,pin) in BASELINES.items():
        path = OLD/'results'/folder/'power_audit.json'
        assert sha(path) == pin, ('Frozen reference changed',name)
        baseline = read(path)
        # Recheck source/artifact pins, timing intervals, full physical SAIF and
        # all report values, not just a previously serialized energy number.
        fresh = prior.annotation(path.parent)
        assert fresh['estimated_dynamic_energy_pJ_per_scalar_update'] == baseline['estimated_dynamic_energy_pJ_per_scalar_update']
        assert baseline['device_settings'] == result['device_settings']
        assert baseline['clock_period_ns'] == result['clock_period_ns'] == 6
        assert baseline['native_interval_audit']['scalar_updates'] == 635904
        assert baseline['thermal_settings']['USER_JUNCTION'] == result['thermal_settings']['USER_JUNCTION']
        # Vivado derives ambient to hold the declared junction temperature;
        # ambient can differ as estimated power differs. Other inputs match.
        assert {k:v for k,v in baseline['thermal_settings'].items() if k!='AMBIENT'} == {k:v for k,v in result['thermal_settings'].items() if k!='AMBIENT'}
        assert {x['name']:x['voltage'] for x in baseline['voltage_sources']} == {x['name']:x['voltage'] for x in result['voltage_sources']}
        base = baseline['estimated_dynamic_energy_pJ_per_scalar_update']
        bound = baseline['dynamic_power_rounding_bound_W']*baseline['native_interval_audit']['duration_ps']/635904
        actual = result['estimated_dynamic_energy_pJ_per_scalar_update']
        err = result['energy_rounding_bound_pJ_per_scalar_update']
        comparisons[name] = dict(reference_audit_file=str(path),reference_audit_sha256=pin,
            reference_estimated_energy_pJ_per_update=base,ratio=actual/base,
            percent_change=100*(actual/base-1),
            rounding_ratio_interval=[max(0,actual-err)/(base+bound),(actual+err)/(base-bound)],
            comparison_scope='Equal saved scalar work and primary power-model settings; actual service duration retained; whole-fixture vendor estimate')
    return comparisons


def self_check():
    assert tcl_words('{net[1]} {a/I b/O} {}') == ['net[1]','a/I b/O','']
    assert tcl_words('x\\ y {z {nested}}') == ['x y','z {nested}']
    result = {}
    for name,(folder,pin) in BASELINES.items():
        path = OLD/'results'/folder/'power_audit.json'
        assert sha(path) == pin
        audited = prior.annotation(path.parent)
        assert audited['status'] == 'pass'
        result[name] = audited['estimated_dynamic_energy_pJ_per_scalar_update']
    return dict(status='pass',parser_and_frozen_reference_checks=result)


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
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__':
    main()
