"""Finish all registered frontier trials serially; fail closed on a missing check."""
from pathlib import Path
import argparse
import json
import sys
import time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
import run_frontier as run


def progress(stage,engine=None):
    run.write(P/'results/queue_progress.json',dict(stage=stage,engine=engine,unix_time=time.time()))
    print('QUEUE',stage,engine,flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true')
    parser.add_argument('--phase',choices=('native-route','energy'),required=True)
    args=parser.parse_args();assert args.run
    if args.phase=='native-route':
        for kind,stall in [('models',1),('main',0),('main',1)]:
            progress(f'native_{kind}_{stall}')
            run.native(kind,stall,0)
        run.functional()
        for engine in range(6):
            progress('route',engine);run.route(engine,0)
    else:
        for engine in range(6):
            route_dir=P/'results'/f'route_e{engine}_a0'
            hw=run.read(route_dir/'hardware.json')
            if hw['status']!='pass':
                progress('energy_blocked_by_timing',engine);continue
            progress('export',engine);run.export(engine,0,route_dir)
            export_dir=P/'results'/f'export_e{engine}_a0'
            progress('replay',engine);run.replay(engine,0,route_dir,export_dir)
            replay_dir=P/'results'/f'replay_e{engine}_a0'
            progress('power',engine);run.power(engine,0,route_dir,replay_dir)
            power_dir=P/'results'/f'power_e{engine}_a0'
            stamps=run.frozen()|run.sources()|run.functional()|run.pins([P/'audit_frontier_power.py',
                power_dir/'evidence.json',replay_dir/'replay_checks.json'])
            progress('audit',engine)
            run.tool([sys.executable,'-B',P/'audit_frontier_power.py','--power-dir',power_dir,
                '--output',power_dir/'power_audit.json'],power_dir,'audit',stamps,.1)
    progress('complete_'+args.phase)


if __name__=='__main__':main()
