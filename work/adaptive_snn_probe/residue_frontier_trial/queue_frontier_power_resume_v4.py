"""Finish every existing timing replay's power using explicit-top attribution."""
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
import run_frontier as run
P=Path(__file__).resolve().parent


def main():
    assert '--run' in sys.argv
    assert run.read(P/'results/power_e0_a0/audit.job.json')['returncode']!=0
    assert 'too many values to unpack' in (P/'results/power_e0_a0/audit.log').read_text()
    for e in range(6):
        print('POWER RESUME WAIT',e,flush=True)
        rd=P/'results'/f'route_e{e}_a0';sd=P/'results'/f'replay_e{e}_a1'
        while not (sd/'replay_checks.json').exists():
            failure=sd/'tool_3.job.json'
            if failure.exists():assert run.read(failure)['returncode']==0
            time.sleep(2)
        replay=run.read(sd/'replay_checks.json')
        assert replay['status']=='timing_pass_activity_pending' and not replay['timing_diagnostics']
        while not (sd/'activity_named.names.json').exists():time.sleep(1)
        pd=P/'results'/f'power_e{e}_a0'
        if pd.exists():
            assert e==0 and (pd/'evidence.json').exists()
            evidence=run.read(pd/'evidence.json')
            run.verify(evidence['source_sha256']);run.verify(evidence['artifact_sha256'])
        else:run.power(e,0,rd,sd)
        stamps=run.frozen()|run.sources()|run.functional()|run.pins([Path(__file__),
            P/'SCHEDULING_ADDENDUM.md',P/'audit_frontier_power_v2.py',pd/'evidence.json',sd/'replay_checks.json'])
        print('POWER RESUME AUDIT',e,flush=True)
        run.tool([sys.executable,'-B',P/'audit_frontier_power_v2.py','--power-dir',pd,
                  '--output',pd/'power_audit.json'],pd,'audit_v2',stamps,.1)
    print('ALL SIX FRONTIER POWER AUDITS PASS',flush=True)


if __name__=='__main__':main()
