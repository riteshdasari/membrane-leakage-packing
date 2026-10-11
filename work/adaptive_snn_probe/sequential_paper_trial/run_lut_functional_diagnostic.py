"""Map-versus-delay diagnostic after failed LUT SDF replay; not an energy result."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
import run_stage4_energy9_v2 as run
def main():
    rd,hw=run.route(2);wd=run.directory('lut_functional_diagnostic')
    stamps=run.sources()|run.pins([Path(__file__),P/'export_lut_functional.tcl',rd/'hardware.json',rd/'design.dcp'])
    run.write(wd/'export_provenance.json',stamps)
    log=run.tool([run.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'export_lut_functional.tcl','-tclargs',rd/'design.dcp',wd],wd,'export',stamps,2.3)
    assert 'LUT_FUNCTIONAL_EXPORT PASS'in log.read_text()
    check,row,trace,total=run.native(2);stamps.update(run.pins([wd/'functional.v',check,trace]))
    try:
        d=run.simulation(2,wd,[wd/'functional.v'],stamps,trace,total,row['first_accept'],row['last_retire'],False)
        run.write(wd/'diagnostic.json',d|dict(status='functional_mapping_pass',accepted_timing=False,accepted_energy=False,scope='Exact complete mapped-functional trace diagnostic only; no SDF and no power claim'))
        print('LUT MAPPED FUNCTIONAL DIAGNOSTIC PASS',flush=True)
    except Exception as exc:
        run.write(wd/'diagnostic.json',dict(status='functional_mapping_failed',reason=repr(exc),accepted_timing=False,accepted_energy=False,source_sha256=stamps));raise
if __name__=='__main__':main()
