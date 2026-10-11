"""Only low-memory native validation of pinned original-reference streams."""
from pathlib import Path
import argparse
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
ORIGINAL=P.parent/'residue_frontier_trial'
F5=P.parent/'residue_frontier_f5_trial'
COMMON=P.parent/'common_layout_trial'
sys.path.insert(0,str(P.parent/'selective_energy_trial'))
import run_selective_energy as base
from prepare_restored_work import pins,verify,sha

def source_pins():
    study=P.parent/'trained_reference_admission_study'
    paths=[Path(__file__),P/'CONTRACT.md',P/'prepare_restored_work.py',P/'verify_restored_native.py',
        P/'prepare_native_sources.py',P/'tb_restored_reference_compare.sv',P/'tb_source_provenance.json',
        P/'guard_add_static_narrow_eight.sv',P/'range_certificate.json',
        ORIGINAL/'guard_add_frontier.sv',F5/'guard_add_frontier_f5.sv',
        COMMON/'guard_add_selective.sv',COMMON.parent/'guard_add.sv',
        study/'manifest.json',study/'restored_reference_summary.json',base.P/'run_selective_energy.py']
    cert=base.read(P/'range_certificate.json')
    assert cert['status']=='pass_light_algebra_and_source_audit'
    assert sha(COMMON.parent/'guard_add.sv')==cert['guard_add_primitive_source_sha256']
    tb=base.read(P/'tb_source_provenance.json')
    assert sha(ORIGINAL/'tb_frontier_compare.sv')==tb['source_tb_sha256']
    assert sha(P/'tb_restored_reference_compare.sv')==tb['generated_tb_sha256']
    assert sha(P/'prepare_native_sources.py')==tb['generator_sha256']
    for model in cert['models']:
        assert sha(P.parent/'results'/f'model_seed{model["seed"]}.npz')==model['model_sha256']
        assert all(t>0 for values in model['thresholds_by_shift'].values()for t in values)
    # The original study manifest and original/F5 native proofs remain immutable.
    verify(base.read(study/'manifest.json')['files'])
    assert sha(ORIGINAL/'guard_add_frontier.sv')=='bf7ac4a24f3a2597084adb13972b79753b1fe280f06deb56b1b696a8da60495c'
    assert sha(F5/'guard_add_frontier_f5.sv')=='40bd9ae237af5a19321e658e113e31cf2edaece6f5c420939ac304f19627617f'
    assert sha(P/'guard_add_static_narrow_eight.sv')=='0e666457b6cfef459f0a5b1ed21beac94dfcc2c31b684dff0da036f593855373'
    return pins(paths)

def tool(argv,wd,label,stamps,gate):
    return base.job([str(arg).replace('\\','/')for arg in argv],wd,label,stamps,gate)

def native(shift,stall,attempt):
    stamps=source_pins();wd=P/'results'/f'native_shift{shift}_stall{stall}_a{attempt}'
    assert not wd.exists(),('Preserve attempt',wd);wd.mkdir(parents=True)
    tool([sys.executable,'-B',P/'prepare_restored_work.py','--shift',shift,'--directory',wd],wd,'prepare',stamps,.1)
    stamps|=pins([wd/'stream_stim.txt',wd/'reference_ledger.json',wd/'workload.json'])
    base.write(wd/'provenance.json',stamps)
    commands=[
        [base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}','-d','CAPTURE_TRACE=0',
         '-d',f'STATIC_COMPARATOR={int(shift==1)}',
         COMMON.parent/'guard_add.sv',COMMON/'guard_add_selective.sv',
         ORIGINAL/'guard_add_frontier.sv',F5/'guard_add_frontier_f5.sv',
         P/'guard_add_static_narrow_eight.sv',P/'tb_restored_reference_compare.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver',
         'tb_restored_reference_compare','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-R']]
    for k,command in enumerate(commands):tool(command,wd,f'tool_{k}',stamps,1.2)
    tool([sys.executable,'-B',P/'verify_restored_native.py','--directory',wd,'--shift',shift,
          '--stall',stall,'--output',wd/'native_checks.json'],wd,'verify',stamps,.1)
    verify(stamps);print('RESTORED NATIVE COMPLETE',shift,stall,flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true')
    ap.add_argument('--shift',type=int,choices=(1,3));ap.add_argument('--stall',type=int,choices=(0,1))
    ap.add_argument('--attempt',type=int,default=0);ap.add_argument('--all',action='store_true');a=ap.parse_args()
    assert a.run and a.attempt>=0
    if a.all:
        assert a.shift is None and a.stall is None
        for shift in (1,3):
            for stall in (0,1):native(shift,stall,a.attempt)
    else:
        assert a.shift is not None and a.stall is not None
        native(a.shift,a.stall,a.attempt)

if __name__=='__main__':main()
