"""F5 two-value work cap plus actual hardware policy on idle/prelude rows."""
from pathlib import Path
import verify_frontier as checker
from prepare_frontier_work import take_for as hardware_take
original_audit=checker.audit_trace


def audit_trace(path,engine,groups):
    for line in Path(path).open():
        fields=line.split()
        if int(fields[1]) and int(fields[4]) and int(fields[9]):
            assert 1<=int(fields[6])<=2
    limited_take=checker.take_for
    checker.take_for=hardware_take
    try:return original_audit(path,engine,groups)
    finally:checker.take_for=limited_take


checker.take_for=lambda engine,pairs,pos:min(2,len(pairs)-pos)
checker.audit_trace=audit_trace
if __name__=='__main__':checker.main()
