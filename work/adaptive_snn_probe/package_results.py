"""Package source and small verification reports, excluding tool working databases."""
from pathlib import Path
import json,re,hashlib,zipfile
here=Path(__file__).resolve().parent
out=here.parent.parent/'outputs'
metrics={}
for folder in sorted((here/'results').glob('*_route')):
 if not (folder/'slack.txt').exists():continue
 text=(folder/'util.rpt').read_text()
 vals={}
 for label,key in [('Slice LUTs','luts'),('Slice Registers','ffs'),('DSPs','dsps')]:
  vals[key]=int(re.search(r'^\| '+label+r'\s*\|\s*(\d+)',text,re.M).group(1))
 vals['target_ns']=4.;vals['wns_ns']=float((folder/'slack.txt').read_text())
 vals['target_minus_slack_mhz_estimate']=1000/(4-vals['wns_ns'])
 metrics[folder.name]=vals
(here/'results'/'hardware_metrics.json').write_text(json.dumps(metrics,indent=2))
readme='''# Reproduce adaptive SNN trials

Python needs NumPy. Original run used Python from C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe and local Vivado 2025.2. No downloads were performed.

- `python probe.py`: trains three digits models; tests integer traces and physical packed arithmetic; saves numerical.json. Takes several minutes.
- `python final_selected.py`: refreshes trained-model scheduling models for the registered guard and saves model arrays.
- `python stress_selected.py`: final burst scheduling tests, including native-current range checks.
- `python stress_probe.py`: larger exploratory synthetic sweep.
- `python promote_probe.py`: membrane-seeded promotion lower-bound model, not migration RTL.
- Set PowerShell `$env:PIPE='1'`, then run `python check_shared.py` for final UNISIM checks. Unset PIPE, set REUSE=1 for DSP-reuse tests. Edit VIV in check_shared.py for another Vivado path.
- Final RTL: guard_acc.sv + old_acc_engines.sv + shared_neuron_pipe.sv. Core uses registered warning, two-event headroom, and a single write bus.
- synth_batch.tcl takes module names as tclargs. synth_lut24.tcl handles the direct LUT baseline. Use `vivado -mode batch -log results/run.log -journal results/run.jou -source synth_batch.tcl -tclargs top_guard_pipe top_native_pipe top_reuse_shared`. Log/journal arguments must precede tclargs.
- route_probe.tcl opens generated synthesis checkpoints; pass the same top names to route them. DCP files are excluded from this bundle and must be regenerated.
- shared_neuron.sv and *_v1 artifacts are intermediate trials. top_margin_acc is the combinational-warning accumulate-only wrapper; it is not the final registered-warning neuron pipeline.

JSON cycle ratios are abstract scheduling models, not measured accelerator latency. rtl_checks_pipe.json is actual cluster simulation cycle counting. Reports are out-of-context local cores without a complete input distributor/SRAM integration. Check the accompanying trial report for comparisons and limitations.

The original source was copied for reference; no original Desktop files were modified. SHA256SUMS.txt verifies packaged contents.
'''
(here/'README_REPRODUCE.md').write_text(readme)
files=[]
for p in here.iterdir():
 if p.is_file() and (p.suffix in ('.py','.sv','.tcl','.md','.txt') or p.name=='digits.csv.gz'):files.append(p)
for p in (here/'results').rglob('*'):
 if p.is_file() and (p.suffix in ('.json','.npz') or p.name in ('util.rpt','timing.rpt','slack.txt','cycles.txt')):files.append(p)
files=sorted(set(files))
manifest='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(here).as_posix() for p in files)+'\n'
manifest+=hashlib.sha256((out/'adaptive_snn_trials.md').read_bytes()).hexdigest()+'  adaptive_snn_trials.md\n'
with zipfile.ZipFile(out/'adaptive_snn_trials.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.relative_to(here).as_posix())
 z.writestr('SHA256SUMS.txt',manifest)
 z.write(out/'adaptive_snn_trials.md','adaptive_snn_trials.md')
print(json.dumps(metrics,indent=2));print('Packaged',len(files),'files', (out/'adaptive_snn_trials.zip').stat().st_size,'bytes')
