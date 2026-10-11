"""Repair XSim's escaped Verilog-identifier wrapper in a separate SAIF copy.

Only NET identifier tokens are changed. Every state/time/transition record,
hierarchy, duration and original file remains unchanged. No invented activity.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def normalize(source,target):
    source,target=Path(source).resolve(),Path(target).resolve()
    assert source!=target and not target.exists()
    original=source.read_text()
    changed=[]
    lines=[]
    pattern=re.compile(r'^(\s*\()([^\s]+)(\s+\(T0\s+.*)$')
    for number,line in enumerate(original.splitlines(keepends=True),1):
        match=pattern.match(line.rstrip('\r\n'))
        if match:
            name=match[2]
            if name.startswith('\\\\') and name.endswith('\\'):
                canonical=name[2:-1]
                assert canonical
                newline=line[len(line.rstrip('\r\n')):]
                line=match[1]+canonical+match[3]+newline
                changed.append(dict(line=number,old=name,new=canonical))
        lines.append(line)
    corrected=''.join(lines)
    # Verify the exact ordered list of every simulator-emitted numeric record.
    activity=r'\(T0\s+\d+\).*?\(TC\s+\d+\)'
    assert re.findall(activity,original)==re.findall(activity,corrected)
    assert re.findall(r'\((?:TIMESCALE|DURATION).*?\)',original)==re.findall(r'\((?:TIMESCALE|DURATION).*?\)',corrected)
    assert [line for line in original.splitlines() if '(INSTANCE' in line]==[
        line for line in corrected.splitlines() if '(INSTANCE' in line]
    assert changed
    target.write_text(corrected,encoding='utf-8',newline='')
    result=dict(status='name-only repair; annotation audit still required',
        source=str(source),source_sha256=sha(source),target=str(target),target_sha256=sha(target),
        script_sha256=sha(__file__),changed_net_tokens=len(changed),changes=changed,
        ordered_numeric_records_unchanged=True,hierarchy_unchanged=True,duration_unchanged=True)
    target.with_suffix('.names.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('target',type=Path)
    args=parser.parse_args()
    result=normalize(args.source,args.target)
    print({key:result[key] for key in ('status','changed_net_tokens','source_sha256','target_sha256')})

if __name__=='__main__':main()
