"""Publish matched exact RTL measurements and a reproducible, hashed source bundle."""
from pathlib import Path
import json,re,hashlib,zipfile
import numpy as np
here=Path(__file__).resolve().parent
out=here.parent.parent/'outputs';out.mkdir(exist_ok=True)
names={0:'Version 1: current checkpoint',1:'Version 3: membrane promotion',2:'Native FOUR12',3:'Fixed six-lane current',4:'Parallel LUT-only'}
tops=['top_exact_checkpoint','top_exact_promote','top_exact_native','top_exact_static','top_exact_lut']
rtl=json.loads((here/'results/exact_tile_checks.json').read_text())
inference=json.loads((here/'results/exact_inference.json').read_text())
assert len(rtl)==54 and all(r['mismatch_rows']==0 and r['timesteps']==120 for r in rtl)
assert len(inference['models'])==36
assert all(r['state_disagreements']==r['spike_disagreements']==r['prediction_disagreements']==0 for r in inference['models'])
metrics={}
static_bounds={}
for seed in range(3):
    saved=np.load(here/'results'/f'model_seed{seed}.npz')
    static_bounds[str(seed)]=[]
    for key in ['w0','w1']:
        weights=saved[key]
        lo=int(np.minimum(weights,0).sum(0).min());hi=int(np.maximum(weights,0).sum(0).max())
        assert -128<=lo and hi<=127
        static_bounds[str(seed)].append({'layer':key,'min_prefix_lower_bound':lo,'max_prefix_upper_bound':hi})
for i,top in enumerate(tops):
    folder=here/'results'/f'{top}_route'
    raw=(folder/'util.rpt').read_text()
    vals={}
    for label,key in [('Slice LUTs','luts'),('Slice Registers','ffs'),('DSPs','dsps'),('Block RAM Tile','bram_tiles')]:
        match=re.search(r'^\| '+label+r'\*?\s*\|\s*(\d+(?:\.\d+)?)',raw,re.M)
        assert match,label
        vals[key]=float(match[1]) if key=='bram_tiles' else int(match[1])
    vals.update(name=names[i],target_ns=4.0,wns_ns=float((folder/'slack.txt').read_text()),mode=i)
    assert vals['dsps']==([4,4,6,4,0][i])
    metrics[top]=vals
bundle={'scope':'Matched 24-neuron B16/int4 OOC timing shells; no full accelerator/host/power measurement',
        'fpga':'xc7a100tcsg324-1','tool':'Vivado 2025.2','hardware':metrics,'rtl_checks':rtl,'inference':inference,
        'static_current_bounds_binary_spikes_once_per_input_per_timestep':static_bounds}
(out/'exact_snn_results.json').write_text(json.dumps(bundle,indent=2))
intro='''# Exact adaptive SNN packing: implementations and matched baselines

Checked 8 October 2026. Both selected versions are implemented and pass numerical and real-DSP RTL checks. The current-checkpoint version saves DSPs relative to native FOUR12 but costs stalls. The membrane-promotion version is exact and genuinely membrane-aware, but its present shared wide fallback is substantially slower. Neither has yet demonstrated an end-to-end advantage over the strongest applicable fixed/fabric baseline.

## New matched FPGA measurements

Every core handles 24 neurons with int4 event weights and a 16-bit state. These are newly synthesized and routed cores with matching global-ready input semantics; the older 13-bit experiments are not mixed into these numbers. The default hardware configuration is LIF shift 1, subtractive reset and threshold 35. These configurations are arithmetic microbenchmarks, not the model-specific calibrated thresholds used in numerical inference.

'''
for top,v in metrics.items():
    intro+=f"- **{v['name']}:** {v['luts']} LUTs, {v['ffs']} FFs, {v['dsps']} DSPs, {v['bram_tiles']:g} BRAMs; routed setup WNS {v['wns_ns']:+.3f} ns at a 4 ns target.\n"
intro+='''
Negative slack means the target is not met. These are out-of-context setup reports without board I/O constraints; they are not signoff timing, a clock sweep, measured Fmax or board operation at 250 MHz. Internal register banks, supplied weights and timing-shell registers are included; a full network's weights/SRAM/distributor/host are not.

The current-checkpoint critical path runs from a group's controller state through readiness gating to another group's DSP OPMODE control. The warning register avoids a direct combinational alarm loop, but the common input barrier still creates a cross-group control path. Promotion additionally needs membrane seeding/range checks and wide-path selection; its extra LUT cost and serialized wide updates explain why packing density alone is an insufficient hardware metric.

## Actual RTL cycle comparison

Cycles include accepted leakage, event and finish commands plus controller waits, over 120 timesteps. An event vector updates all 24 neurons. The following comparison uses identical stimulus and independent valid/ready drivers for each engine; it is not the earlier idealized sum of independent group schedules. Clock-period differences and end-to-end host latency are not folded into these cycle counts.

'''
for bounded in (False,True):
    selected=[r for r in rtl if r['shift']==1 and r['leak']==1 and r['hard_reset']==0 and r['bounded_current']==bounded]
    intro+=f"{'Bounded-current' if bounded else 'Burst-stress'} stream: {selected[0]['cycles'][1]} accepted event vectors; maximum absolute current prefix {selected[0]['max_abs_current_prefix']}.\n\n"
    for r in selected:
        intro+=f"- {names[r['mode']]}: **{r['cycles'][0]:,} clocks**, {r['cycles'][2]:,} input-busy clocks.\n"
    intro+='\n'
stress=[r for r in rtl if not r['bounded_current'] and r['shift']==1 and r['leak']==1 and r['hard_reset']==0]
cycles={r['mode']:r['cycles'][0] for r in stress}
intro+=f"On this burst stream, version 1 takes {cycles[0]/cycles[2]:.2f} times the native core's clocks; version 3 takes {cycles[1]/cycles[2]:.2f} times. Version 1 uses {metrics[tops[0]]['dsps']} rather than {metrics[tops[2]]['dsps']} DSPs, a one-third saving, but this is not a latency win. The LUT baseline is fastest at {cycles[4]:,} clocks.\n\n"
prom=[r['cycles'][0] for r in rtl if not r['bounded_current'] and r['mode']==1]
intro+=f"Across the six leak/reset settings, membrane-promotion burst cost spans {min(prom):,}–{max(prom):,} clocks. Hard reset can alter membrane residency but does not make the present shared wide path fast. Fixed six-lane packing is excluded from the unbounded-current correctness/latency comparison because its range contract is violated. It does pass all bounded-current checks.\n\n"
intro+='''For these particular microcores, LUT-only has the lowest LUT, FF and DSP counts and the fewest clocks in both streams. Both adaptive designs therefore lose to it on these measured dimensions. None of the five cores meets the 4 ns setup target in this run; timing closure remains future implementation work. This result supports using LUT-only as the main local performance/resource baseline, not merely listing it as an optional alternative.

'''
report=intro+(here/'exact_report_body.md').read_text()
(out/'exact_snn_implementation_and_baselines.md').write_text(report,encoding='utf-8')
readme='''# Reproduce the two exact SNN engines

Python needs NumPy; Vivado 2025.2 was used on Windows. No model, dataset or package download was performed. Original Desktop source files were not modified. Dataset/model snapshots needed for existing inference are included.

1. `python exact_inference.py`: all 36 full-test inference comparisons, using saved int4 models/calibrated thresholds. Does not retrain or require a board. Results: `results/exact_inference.json`.
2. `python check_exact_tiles.py`: 54 matched real-UNISIM engine cases. Edit the VIV path for your installation; the script checks at least 2 GiB free RAM. Leave QUICK/TRACE unset for the full run. Results: `results/exact_tile_checks.json`. Static packing is checked only with valid bounded inputs. Each driver supplies identical vectors when its core is ready.
3. `vivado -mode batch -source synth_exact.tcl -log results/exact_synth.log -journal results/exact_synth.jou -tclargs top_exact_checkpoint top_exact_promote top_exact_native top_exact_static top_exact_lut`
4. `vivado -mode batch -source route_probe.tcl -log results/exact_route.log -journal results/exact_route.jou -tclargs top_exact_checkpoint top_exact_promote top_exact_native top_exact_static top_exact_lut`

The RTL files are packed_exact_acc.sv, old_acc_engines.sv, exact_checkpoint.sv, exact_promote.sv, exact_tile.sv, and tb_exact_tile.sv. The portable functional boundary is `exact_tile`; top_exact_* are timing-only shells, not elastic host interfaces. See the report for numerical bounds, handshake, memory/power and paper-comparison limits. Synthesized DCPs and simulator databases are excluded; reproduce them with the above commands.

Model provenance/training and the older scheduling estimates are in probe.py, base.py, final_selected.py and final_selected.json. That JSON's scheduling model is not the new RTL's measured latency. build_exact.py regenerates two derived modules from the included earlier guard_acc.sv/shared_neuron_pipe.sv; regeneration is optional.

SHA256SUMS.txt covers all packaged files except itself. Reports and the consolidated exact_snn_results.json are at the archive root. This package does not claim a full network implementation, a FireFly reproduction, measured board throughput, host performance or measured power.
'''
(here/'README_EXACT.md').write_text(readme)
sources=['README_EXACT.md','exact_report_body.md','package_exact.py','build_exact.py','packed_exact_acc.sv',
 'old_acc_engines.sv','exact_checkpoint.sv','exact_promote.sv','exact_tile.sv','tb_exact_tile.sv',
 'check_exact_tiles.py','exact_inference.py','synth_exact.tcl','route_probe.tcl','probe.py','base.py',
 'final_selected.py','guard_acc.sv','shared_neuron_pipe.sv','digits.csv.gz']
files={s:here/s for s in sources}
for s in ['exact_tile_checks.json','exact_inference.json','final_selected.json','model_seed0.npz','model_seed1.npz','model_seed2.npz']:
    files['results/'+s]=here/'results'/s
for top in tops:
    for stage in ['synth','route']:
        for s in ['util.rpt','timing.rpt']+(['slack.txt'] if stage=='route' else []):
            rel=f'results/{top}_{stage}/{s}';files[rel]=here/rel
for folder in sorted((here/'results').glob('exact_tile_sh*')):
    for p in sorted(folder.glob('*.txt')):
        if folder.name.endswith('_b0') and p.name in ('out3.txt','cycles3.txt'):continue
        if p.name.startswith(('stim','out','cycles')):files[p.relative_to(here).as_posix()]=p
for s in ['exact_snn_implementation_and_baselines.md','exact_snn_results.json']:files[s]=out/s
data={rel:p.read_bytes() for rel,p in sorted(files.items())}
manifest=''.join(hashlib.sha256(blob).hexdigest()+'  '+rel+'\n' for rel,blob in data.items())
archive=out/'exact_snn_implementation.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for rel,blob in data.items():z.writestr(rel,blob)
    z.writestr('SHA256SUMS.txt',manifest)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for line in z.read('SHA256SUMS.txt').decode().splitlines():
        sha,rel=line.split('  ',1);assert hashlib.sha256(z.read(rel)).hexdigest()==sha,rel
print(json.dumps(metrics,indent=2))
print('Verified',len(files),'files;',archive.stat().st_size,'bytes')
