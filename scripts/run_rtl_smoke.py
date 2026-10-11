from pathlib import Path
import shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];build=ROOT/'.build/rtl_smoke';build.mkdir(parents=True,exist_ok=True)
for command in ('iverilog','vvp'):
    if not shutil.which(command):raise SystemExit(f'{command} is required on PATH for the optional behavioral RTL smoke test')
subprocess.run(['iverilog','-g2012','-s','tb_smoke','-o',str(build/'smoke.vvp'),str(ROOT/'rtl/leak_core16.sv'),str(ROOT/'examples/behavioral_dsp.sv'),str(ROOT/'examples/tb_smoke.sv')],check=True)
subprocess.run(['vvp',str(build/'smoke.vvp')],check=True)
