"""Independent constant25 ordered-window and integer oracle checks.

Tool execution requires explicit --run; default only prints planned stimulus
size/source hashes. --small is smoke, --models replays saved raw membranes only.
Full SNN state/spike reconstruction is a separate validation, not implied here.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,random,re,subprocess
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
MODEL_INPUTS=['adaptive_delta_model_25_1/expected.npz','adaptive_delta_model_input.json']
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def model_input_hashes():return {n:sha(R/n)for n in MODEL_INPUTS}
def hashes():return {n:hashlib.sha256((P/n).read_bytes()).hexdigest()for n in ['quad_leak.sv','tb_quad_leak.sv',Path(__file__).name]}
def free():
 class M(ctypes.Structure):
  _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
 m=M();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.free/2**30
def policy(u,e):
 x=u[:4];n=len(x);copy=n==4 and 0<=x[3]<=10
 quad=(e==3 and n>0)or(n==4 and not copy and ((e==0 and all(-32<=v<=31 for v in x))or(e==1 and all(-64<=v<=63 for v in x))))
 take=4 if n==4 and(e==4 or quad or copy)else min(3,n)
 bypass=all(0<=v<=10 for v in x[:take])
 return take,int(quad),bypass
def frames(small=False):
 out=[];rg=random.Random(246813)
 xs=[-1024,-1000,-513,-129,-65,-64,-33,-32,-17,-16,-1,0,1,10,11,15,16,31,32,63,64,127,511,1023]if small else range(-1024,1024)
 for x in xs:
  out.extend([([x,-x-1,0,1],0),([x,x,x,x],0),([0,0,0,x],0)])
 for bits in range(256):
  r=[(bits>>(2*i))&3 for i in range(4)]
  h=[-256,-1,0,255];out.append(([4*h[i]+r[i]for i in range(4)],0))
 if not small:
  for code in range(65536):out.append(([(code>>(4*i)&15)-8 for i in range(4)],0))
 for j in range(100 if small else 1500):
  n=rg.randrange(1,40)
  if j%5==0:u=[rg.randrange(11)for _ in range(n)]
  elif j%7==0:u=[0]*n
  elif j%3==0:u=[rg.randrange(-32,32)for _ in range(n)]
  else:u=[rg.randrange(-1024,1024)for _ in range(n)]
  out.append((u,rg.randrange(3)if j%9==0 else 0))
 return out
def model_frames():
 pin=model_input_hashes()
 import numpy as np
 groups=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups']
 text=(R/'adaptive_delta_model_input.json').read_text()
 pattern=r'"seed":(\d+),"t":\d+,"layer":\d+,"image":\d+,"start":(\d+),"blocks":(\d+),"neurons":(\d+)'
 records=[tuple(map(int,m))for m in re.findall(pattern,text)];assert len(records)==9216;del text
 out=[(groups[start:start+blocks].reshape(-1)[:neurons].tolist(),0)for seed,start,blocks,neurons in records]
 assert model_input_hashes()==pin,'Model input changed while loading'
 return out,pin
def simulate(tag,stimulus,stall,model_pin=None):
 wd=R/tag;wd.mkdir(parents=True,exist_ok=True);pin=hashes()
 if model_pin is not None:assert model_input_hashes()==model_pin,'Model inputs changed before simulation'
 with(wd/'stream_stim.txt').open('w')as f:
  f.write(str(len(stimulus))+'\n')
  for u,gap in stimulus:
   assert 1<=len(u)<=4096 and all(-1024<=v<=1023 for v in u)
   f.write(f'{len(u)} 25 {gap}\n');f.writelines(f'{v&2047:03x}\n'for v in u)
 assert free()>1.2,'Insufficient free RAM for simulation';print(tag,'free GiB',round(free(),2),flush=True)
 temp=wd/'tmp';temp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(temp);env['TMP']=str(temp)
 commands=[f'"{V}/bin/xvlog.bat" -sv -d "STALL={stall}" "{P}/quad_leak.sv" "{P}/tb_quad_leak.sv"',
  f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',
  f'"{V}/bin/xelab.bat" -mt off -L unisims_ver tb_quad_leak glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
 for i,cmd in enumerate(commands):
  z=subprocess.run(cmd,shell=True,cwd=wd,env=env,capture_output=True,text=True);(wd/f'tool_{i}.log').write_text(z.stdout+z.stderr)
  assert z.returncode==0,z.stdout[-4000:]+z.stderr[-1000:]
 assert 'QUAD PASS'in z.stdout,z.stdout[-4000:];assert hashes()==pin,'Source changed during simulation'
 rows=[]
 for e in range(5):
  positions=[0]*len(stimulus);expected_requests=expected_issues=expected_quad=expected_bypass=0
  for u,gap in stimulus:
   pos=0
   while pos<len(u):
    take,quad,bypass=policy(u[pos:],e);expected_requests+=1;expected_issues+=not bypass;expected_quad+=quad;expected_bypass+=bypass;pos+=take
  count=0
  with(wd/f'stream_out{e}.txt').open()as f:
   for line in f:
    fid,pos,n,d,bits,ac,rc,mode=line.split();fid,pos,n,d,ac,rc,mode=map(int,[fid,pos,n,d,ac,rc,mode]);bits=int(bits,16)
    u,gap=stimulus[fid];take,quad,bypass=policy(u[pos:],e)
    assert (n,d,mode,pos)==(take,25,quad,positions[fid]),(e,line)
    got=[(bits>>(11*i))&2047 for i in range(4)]
    want=[(-((-(231*v))//256))&2047 for v in u[pos:pos+n]]+[0]*(4-n)
    assert got==want,(e,line,u[pos:pos+n],got,want)
    positions[fid]+=n;count+=1
    if not stall:assert rc-ac==4
  assert positions==[len(u)for u,gap in stimulus]and count==expected_requests
  match=re.search(rf'STREAM E {e} REQUESTS (\d+) NEURONS (\d+) ISSUES (\d+) NARROW (\d+) BYPASS (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+)',z.stdout);assert match
  req,neurons,issues,quad,by,clocks,ins,outs=map(int,match.groups())
  assert (req,issues,quad,by)==(expected_requests,expected_issues,expected_quad,expected_bypass)
  assert neurons==sum(len(u)for u,gap in stimulus)
  if not stall and not any(g for u,g in stimulus):assert clocks==req+4
  if stall:assert ins>0 and outs>0
  rows.append(dict(engine=e,requests=req,neurons=neurons,arithmetic_issues=issues,quad_requests=quad,bypass_requests=by,clocks=clocks,input_stall_checks=ins,output_stall_checks=outs,latency_checks=req,mismatches=0))
  print(rows[-1],flush=True)
 result=dict(source_hashes=pin,delta=25,backpressure=bool(stall),frames=len(stimulus),rows=rows,
  stimulus_sha256=sha(wd/'stream_stim.txt'),stimulus_file=f'{tag}/stream_stim.txt',expected_engines=list(range(5)),
  validation_kind='saved_model_raw_replay'if model_pin is not None else('smoke'if tag.startswith('quad_smoke')else'full_integer_stress'),
  model_input_sha256=model_pin,
  source_contract='valid and entire raw window held until acceptance; input valid low during reset',
  scope='Raw four-window leakage primitive; no memory source/controller and no SNN state reconstruction',
  acceptance_to_handshake_advances=4,identity_bypass='All CONSUMED values0..10; constant25 only')
 if model_pin is not None:assert model_input_hashes()==model_pin,'Model inputs changed during simulation'
 (R/(tag+'_checks.json')).write_text(json.dumps(result,indent=2));return result
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',action='store_true');ap.add_argument('--small',action='store_true');ap.add_argument('--models',action='store_true');args=ap.parse_args()
 if not args.run:print('No tools run. Use --run [--small|--models] after source review.',hashes());return
 assert not(args.small and args.models),'Choose smoke or model replay'
 if args.models:stimulus,model_pin=model_frames()
 else:stimulus,model_pin=frames(args.small),None
 stem='quad_models'if args.models else('quad_smoke'if args.small else'quad_main')
 for stall in [0,1]:simulate(stem+f'_{stall}',stimulus,stall,model_pin)
if __name__=='__main__':main()
