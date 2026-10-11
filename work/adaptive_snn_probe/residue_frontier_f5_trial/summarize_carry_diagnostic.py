"""Record settled-pin consistency without changing vendor models or SDF."""
from pathlib import Path
import hashlib
import json
P=Path(__file__).resolve().parent
V=P/'results/timing_diagnostic_f5_o0_a0/waveform.vcd'
D=P/'results/timing_diagnostic_f5_o0_a0'
suffix='lane[3].full_lane.base0_reg[6]_i_1'
scope=[];selected={};events=[];values={};time=0;header=True
with V.open() as f:
    for line in f:
        parts=line.split()
        if not parts:continue
        if header:
            if parts[0]=='$scope':scope.append(parts[2])
            elif parts[0]=='$upscope':scope.pop()
            elif parts[0]=='$var' and scope and scope[-1].endswith(suffix):
                selected[parts[3]]=parts[4]
            elif parts[0]=='$enddefinitions':header=False
            continue
        if line[0]=='#':
            time=int(line[1:])
            if time>8810000:break
            continue
        if line[0] in 'bBrR':value,code=parts[0][1:],parts[1]
        else:value,code=parts[0][0],parts[0][1:]
        if code in selected:
            name=selected[code];values[name]=value
            if 8805000<=time:events.append(dict(time_ps=time,name=name,value=value))
assert selected and all(k in values for k in ('S_in','DI_in','CI_in','CYINIT_in','CO_fb','O','CO'))
bits=lambda name:int(values[name],2)
s,di,ci=bits('S_in'),bits('DI_in'),bits('CI_in')|bits('CYINIT_in')
expected_o=expected_co=0
carry=ci
for b in range(4):
    expected_o|=(((s>>b)&1)^carry)<<b
    carry=carry if (s>>b)&1 else (di>>b)&1
    expected_co|=carry<<b
latest_input=max(e['time_ps'] for e in events if e['name'] in ('S_in','DI_in','CI_in','CYINIT_in'))
log=(D/'tool_3.log').read_text()
result=dict(status='retained_timing_replay_mismatch',sample_time_ps=8810000,
    settled_input_duration_ps=8810000-latest_input,selected_primitive=suffix,
    pins=values,expected_settled_O=expected_o,actual_O=bits('O'),
    expected_settled_CO=expected_co,actual_CO=bits('CO'),
    settled_boolean_consistency=(expected_o==bits('O') and expected_co==bits('CO')),
    full_SDF_and_checks_retained=True,elaboration_optimization_disabled=True,
    same_full_replay_assertion_failed='Fatal: REPLAY data mismatch V5 row1450' in log,
    interpretation='The local timing primitive fails settled Boolean consistency in this replay. This supports a timing-model/event-scheduling diagnosis, but is not a verified vendor bug or proof of board correctness. No adaptive energy is accepted.',
    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),V,D/'tool_2.job.json',D/'tool_3.log')},
    events=events)
out=D/'settled_carry_consistency.json';assert not out.exists()
out.write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items() if k not in ('source_sha256','events','pins')})
