"""Two low-memory timing replays; one serial Vivado export/power job at a time."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
import run_frontier as run
import run_frontier_replay_startup_v2 as replay_v2
P=Path(__file__).resolve().parent


def progress(stage,engine=None):
    run.write(P/'results/parallel_energy_progress.json',dict(stage=stage,engine=engine,unix_time=time.time()))
    print('PARALLEL ENERGY',stage,engine,flush=True)


def main():
    assert '--run' in sys.argv
    failed=P/'results/replay_e0_a0'
    text=(failed/'xsim.log').read_text()
    assert 'Timing violation' in text and 'at time 3 ns' in text
    # The old queue is guaranteed to reject that warning before starting E1.
    futures={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for e in range(6):
            rd=P/'results'/f'route_e{e}_a0'
            assert run.read(rd/'hardware.json')['status']=='pass'
            xd=P/'results'/f'export_e{e}_a0'
            if xd.exists():run.verify(run.read(xd/'artifacts.json'))
            else:progress('export',e);run.export(e,0,rd)
            progress('replay_submitted',e)
            futures[pool.submit(replay_v2.replay,e,1,rd,xd)]=e
        for future in as_completed(futures):
            e=futures[future];future.result()
            rd=P/'results'/f'route_e{e}_a0';sd=P/'results'/f'replay_e{e}_a1'
            progress('power',e);run.power(e,0,rd,sd)
            pd=P/'results'/f'power_e{e}_a0'
            stamps=run.frozen()|run.sources()|run.functional()|run.pins([Path(__file__),
                P/'SCHEDULING_ADDENDUM.md',P/'audit_frontier_power.py',pd/'evidence.json',sd/'replay_checks.json'])
            progress('audit',e)
            run.tool([sys.executable,'-B',P/'audit_frontier_power.py','--power-dir',pd,
                      '--output',pd/'power_audit.json'],pd,'audit',stamps,.1)
    progress('complete')


if __name__=='__main__':main()
