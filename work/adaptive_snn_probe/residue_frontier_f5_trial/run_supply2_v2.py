"""Complete F5 bandwidth control without editing agent-pinned source files."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import run_frontier_f5 as run
P=Path(__file__).resolve().parent


def main():
    assert '--run' in sys.argv
    wd=run.directory('supply2_models_0',0)
    stamps=run.frozen()|run.sources()|run.pins([Path(__file__),P/'prepare_frontier_work.py',
        P/'tb_frontier_supply2.sv',P/'verify_frontier.py',P/'verify_frontier_supply2_v2.py'])
    run.tool([sys.executable,'-B',P/'prepare_frontier_work.py','--kind','models','--directory',wd],wd,'prepare',stamps,.1)
    work=run.read(wd/'workload.json');requests=work['supply2_minimum_clocks']
    histogram={str(n):0 for n in range(1,9)}
    for group in work['group_boundaries']:
        histogram['2']+=group['neurons']//2;histogram['1']+=group['neurons']%2
    work['predicted_issues']=[dict(engine=e,requests=requests,take_histogram=histogram) for e in range(6)]
    work['delivery_cap']=2
    work['supply_scope']='Actual unchanged F5 cores; max two useful values supplied per cycle; no external memory circuit/window buffer cost.'
    run.write(wd/'workload.json',work);stamps|=run.pins([wd/'stream_stim.txt',wd/'workload.json'])
    run.write(wd/'provenance.json',stamps)
    commands=[
        [run.base.VIVADO/'bin/xvlog.bat','-sv','-d','STALL=0','-d','CAPTURE_TRACE=1',
         run.COMMON.parent/'guard_add.sv',run.COMMON/'guard_add_selective.sv',P/'guard_add_frontier_f5.sv',P/'tb_frontier_supply2.sv'],
        [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
        [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_frontier_compare','glbl','-s','sim'],
        [run.base.VIVADO/'bin/xsim.bat','sim','-R']]
    for n,cmd in enumerate(commands):run.tool(cmd,wd,f'tool_{n}',stamps,1.2)
    run.tool([sys.executable,'-B',P/'verify_frontier_supply2_v2.py','--directory',wd,
        '--kind','models','--stall',0,'--output',wd/'frontier_checks.json'],wd,'verify',stamps,.1)
    check=run.read(wd/'frontier_checks.json')
    assert all(r['requests']==317952 and r['service_clocks']==354816 for r in check['rows'])
    print('F5 SUPPLY2 COMPLETE all6 engines 354816 clocks',flush=True)


if __name__=='__main__':main()
