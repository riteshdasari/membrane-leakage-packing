"""Seven uniform timing replays, two simulators, one Vivado power job at a time."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import importlib.util
import sys
import time
sys.dont_write_bytecode=True
import run_frontier as original
P=Path(__file__).resolve().parent
F5=P.parent/'residue_frontier_f5_trial'
sys.path.insert(0,str(F5))
import run_frontier_f5 as sibling


def replay_worker(family,engine,run):
    attempt=3 if family=='original' else 1
    directory=run.P/'results'/f'replay_e{engine}_a{attempt}'
    assert not directory.exists()
    # The runner itself creates and owns the replay directory and provenance.
    # Avoid a second wrapper job that would introduce mutable activity hashes.
    module_path=run.P/'run_frontier_replay_transport_v4.py'
    spec=importlib.util.spec_from_file_location(f'{family}_transport_replay',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.replay(engine,attempt,run.P/'results'/f'route_e{engine}_a0',
                  run.P/'results'/f'export_e{engine}_a{0 if family=="original" else 1}')
    return directory


def main():
    assert '--run' in sys.argv
    jobs=[('original',2,original),('f5',5,sibling),('original',3,original),
          ('original',0,original),('original',1,original),('original',4,original),
          ('original',5,original)]
    failures=[];finished=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(replay_worker,*job):job for job in jobs}
        for future in as_completed(futures):
            family,engine,run=futures[future]
            try:
                replay_dir=future.result()
                print('TRANSPORT REPLAY ACCEPTED',family,engine,flush=True)
                # No worker launches Vivado. Power is serial in this main loop.
                attempt=1
                run.power(engine,attempt,run.P/'results'/f'route_e{engine}_a0',replay_dir)
                pd=run.P/'results'/f'power_e{engine}_a{attempt}'
                stamps=run.frozen()|run.sources()|run.functional()|run.pins([
                    Path(__file__),P/'SCHEDULING_ADDENDUM.md',P/'TIMING_SIMULATION_CORRECTION.md',
                    run.P/'audit_frontier_power_v4.py',pd/'evidence.json',replay_dir/'replay_checks.json'])
                run.tool([sys.executable,'-B',run.P/'audit_frontier_power_v4.py',
                          '--power-dir',pd,'--output',pd/'power_audit.json'],pd,'audit_v4',stamps,.1)
                finished.append(dict(family=family,engine=engine,power_dir=str(pd)))
                print('TRANSPORT POWER AUDIT PASS',family,engine,flush=True)
            except Exception as exc:
                failures.append(dict(family=family,engine=engine,error=repr(exc)))
                print('TRANSPORT JOB FAILED',family,engine,repr(exc),flush=True)
            original.write(P/'results/transport_energy_v6_progress.json',dict(
                completed=finished,failures=failures,total=7,unix_time=time.time()))
    assert not failures,failures
    assert len(finished)==7
    print('ALL SEVEN TRANSPORT TIMING AND POWER AUDITS PASS',flush=True)


if __name__=='__main__':main()
