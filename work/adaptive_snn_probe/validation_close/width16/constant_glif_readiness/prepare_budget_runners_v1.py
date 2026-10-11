"""Add operationally calibrated runners without changing accepted evidence."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent; W=P.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hist=W/'historical_stage_memory_audit_a0.json'
history=json.loads(hist.read_text())
route=W/'hardware/route12_e5_a0/route.job.json'
jobs=[route]
for stage in ('export','power_annotation'):
    jobs.append(Path(history['summary'][stage]['largest_sampled_peak_job']['job_file']))
for p in jobs:assert p.exists()
receipt=P/'operational_budget_v1.json'
assert not receipt.exists()
receipt.write_text(json.dumps(dict(status='operational_only',source_sha256={str(p):sha(p) for p in [hist,*jobs,P/'run_route_glif_mcm.py',P/'run_energy_glif_mcm.py',Path(__file__)]},
    route=dict(wait_GiB=2.15,start_gate_GiB=2.1,historical_sampled_tree_RSS_GiB=json.loads(route.read_text())['sampled_peak_tool_tree_RSS_sum_GiB']),
    export_annotation=dict(wait_GiB=1.75,start_gate_GiB=1.6),wait_timeout_seconds=600,
    unchanged='Datapath, constraints, exactness, stalls, SDF settings, complete trace and physical annotation acceptance gates',
    limitation='Historical one-second descendant RSS sums are sampled and may double count shared pages; they do not guarantee the new peak. New telemetry is retained.'),indent=2))
budget_sha=sha(receipt)
insert=f'''\ndef wait_memory(threshold):
 budget_file=P/'operational_budget_v1.json'
 assert b.sha(budget_file)=={budget_sha!r}
 b.verify(b.read(budget_file)['source_sha256'])
 deadline=time.monotonic()+600
 while b.free()<=threshold:
  assert time.monotonic()<deadline,('Bounded memory wait expired',threshold,b.free())
  print('MEMORY WAIT free GiB',round(b.free(),3),'required',threshold,flush=True)
  time.sleep(5)
\n'''
for kind in ('route','energy'):
    src=P/f'run_{kind}_glif_mcm.py'; dst=P/f'run_{kind}_glif_mcm_budget_v1.py'
    assert not dst.exists(); txt=src.read_text()
    if kind=='route':
        old='while b.free()<=2.45:time.sleep(5)'; assert txt.count(old)==1
        txt=txt.replace(old,'wait_memory(2.15)')
        old="wd,'route',sources,2.3)"; assert txt.count(old)==1
        txt=txt.replace(old,"wd,'route',sources,2.1)")
        target='def main():'
    else:
        old='while b.free()<=gate+.15:time.sleep(5)'; assert txt.count(old)==1
        txt=txt.replace(old,'wait_memory(gate+.15)')
        for label in ('export','annotation'):
            old=f"wd,'{label}',stamps,2.3)"; assert txt.count(old)==1
            txt=txt.replace(old,f"wd,'{label}',stamps,1.6)")
        target='def tool('
    assert txt.count(target)==1; txt=txt.replace(target,insert+target)
    dst.write_text(txt)
print('Operational budget derivatives saved; no vendor launched')
