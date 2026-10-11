"""Root continuation of prepared U13 exactness checks; fresh attempt only."""
from pathlib import Path
import argparse
import sys
sys.dont_write_bytecode=True
import run_u13_physical as run
P=Path(__file__).resolve().parent

def native(kind,stall,attempt):
    stamps=run.frozen()|run.sources()|run.pins([Path(__file__),P/'prepare_u13_work.py',
        P/'verify_frontier_u13.py',P/'tb_frontier_u13_compare.sv',P/'tb_preparation.json'])
    tb=run.read(P/'tb_preparation.json')
    for prefix in ('source','generator','output'):
        assert run.sha(Path(tb[prefix+'_file']))==tb[prefix+'_sha256']
    wd=run.directory(f'native_{kind}_{stall}',attempt)
    run.tool([sys.executable,'-B',P/'prepare_u13_work.py','--kind',kind,'--directory',wd],wd,'prepare',stamps,.1)
    stamps|=run.pins([wd/'stream_stim.txt',wd/'workload.json'])
    run.write(wd/'provenance.json',stamps)
    commands=[
        [run.base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}',
         '-d',f'CAPTURE_TRACE={int(kind=="models" and stall==0)}',
         P.parent/'guard_add.sv',P/'guard_add_frontier_u13.sv',P/'tb_frontier_u13_compare.sv'],
        [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
        [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver',
         'tb_frontier_u13_compare','glbl','-s','sim'],
        [run.base.VIVADO/'bin/xsim.bat','sim','-R']]
    for n,command in enumerate(commands):run.tool(command,wd,f'tool_{n}',stamps,1.2)
    run.tool([sys.executable,'-B',P/'verify_frontier_u13.py','--directory',wd,'--kind',kind,
        '--stall',stall,'--output',wd/'frontier_checks.json'],wd,'verify',stamps,.1)
    run.verify(stamps)
    print('U13 NATIVE COMPLETE',kind,stall,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true')
    ap.add_argument('--all',action='store_true');ap.add_argument('--kind',choices=('main','models'))
    ap.add_argument('--stall',type=int,choices=(0,1));ap.add_argument('--attempt',type=int,default=0)
    a=ap.parse_args();assert a.run and a.attempt>=0
    if a.all:
        assert a.kind is None and a.stall is None
        for kind in ('models','main'):
            for stall in (0,1):native(kind,stall,a.attempt)
    else:
        assert a.kind is not None and a.stall is not None
        native(a.kind,a.stall,a.attempt)
