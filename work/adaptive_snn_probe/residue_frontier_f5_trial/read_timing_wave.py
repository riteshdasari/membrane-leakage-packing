"""Extract the affected lane and register signals from preserved VCD evidence."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
file=P/'results/timing_diagnostic_f5_a0/waveform.vcd'
scope=[];signals={};selected={};events=[];time=0;header=True
with file.open() as stream:
    for line in stream:
        parts=line.split()
        if not parts:continue
        if header:
            if parts[0]=='$scope':scope.append(parts[2])
            elif parts[0]=='$upscope':scope.pop()
            elif parts[0]=='$var':
                code=parts[3];name='/'.join(scope+[parts[4]])
                signals.setdefault(code,[]).append(name)
                keep=('lane[3].full_lane.base' in name or 'result_data_reg[46]' in name or
                      'result_data[46]_i_1' in name or name in (
                        'tb_frontier_route_replay/clk','tb_frontier_route_replay/dut/fixture/src_u',
                        'tb_frontier_route_replay/dut/fixture/src_i',
                        'tb_frontier_route_replay/dut/fixture/core_data'))
                if keep:selected.setdefault(code,[]).append(name)
            elif parts[0]=='$enddefinitions':header=False
            continue
        if line[0]=='#':time=int(line[1:]);continue
        if not 8790000<=time<=8840000:continue
        if line[0] in 'bBrR':value,code=parts[0][1:],parts[1]
        else:value,code=parts[0][0],parts[0][1:]
        if code in selected:
            events.append(dict(time_ps=time,names=selected[code],value=value))
out=P/'results/timing_diagnostic_f5_a0/affected_lane_events.json'
assert not out.exists();out.write_text(json.dumps(events,indent=2)+'\n')
for event in events:
    name=event['names'][0]
    if ('/base' in name or '.base' in name) and '_reg' not in name and '_i_' not in name or 'result_data_reg[46]' in name:
        print(event['time_ps'],name,event['value'])
print('saved',len(events),'events',out)
