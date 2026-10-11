"""Generate a new port-matched replay and physical-power auditor; predecessors read-only."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;OLD=P.parent/'natural_energy_trial'
def put(name,value):
    p=P/name;assert not p.exists();p.write_text(value,encoding='utf-8',newline='\n')
tb=(OLD/'tb_replay.sv').read_text()
tb=tb.replace('tb_natural_energy_replay','tb_sequential_energy_replay')
tb=tb.replace('reg[87:0]u=0,i=0;reg[3:0]av=0;','reg[23:0]u=0;reg[17:0]beta=0;reg[1:0]av=0;')
tb=tb.replace('wire[3:0]take,nout;wire[95:0]data;','wire[1:0]take,nout;wire[23:0]data;')
tb=tb.replace('.i_in(i)','.beta_in(beta)')
tb=tb.replace('reg[87:0]u0,i0;reg[95:0]data0;','reg[23:0]u0;reg[17:0]beta0;reg[23:0]data0;')
tb=tb.replace('[106:0]','[30:0]')
a=tb.index('   if(got[106:101]');b=tb.index('   checked=checked+1;',a)
tb=tb[:a]+'''   if(got!==expected[slot])
    $fatal(1,"REPLAY mismatch E%0d row%0d got%h expected%h",`ENGINE_ID,indices[slot],got,expected[slot]);
'''+tb[b:]
tb=tb.replace('expected[slot][101]','expected[slot][27]')
a=tb.index('    status=$fscanf');b=tb.index('   end else begin',a)
tb=tb[:a]+'''    status=$fscanf(fd,"%d %d %d %d %d %h %h %d %d %d %d %h %d %d %d\\n",
     idx,rst0,iv0,orr0,av0,u0,beta0,ir0,take0,ov0,nout0,data0,mode0,corr0,busy0);
    if(status!=15||idx!=n||$isunknown(data0))$fatal(1,"Bad native row%0d fields%0d",n,status);
    rst=rst0;iv=iv0;orr=orr0;av=av0;u=u0;beta=beta0;
    expected[n%4]={1'(ir0),2'(take0),1'(ov0),2'(nout0),data0,1'(mode0)};
    known[n%4][0]=1;indices[n%4]=n;
'''+tb[b:]
tb=tb.replace('u=0;i=0;','u=0;beta=0;')
assert 'i_in'not in tb and '106:'not in tb
put('tb_energy.sv',tb)
put('export.tcl',(OLD/'export.tcl').read_text())
put('power.tcl',(OLD/'power.tcl').read_text().replace('$engine > 4','$engine > 5').replace('0..4','0..5').replace('tb_natural_energy_replay','tb_sequential_energy_replay'))
audit=(OLD/'audit_power_v2.py').read_text()
tail=audit[audit.index('def tcl_words('):audit.index('def self_check():')]
tail=tail.replace('engine in range(5)','engine in range(6)').replace('== 290','== 78').replace('== 183','== 47').replace('== 107','== 31')
tail=tail.replace('(1 if engine < 3 else 0)','[1,1,0,2,1,1][engine]').replace('fixture_FF=290','fixture_FF=78').replace('290-FF','78-FF')
put('audit_power.py',(P/'audit_power_prefix.py').read_text()+'\n'+tail)
paths=[P/n for n in ('prepare_stage4_energy.py','audit_power_prefix.py','audit_power.py','tb_energy.sv','export.tcl','power.tcl')]+[OLD/'tb_replay.sv',OLD/'audit_power_v2.py',OLD/'export.tcl',OLD/'power.tcl']
value=dict(status='prepared',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths})
put('stage4_energy_preparation.json',json.dumps(value,indent=2)+'\n')
