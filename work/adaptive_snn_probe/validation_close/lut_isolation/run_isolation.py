"""Serial gated diagnostic only. Requires explicit --run; no route or power."""
from pathlib import Path
import argparse
import json
import re
import shutil
import sys

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent.parent/'selective_energy_trial'))
import run_selective_energy as b

ap=argparse.ArgumentParser()
ap.add_argument('--run',action='store_true')
ap.add_argument('--attempt',type=int,default=0)
ap.add_argument('--pulse-defaults',action='store_true')
args=ap.parse_args()
assert args.run,'No vendor tools launch without --run.'
wd=P/f'run_a{args.attempt}'
assert not wd.exists(),'Retain previous attempts; choose another number.'
wd.mkdir()
for name in ['CARRY4_vendor.v','tb_minimal_carry.sv','carry_original_paths.sdf','run.tcl']:
    shutil.copyfile(P/name,wd/name)
stamps=b.pins([Path(__file__),P/'preparation.json',*list(wd.glob('*.*')),b.VIVADO/'data/verilog/src/glbl.v'])
b.write(wd/'provenance.json',stamps)
pulse=[] if args.pulse_defaults else ['-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0']
commands=[
 [b.VIVADO/'bin/xvlog.bat','-d','XIL_TIMING',wd/'CARRY4_vendor.v'],
 [b.VIVADO/'bin/xvlog.bat','-sv',wd/'tb_minimal_carry.sv'],
 [b.VIVADO/'bin/xvlog.bat',b.VIVADO/'data/verilog/src/glbl.v'],
 [b.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays',*pulse,'-L','work','-L','simprims_ver','-L','secureip','-L','unisims_ver','tb_minimal_carry','glbl','-s','sim'],
 [b.VIVADO/'bin/xsim.bat','sim','-tclbatch',wd/'run.tcl'],
 [b.VIVADO/'bin/xvlog.bat','-sv','-d','OMIT_SDF',wd/'tb_minimal_carry.sv'],
 [b.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays',*pulse,'-L','work','-L','simprims_ver','-L','secureip','-L','unisims_ver','tb_minimal_carry','glbl','-s','functional'],
 [b.VIVADO/'bin/xsim.bat','functional','-tclbatch',wd/'run.tcl'],
]
logs=[]
for i,command in enumerate(commands):
    logs.append(b.job([str(x).replace('\\','/')for x in command],wd,f'tool_{i}',stamps,0.6))
summary={'status':'completed_diagnostic_not_hardware_acceptance',
         'maxdelay':True,'transport_int_delays':True,'pulse_filter':'vendor_defaults' if args.pulse_defaults else 'all_0_original',
         'vendor_source_modified':False,'timing_checks_disabled':False,
         'tool_artifact_sha256':b.pins(logs),'cases':[]}
assert 'SDF backannotation was successful' in logs[3].read_text(errors='replace'), 'SDF must be accepted.'
assert '$sdf_annotate will be ignored' not in logs[3].read_text(errors='replace'), 'SDF was ignored.'
for kind,log in [('SDF',logs[4]),('functional_control',logs[7])]:
    text=log.read_text(errors='replace')
    match=re.search(r'ISOLATION_COMPLETE cases=(\d+) failures=(\d+)',text)
    assert match,'Missing completion marker'
    summary['cases'].append({'kind':kind,'checks':int(match[1]),'failures':int(match[2]),
                             'failure_lines':[x for x in text.splitlines() if x.startswith('ISOLATED_FAILURE')]})
b.write(wd/'diagnostic.json',summary)
print(json.dumps({k:v for k,v in summary.items() if not k.endswith('sha256')},indent=2),flush=True)
