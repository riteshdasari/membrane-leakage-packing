from pathlib import Path
import zipfile,hashlib,json
p=Path(__file__).resolve().parent
out=p.parents[1]/'outputs';out.mkdir(exist_ok=True)
files=[p/x for x in ['fixed_pair.sv','tb_fixed_pair.sv','check_fixed_pair.py','route_fixed_pair.tcl','run_fixed_pair_route.py','package_fixed_pair.py','results/fixed_pair_checks.json']]
for d in sorted((p/'results').glob('fixed_pair_[0-9]*')):
 files.extend(d/x for x in ['stim.txt','expected.txt','out0.txt','out1.txt','out2.txt','out3.txt','last_tool_output.txt'])
for d in sorted((p/'results').glob('top_pair*_route')):
 files.extend(d/x for x in ['util.rpt','timing.rpt','paths.rpt','slack.txt']if (d/x).exists())
for d in sorted((p/'results').glob('top_pair*_synth')):
 files.append(d/'util.rpt')
files.extend((p/'results').glob('top_pair*_build.log'))
if (p/'results/fixed_pair_hardware.json').exists():files.append(p/'results/fixed_pair_hardware.json')
entries={str(f.relative_to(p)).replace('\\','/'):f.read_bytes()for f in files}
entries['README.md']=(out/'fixed_pair_implementation.md').read_bytes()
entries['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(b).hexdigest()}  {n}\n'for n,b in entries.items()).encode()
dest=out/'fixed_pair_implementation.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in entries.items():z.writestr(n,b)
with zipfile.ZipFile(dest)as z:
 assert z.testzip()is None
 for n,b in entries.items():assert z.read(n)==b
(out/'fixed_pair_checks.json').write_bytes((p/'results/fixed_pair_checks.json').read_bytes())
(out/'fixed_pair_hardware.json').write_bytes((p/'results/fixed_pair_hardware.json').read_bytes())
print(dest,len(entries),dest.stat().st_size)
