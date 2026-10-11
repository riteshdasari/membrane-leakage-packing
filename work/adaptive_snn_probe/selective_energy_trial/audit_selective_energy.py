"""Read-only audit of routed replay evidence, annotation and power estimates.

No HDL/Vivado jobs. This verifies actual intervals and report data, separately
from replay scheduling. It makes no board-energy or arithmetic novelty claim.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent


def read(path):return json.loads(Path(path).read_text())
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def verify(stamps):
    for path,pin in stamps.items():assert sha(path)==pin,('Changed evidence',path)


def replay(directory):
    directory=Path(directory).resolve()
    result=read(directory/'replay_checks.json')
    assert result['status'] in ('pass','timing_pass_activity_pending') and result['variant'] in (2,3)
    verify(result['source_sha256']);verify(result['artifact_sha256'])
    row=result['native_row']
    assert sha(row['trace_file'])==row['trace_sha256']
    first,last=None,None
    requests=retired=neurons=corrections=freezes=total=0
    with Path(row['trace_file']).open() as f:
        for n,line in enumerate(f):
            fields=line.split();assert len(fields)==18 and int(fields[0])==n
            running,rst,iv,orr,av,ir,take,ov,corr,adv=map(int,
                [fields[k] for k in (1,3,4,5,6,9,10,11,15,16)])
            total+=1
            if not running:continue
            assert rst==0
            if iv and ir and av:
                requests+=1;neurons+=take
                if first is None:first=n
            if ov and orr:retired+=1;last=n
            corrections+=corr;freezes+=bool(corr and not adv)
    assert requests==retired==110592 and neurons==635904
    assert total==result['replay_rows_checked']==row['trace_count']
    assert (first,last)==(row['first_accept_trace_index'],row['last_retire_trace_index'])
    assert last-first+1==(110596 if result['variant']==2 else 110710)
    assert (corrections,freezes)==((0,0) if result['variant']==2 else (1008,114))
    assert result['roi_start_ps']==(126+6*first)*1000-1
    assert result['roi_end_ps']==(126+6*(last+3))*1000-1
    assert result['roi_duration_ps']==(last-first+3)*6000
    assert result['roi_extra_fixture_cycles']==2 and result['output_trace_row_offset']==2
    logs=[path for path in directory.glob('*.log') if path.is_file()]
    text='\n'.join(path.read_text(errors='replace') for path in logs)
    assert 'SDF backannotation was successful' in text
    assert 'root module "tb_selective_route_replay/dut"' in text
    assert not re.search(r'\b(?:Warning|ERROR|Fatal)\b.*(?:SDF|timing|setup|hold)|Timing violation|\$setuphold|\$recovery|\$recrem|\$width|REPLAY.*mismatch',text,re.I)
    assert f"SELECTIVE_ROUTE_REPLAY PASS V{result['variant']}" in text
    assert f"SELECTIVE_SAIF_CLOSED START_PS {result['roi_start_ps']} END_PS {result['roi_end_ps']} DURATION_PS {result['roi_duration_ps']}" in text
    for path in directory.glob('tool_*.job.json'):
        metadata=read(path);assert metadata['returncode']==0
        options=' '.join(metadata['argv'])
        assert not re.search(r'notimingchecks|nospecify|sdfnoerrors|sdfnowarn',options,re.I)
    saif=(directory/'activity.saif').read_text()
    duration=int(re.search(r'\(DURATION\s+(\d+)\)',saif)[1])
    assert re.search(r'\(TIMESCALE\s+1\s+ps\)',saif)
    assert duration==result['roi_duration_ps']
    assert sha(directory/'activity.saif')==result['saif']['saif_sha256']
    # Independently verify each state-time record and the root 6 ns clock.
    entries=re.findall(r'\(T0\s+(\d+)\)\s*\(T1\s+(\d+)\)\s*\(TX\s+(\d+)\)(?:\s*\(TZ\s+(\d+)\))?(?:\s*\(TB\s+(\d+)\))?\s*\(TC\s+(\d+)\)',saif)
    assert len(entries)==result['saif']['scalar_records']>0
    for a,b,x,z,tb,tc in entries:assert int(a)+int(b)+int(x)+int(z or 0)==duration and int(tb or 0)==0
    clock=re.search(r'\(clk\s+\(T0\s+(\d+)\)\s*\(T1\s+(\d+)\)\s*\(TX\s+(\d+)\)(?:\s*\(TZ\s+(\d+)\))?(?:\s*\(TB\s+(\d+)\))?\s*\(TC\s+(\d+)\)',saif)
    assert clock,'Root clock missing from SAIF'
    a,b,x,z,tb,tc=clock.groups()
    assert int(a)==int(b)==duration//2 and int(tc)==duration//3000
    return dict(status='pass',variant=result['variant'],directory=str(directory),
        replay_check_sha256=sha(directory/'replay_checks.json'),duration_ps=duration,
        scalar_updates=neurons,requests=requests,correction_steps=corrections,
        correction_freezes=freezes,clock_transitions=int(tc),
        raw_unknown_time_records=result['saif']['unknown_time_records'],
        scope='Exact trace/interval/SDF/SAIF checks; power relevance of raw unknown records requires mapped-net audit')


def canonical(token):
    # XSim emits a Verilog escaped bus base plus a separate escaped bit index.
    # The separator belongs to the name wrapper, not to the logical net name.
    if token.startswith('\\\\'):
        token=token[2:]
        token=re.sub(r'\\ (?=\\\[)','',token)
        if token.endswith('\\'):token=token[:-1]
    return re.sub(r'\\(.)',r'\1',token)


def saif_records(path):
    """Parse scalar records with instance scope; retain simulator aliases."""
    records={};depth=0;stack=[]
    pattern=re.compile(r'^\s*\((.+?)\s+\(T0\s+(\d+)\)\s*\(T1\s+(\d+)\)\s*\(TX\s+(\d+)\)\s*\(TZ\s+(\d+)\)\s*\(TB\s+(\d+)\)\s*\(TC\s+(\d+)\)')
    for line in Path(path).read_text().splitlines():
        inst=re.match(r'\s*\(INSTANCE\s+(\S+)',line)
        if inst:stack.append((depth+1,canonical(inst[1])))
        match=pattern.match(line)
        if match:
            name='/'.join([value for _,value in stack]+[canonical(match[1])])
            values=tuple(map(int,match.groups()[1:]))
            if name in records:assert records[name]==values,('Conflicting canonical aliases',name)
            records[name]=values
        parentheses=re.sub(r'\\.','',line)
        depth+=parentheses.count('(')-parentheses.count(')')
        while stack and stack[-1][0]>depth:stack.pop()
    assert depth==0 and records
    return records


def annotation(directory):
    directory=Path(directory).resolve()
    evidence=read(directory/'evidence.json')
    verify(evidence['source_sha256']);verify(evidence['artifact_sha256'])
    check=replay(evidence['replay_dir'])
    named=Path(evidence['saif_file'])
    normalization=read(named.with_suffix('.names.json'))
    raw=Path(normalization['source'])
    assert sha(raw)==normalization['source_sha256'] and sha(named)==normalization['target_sha256']
    assert normalization['script_sha256']==sha(P/'normalize_saif_names.py')
    original,corrected=raw.read_text(),named.read_text()
    state=r'\(T0\s+\d+\).*?\(TC\s+\d+\)'
    assert re.findall(state,original)==re.findall(state,corrected)
    assert original.count('(INSTANCE')==corrected.count('(INSTANCE')
    assert len(normalization['changes'])==normalization['changed_net_tokens']
    for change in normalization['changes']:
        assert change['new']==change['old'][2:-1]
    records=saif_records(named)
    log=(directory/'annotation.log').read_text()
    matched=re.search(r'Design nets matched = (\d+) of (\d+)',log)
    assert matched and matched[1]==matched[2],'Not all physical design nets mapped'
    assert '--- Unmatched design nets ---' in (directory/'unmatched.rpt').read_text()
    tail=(directory/'unmatched.rpt').read_text().split('--- Unmatched design nets ---')[-1]
    assert not tail.strip(),tail
    assert not re.search(r'CRITICAL WARNING|ERROR:',log)
    # The clock-annotation warning is expected: Vivado uses the audited 6ns XDC.
    warns=[line for line in log.splitlines() if line.startswith('WARNING:')]
    assert all('[Power 33-330]' in line for line in warns),warns
    activity={};types={};missing=[]
    pattern=re.compile(r'^(.*?):\s+static probability = ([\d.eE+-]+) \((\w)\)\s+signal rate = ([\d.eE+-]+) \((\w)\)\s+toggle rate = ([\d.eE+-]+) \((\w)\)')
    for line in (directory/'switching_activity.rpt').read_text().splitlines():
        if not line.strip():continue
        match=pattern.fullmatch(line.strip());assert match,('Unexpected activity report',line)
        name,sp,sp_source,rate,rate_source,toggle,toggle_source=match.groups()
        assert sp_source==rate_source==toggle_source
        values=dict(static_probability=float(sp),signal_rate_Mtransitions_per_s=float(rate),
                    toggle_rate_percent=float(toggle),source=sp_source)
        activity[name]=values;types[sp_source]=types.get(sp_source,0)+1
        if sp_source=='S':
            key='tb_selective_route_replay/dut/'+name
            if key not in records:missing.append(name);continue
            t0,t1,tx,tz,tb,tc=records[key]
            assert tx==tz==tb==0,('Unknown physical activity',name)
            expected_sp=t1/check['duration_ps']
            expected_rate=tc/(check['duration_ps']*1e-12)/1e6
            assert abs(float(sp)-expected_sp)<=0.000001,('Mapped state mismatch',name)
            assert abs(float(rate)-expected_rate)<=max(0.00001,expected_rate*0.00001),('Mapped rate mismatch',name)
        elif sp_source=='C':
            assert name=='clk' or name.endswith('/clk')
            assert float(sp)==0.5 and abs(float(rate)-1000/3)<0.001
        elif sp_source=='D':
            assert '<const' in name or 'narrow_mode' in name
            assert float(sp) in (0,1) and float(rate)==float(toggle)==0
        else:raise AssertionError(('Unverified activity source',name,sp_source))
    assert not missing,('SAIF aliases need verification',missing)
    for signal in ('fixture/core/d/CEA20','fixture/core/d/CEP0','fixture/core/d/advance'):
        assert activity[signal]['source']=='S',('DSP enable not measured',signal)
    conditions=(directory/'operating_conditions.rpt').read_text()
    xpe=ET.parse(directory/'power_xpe.xml').getroot()
    assert xpe.attrib['design']==f"top_guard_add_selective_v{evidence['variant']}"
    device=xpe.find('ENVIRONMENT/DEVICE')
    assert device.attrib==dict(part='xc7a100t',grade='commercial',package='csg324',speed='-1',process='typical',vid='No')
    sources=xpe.findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')
    dynamic=sum(float(source.attrib['voltage'])*float(source.attrib['icc']) for source in sources)
    # Six decimals on each exported current and voltage; retain a rounding bound.
    rounding=sum(abs(float(source.attrib['voltage']))*0.5e-6+abs(float(source.attrib['icc']))*0.5e-6+0.25e-12 for source in sources)
    static=sum(float(source.attrib['voltage'])*float(source.attrib['iccq']) for source in sources)
    report=(directory/'power.rpt').read_text()
    coarse=float(re.search(r'\| Dynamic \(W\)\s*\|\s*([\d.]+)',report)[1])
    assert abs(dynamic-coarse)<=0.0005+rounding
    thermal=xpe.find('ENVIRONMENT/THERMAL')
    return dict(status='pass',variant=evidence['variant'],directory=str(directory),
        matched_physical_design_nets=int(matched[1]),physical_activity_source_counts=types,
        physical_activity_unknown_records=0,raw_unknown_records=check['raw_unknown_time_records'],
        excluded_unknown_scope='Only simulator internals/optimized aliases absent from verified physical S activity; constant nets inferred0/1 explicitly audited',
        native_interval_audit=check,critical_dsp_activity={name:activity[name] for name in activity if '/d/CE' in name or name.endswith('/d/advance')},
        dynamic_power_W=dynamic,dynamic_power_rounding_bound_W=rounding,device_static_W=static,
        dynamic_energy_J=dynamic*check['duration_ps']*1e-12,
        estimated_dynamic_energy_pJ_per_scalar_update=dynamic*check['duration_ps']/635904,
        voltage_sources=[source.attrib for source in sources],device_settings=device.attrib,
        thermal_settings={item.tag:item.attrib for item in thermal},
        clock_period_ns=6,power_xpe_sha256=sha(directory/'power_xpe.xml'),
        scope='Vendor estimated dynamic energy of complete219FF OOC fixture; not board measurement or core-only result')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay-dir',type=Path)
    parser.add_argument('--power-dir',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    assert bool(args.replay_dir)!=bool(args.power_dir)
    result=annotation(args.power_dir) if args.power_dir else replay(args.replay_dir)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
