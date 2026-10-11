"""Replay model/stress leakage in RTL, then reconstruct sampled integer SNN outputs."""
from pathlib import Path
import os,subprocess,numpy as np,json,re,hashlib,ctypes,sys
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
kind=sys.argv[1];assert kind in ['model','stress'];wd=R/f'adaptive_delta_compact_{kind}_25_1'
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));print('Free GiB',m.free/2**30,flush=True);assert m.free>1.0*2**30
source_hashes={n:hashlib.sha256((P/n).read_bytes()).hexdigest()for n in ['adaptive_delta_compact.sv','tb_adaptive_delta_compact.sv']}
temp=wd/'tmp';temp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(temp);env['TMP']=str(temp)
cmds=[f'"{V}/bin/xvlog.bat" -sv -d "DC=25" -d "MP=1" "{P}/adaptive_delta_compact.sv" "{P}/tb_adaptive_delta_compact.sv"',
 f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',f'"{V}/bin/xelab.bat" -mt off -L unisims_ver tb_adaptive_delta_compact glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
for i,c in enumerate(cmds):
 z=subprocess.run(c,shell=True,cwd=wd,env=env,capture_output=True,text=True);(wd/f'tool_{i}.log').write_text(z.stdout+z.stderr)
 assert z.returncode==0,z.stdout[-3000:]+z.stderr[-1000:]
assert 'ADAPTIVE DELTA PASS'in z.stdout,z.stdout[-3000:]
groups=np.load(wd/'expected.npz')['groups'].astype(np.int64);reference=groups-(25*groups//256);rows=[]
for e in [0,1,2,3,5]:
 text=(wd/f'out{e}.txt').read_text().splitlines();assert len(text)==len(groups)
 parsed=[s.split()for s in text];got=np.empty(groups.shape,dtype=np.int64)
 for i,s in enumerate(parsed):
  x=int(s[0],16)
  for j in range(6):
   v=(x>>(11*j))&2047;got[i,j]=v-2048 if v>=1024 else v
 assert np.array_equal(got,reference),(kind,e,'leak mismatch')
 match=re.search(rf'DELTA E {e} CYCLES (\d+) ACCEPTED (\d+) OUTPUTS (\d+) ISSUES (\d+) NARROW (\d+) BYPASS (\d+)',z.stdout);assert match
 row=dict(engine=e,groups=len(groups),neuron_operations=6*len(groups),mismatches=0,cycles=int(match[1]),issue_slots=int(match[4]),narrow_groups=int(match[5]),bypass_groups=int(match[6]))
 if kind=='model':
  info=json.loads((R/'adaptive_delta_model_input.json').read_text());counts={m['seed']:np.zeros((48,10),np.int64)for m in info['metadata']};states_bad=spikes_bad=0
  for item in info['ledger']:
   leaked=got[item['start']:item['start']+item['blocks']].reshape(-1)[:item['neurons']]
   nxt=leaked+np.array(item['current']);fire=nxt>=item['threshold'];state=nxt-fire*item['threshold']
   states_bad+=int(np.count_nonzero(state!=item['expected_state']));spikes_bad+=int(np.count_nonzero(fire!=item['expected_spikes']))
   if item['layer']==1:counts[item['seed']][item['image']]+=fire
  assert states_bad==spikes_bad==0
  model_rows=[]
  for meta in info['metadata']:
   count=counts[meta['seed']];assert np.array_equal(count,meta['expected_counts']);labels=np.array(meta['labels'])
   start=meta['start'];end=start+meta['groups'];starts=[int(s[1])for s in parsed[start:end]];ends=[int(s[2])for s in parsed[start:end]]
   model_rows.append(dict(seed=meta['seed'],images=48,accuracy=float(np.mean(count.argmax(1)==labels)),
    exact_spike_counts=True,trace_group_cycles=ends[-1]-starts[0]+1))
  row.update(model_rows=model_rows,state_mismatches=states_bad,spike_mismatches=spikes_bad)
 else:
  row['stress_rows']=[]
  for meta in json.loads((R/'adaptive_delta_stress_input.json').read_text()):
   start=meta['start'];end=start+meta['groups'];cyc=int(parsed[end-1][2])-int(parsed[start][1])+1
   expected=meta['adaptive_group_cycles']if e==0 else (4*(320-meta['zero_groups'])+meta['zero_groups']if e==3 else meta['fixed_group_cycles'])
   assert cyc==expected
   row['stress_rows'].append(dict(hard_reset=meta['hard_reset'],cycles=cyc,common_add_cycles=meta['common_add_cycles'],common_finish_cycles=meta['common_finish_cycles']))
 rows.append(row);print(row,flush=True)
(R/f'adaptive_delta_compact_{kind}_checks.json').write_text(json.dumps(dict(source_hashes=source_hashes,rows=rows),indent=2))
