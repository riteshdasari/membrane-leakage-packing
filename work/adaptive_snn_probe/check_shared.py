import sys,subprocess,json,random,os
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; VIV=Path('C:/AMDDesignTools/2025.2/Vivado')
results=[]
for native in ((False,) if os.environ.get('TRACE') else (False,True)):
 for shift in ((1,) if os.environ.get('TRACE') else (1,3)):
  pipe=bool(os.environ.get('PIPE'));reuse=bool(os.environ.get('REUSE'));n=4 if native else 6; name=f'sim_shared_{int(native)}_{shift}_pipe{int(pipe)}_reuse{int(reuse)}'; wd=HERE/'results'/name;wd.mkdir(exist_ok=True)
  rng=random.Random(33);S=[0]*n;stim=[];expect=[]
  for t in range(120):
   S=[s-(s>>shift) for s in S];e=rng.randint(10,90);stim.append(str(e))
   for j in range(e):
    W=[7 if t%5==0 else -8 if t%5==1 else rng.randint(-8,7) for _ in range(6)]
    stim.append(' '.join(map(str,W)));S=[s+w for s,w in zip(S,W)]
   spike=[int(s>=35) for s in S];S=[s-35*f for s,f in zip(S,spike)]
   assert max(abs(s) for s in S)<4096
   expect.append(S+spike)
  (wd/'stim.txt').write_text('\n'.join(stim)+'\n')
  defs=f'-d "SHIFT={shift}" '+('-d NATIVE ' if native else '')
  if os.environ.get('TRACE'):defs+='-d TRACE '
  if pipe:defs+='-d PIPE '
  if reuse:defs+='-d REUSE '
  commands=[f'"{VIV}/bin/xvlog.bat" -sv {defs} "{HERE}/guard_acc.sv" "{HERE}/old_acc_engines.sv" "{HERE}/shared_neuron.sv" "{HERE}/shared_neuron_pipe.sv" "{HERE}/reuse_neuron.sv" "{HERE}/tb_shared.sv"',
   f'"{VIV}/bin/xvlog.bat" "{VIV}/data/verilog/src/glbl.v"',
   f'"{VIV}/bin/xelab.bat" -L unisims_ver tb glbl -s sim',f'"{VIV}/bin/xsim.bat" sim -R']
  for cmd in commands:
   r=subprocess.run(cmd,shell=True,cwd=wd,capture_output=True,text=True)
   if os.environ.get('TRACE') and 'xsim.bat' in cmd:(wd/'trace.txt').write_text(r.stdout)
   if r.returncode:print(r.stdout[-2500:],r.stderr[-1000:]);sys.exit(1)
  got=[[int(x) for x in l.split()[1:]] for l in (wd/'out.txt').read_text().splitlines()]
  bad=sum(a!=b for a,b in zip(expect,got))+abs(len(expect)-len(got))
  row=dict(native=native,pipe=pipe,reuse=reuse,shift=shift,timesteps=len(got),mismatches=bad,
           max_abs_state=max(max(abs(v) for v in x[:n]) for x in expect),
           cycles=[int(x) for x in (wd/'cycles.txt').read_text().split()],
           cycle_note='total clocks, accepted events, busy clocks; one event per clock when ready; positive/negative/random stress, not trained-model latency')
  results.append(row); print(row,flush=True)
  (HERE/'results'/('rtl_checks_reuse.json' if reuse else 'rtl_checks_pipe.json' if pipe else 'rtl_checks.json')).write_text(json.dumps(results,indent=2))
  if bad:
   print('first failures',[(i,a,b) for i,(a,b) in enumerate(zip(expect,got)) if a!=b][:3]);sys.exit(1)
