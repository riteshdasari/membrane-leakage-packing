"""Strict new leakage trace/SDF audit; physical-net checks imported as source from frozen predecessor."""
from pathlib import Path
from collections import deque
import importlib.util,json,re,sys
import xml.etree.ElementTree as ET
import numpy as np
P=Path(__file__).resolve().parent;OLD=P.parent.parent.parent/'selective_energy_trial'
ROOT='tb_sequential_energy_replay16/dut';PERIOD_PS=12000
AUDIT_SHA='d4cc05920fb7a2beada60d125bc885b39ad9eefd1a6aac68bb26cc258aa9ddf2'
NORMALIZER_SHA='81d84539f84354b317e452de0f4ffe3858f4a32afa54baea37416497d1d7ff07'
path=OLD/'audit_selective_energy.py'
import hashlib
assert hashlib.sha256(path.read_bytes()).hexdigest()==AUDIT_SHA
spec=importlib.util.spec_from_file_location('frozen_physical_saif_parser',path)
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
read,sha,verify=prior.read,prior.sha,prior.verify
def replay(directory):
    directory=Path(directory);d=read(directory/'replay_checks.json');e=d['engine']
    assert d['status']=='timing_pass_activity_pending'and e in range(7)
    verify(d['source_sha256']);verify(d['artifact_sha256'])
    checkfile=Path(d['native_check_file']);check=read(checkfile)
    assert sha(checkfile)==d['native_check_sha256']and check['status']=='pass'and check['B']==16 and check['cohort']=='actual_ottt_representative' and check['stall']==0 and check['capture']==1
    verify(check['source_sha256']);verify(check['artifact_sha256'])
    row,=[r for r in check['rows']if r['engine']==e];assert row==d['native_row']
    expectation_path=Path(d['cohort_expectation_file']);expectation=read(expectation_path)
    assert d['source_sha256'][str(expectation_path)]==sha(expectation_path)
    verify(expectation['source_sha256']);cohort=expectation['cohorts'][check['cohort']]
    verify(cohort['artifact_sha256']);actual={key:value for key,value in np.load(cohort['expected_outputs_file']).items()}
    assert row['neurons']==cohort['operations'] and row['requests']==cohort['expected_requests_by_engine'][e]
    ends=np.repeat(np.cumsum(actual['frame_lengths']),actual['frame_lengths'])
    if e==6:assert check['cohort']=='actual_ottt_representative'and np.all(actual['beta']==128)

    trace=Path(d['native_trace_file']);assert trace==checkfile.parent/f"trace{row['native_index']}.txt";assert sha(trace)==d['trace_sha256']
    assert row['native_index']=={5:0,1:1,6:2}[e]
    queue=deque();requests=retired=neurons=retired_neurons=0;first=last=None
    for index,line in enumerate(trace.open()):
        f=line.split();assert len(f)==15 and int(f[0])==index
        v=[int(x,16 if j in(5,6,11)else 10)for j,x in enumerate(f)]
        _,rst,iv,ready,av,U,B,ir,take,ov,count,data,mode,accept,retire=v
        assert 0<=av<=2 and accept==int(iv and ir and av>0)and retire==int(ov and ready)
        if accept:
            assert not rst and 1<=take<=av
            want=0
            source=[]
            assert av==(2 if ends[neurons]-neurons>=2 else 1)
            for k in range(av):
                u=(U>>(16*k))&65535;u=u-65536 if u&32768 else u;b=(B>>(9*k))&511
                assert b<=256 and u==int(actual['U'][neurons+k]) and b==int(actual['beta'][neurons+k])
                source.append((u,b))
            pair=av==2
            if e==4:pair=False
            elif e==1:pair=pair and source[0][1]==source[1][1]
            elif e in (0,5):pair=pair and source[0][1]==source[1][1]and -256<=source[0][0]<=255 and -256<=source[1][0]<=255 and(e==5 or source[0][1]>=64)
            assert take==(2 if pair else 1)
            for k,(u,b)in enumerate(source[:take]):
                scalar=-((-u*b)//256);assert scalar==int(actual['expected_leak'][neurons+k])
                want|=(scalar&65535)<<(16*k)
            queue.append((take,want,int(e in (0,5)and take==2),index));requests+=1;neurons+=take
            if first is None:first=index
        if retire:
            assert queue
            qcount,qdata,qmode,qcycle=queue.popleft()
            assert (count,data,mode)==(qcount,qdata,qmode)and index-qcycle==2
            retired+=1;retired_neurons+=count;last=index
    total=index+1
    assert not queue and requests==retired==row['requests']and neurons==retired_neurons==row['neurons']==cohort['operations']
    assert(first,last)==(row['first_accept'],row['last_retire'])and total==d['replay_rows_checked']==d['trace_count']
    start=132000+12000*first-1;duration=12000*(last-first+3)
    assert(d['roi_start_ps'],d['roi_duration_ps'],d['roi_end_ps'])==(start,duration,start+duration)
    assert d['output_trace_row_offset']==2 and d['clock_period_ns']==12
    golden=read(Path(d['golden_check_file']));assert golden['status']=='pass'
    verify(golden['source_sha256']);verify(golden['artifact_sha256'])
    exported=Path(d['export_artifacts_file']);verify(read(exported));producer=read(exported.parent/'provenance.json');verify(producer)
    for name in ('routed.v','routed.sdf'):
        p=str(exported.parent/name);assert producer.get(p,sha(p))==d['source_sha256'][p]==read(exported)[p]==sha(p)
    hardware_file=Path(d['hardware_file']);hardware=read(hardware_file);assert hardware['status']=='pass'
    dcp=str(hardware_file.parent/'design.dcp');assert producer[dcp]==d['source_sha256'][dcp]==sha(dcp)
    text='\n'.join(p.read_text(errors='replace')for p in directory.glob('*.log'))
    assert 'SDF backannotation was successful'in text and f'root module "{ROOT}"'in text
    assert not re.search(r'\b(?:Warning|ERROR|Fatal)\b.*(?:SDF|timing|setup|hold)|Timing violation|\$setuphold|\$recovery|\$recrem|\$width|REPLAY.*mismatch',text,re.I)
    assert f'FRONTIER_ROUTE_REPLAY PASS E{e} ROWS {total} CHECKED {total}'in text
    assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {start+duration} DURATION_PS {duration}'in text
    jobs=[read(p)for p in directory.glob('tool_*.job.json')];assert len(jobs)==4 and all(j['returncode']==0 for j in jobs)
    opts,=[j['argv']for j in jobs if Path(j['argv'][0]).name=='xelab.bat']
    assert '-transport_int_delays'in opts and '-maxdelay'in opts
    assert not re.search(r'notimingchecks|nospecify|sdfnoerrors|sdfnowarn',' '.join(opts),re.I)
    for name in('-pulse_r','-pulse_int_r','-pulse_e','-pulse_int_e'):assert opts.count(name)==1 and opts[opts.index(name)+1]=='0'
    raw=directory/'activity.saif';s=raw.read_text();assert re.search(r'\(TIMESCALE\s+1\s+ps\)',s)
    assert int(re.search(r'\(DURATION\s+(\d+)\)',s)[1])==duration
    records=prior.saif_records(raw);unknown=0
    for a,b,x,z,tb,tc in records.values():
        assert a+b+x+z==duration and tb==0;unknown+=bool(x or z)
    assert records[ROOT+'/clk']==(duration//2,duration//2,0,0,0,duration//6000)
    return dict(status='pass',engine=e,design_top=d['design_top'],duration_ps=duration,scalar_updates=neurons,requests=requests,retirements=retired,clock_transitions=duration//6000,raw_unknown_time_records=unknown,scope='Representative OTTT64 fixed16 actual source operands, signed9 pair metadata, golden fixture, exact routed/SDF replay and SAIF interval audit')

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
    engine = evidence['engine']; assert engine in range(7)
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
    assert hardware['B']==16 and hardware['clock_period_ns'] == 12 and hardware['part'] == 'xc7a100tcsg324-1'
    accounting = hardware['slice_accounting']
    assert accounting['fixture_FF'] == 94 and accounting['launch_FF'] == 55 and accounting['capture_FF'] == 39
    assert hardware['full_fixture']['FF'] - hardware['core']['FF'] == 94
    assert hardware['WNS_ns'] >= 0 and hardware['WHS_ns'] >= 0
    replay_sources = read(Path(evidence['replay_dir'])/'replay_checks.json')['source_sha256']
    dcp = hardware_file.parent/'design.dcp'
    assert evidence['source_sha256'][str(dcp)] == replay_sources[str(dcp)] == sha(dcp)
    refs,nets,pin_nets,groups,find,clocks,constants,settled_ff = connectivity(directory)
    dsps = [cell for cell,ref in refs.items() if ref == 'DSP48E1']
    assert len(dsps) == hardware['core']['DSP'] == hardware['full_fixture']['DSP']
    assert len(dsps) == [1,1,0,2,1,1,0][engine]
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
            assert find(name) in clocks and sp == 0.5 and abs(rate-1000/6) < 0.001
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
    energy = dynamic*check['duration_ps']/check['scalar_updates']
    return dict(status='pass',engine=engine,design_top=evidence['design_top'],directory=str(directory),
        auditor_sha256=sha(__file__),prior_auditor_sha256=AUDIT_SHA,
        matched_physical_design_nets=int(matched[1]),physical_activity_source_counts=types,
        physical_activity_unknown_records=0,raw_unknown_records=check['raw_unknown_time_records'],
        excluded_unknown_scope='Only simulator internal/optimized aliases outside fully verified physical activity; inferred constants proved from primitive connectivity and ROI settling',
        native_interval_audit=check,critical_dsp_activity=dsp_activity,settled_constant_ffs=settled_ff,
        dynamic_power_W=dynamic,device_static_W=static,dynamic_power_rounding_bound_W=rounding,
        dynamic_energy_J=dynamic*check['duration_ps']*1e-12,
        estimated_dynamic_energy_pJ_per_scalar_update=energy,
        energy_rounding_bound_pJ_per_scalar_update=rounding*check['duration_ps']/check['scalar_updates'],
        voltage_sources=[x.attrib for x in sources],device_settings=device.attrib,thermal_settings=thermal,
        clock_period_ns=12,fixture_FF=94,power_xpe_sha256=sha(directory/'power_xpe.xml'),
        routed_hardware_file=str(hardware_file),routed_hardware_sha256=sha(hardware_file),
        core_resources=hardware['core'],WNS_ns=hardware['WNS_ns'],WHS_ns=hardware['WHS_ns'],
        scope='Representative OTTT64 after common zero filtering: vendor estimated dynamic energy of complete common 94-FF OOC fixture; not core-only energy, board energy or complete SNN-update energy',
        uncertainty_scope='Rounding bound describes export serialization only; it does not bound vendor-model or physical measurement error')


