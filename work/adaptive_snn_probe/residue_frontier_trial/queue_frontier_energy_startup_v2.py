"""Finish all six energy audits after preserving startup-invalid E0 replay."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import run_frontier as run
import run_frontier_replay_startup_v2 as replay_v2
from queue_frontier import progress
P=Path(__file__).resolve().parent


def main():
    assert '--run' in sys.argv
    failed=run.read(P/'results/replay_e0_a0/replay_checks.json')
    assert failed['status']=='invalid' and failed['timing_diagnostics']
    assert all('at time 3 ns' in x['line'] for x in failed['timing_diagnostics'])
    for e in range(6):
        rd=P/'results'/f'route_e{e}_a0';hw=run.read(rd/'hardware.json')
        if hw['status']!='pass':progress('energy_blocked_by_timing',e);continue
        xd=P/'results'/f'export_e{e}_a0'
        if xd.exists():run.verify(run.read(xd/'artifacts.json'))
        else:progress('export',e);run.export(e,0,rd)
        progress('replay_startup_v2',e);replay_v2.replay(e,1,rd,xd)
        sd=P/'results'/f'replay_e{e}_a1'
        progress('power',e);run.power(e,0,rd,sd)
        pd=P/'results'/f'power_e{e}_a0'
        stamps=run.frozen()|run.sources()|run.functional()|run.pins([Path(__file__),
            P/'audit_frontier_power.py',pd/'evidence.json',sd/'replay_checks.json'])
        progress('audit',e)
        run.tool([sys.executable,'-B',P/'audit_frontier_power.py','--power-dir',pd,
                  '--output',pd/'power_audit.json'],pd,'audit',stamps,.1)
    progress('complete_energy_startup_v2')


if __name__=='__main__':main()
