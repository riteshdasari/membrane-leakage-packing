"""New matched implementation of the common proven U interval, not full U11."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;ROOT=P.parent;OLD=ROOT/'natural_u11_trial'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(t,a,b):
    assert t.count(a)==1,(a,t.count(a));return t.replace(a,b)
assert not(P/'source_preparation.json').exists()
cert=ROOT/'sum_width_trial/certificates.json';d=json.loads(cert.read_text())
rows=[r for r in d['rows']if r['unchanged_original_control']]
lo=min(r['certified_U_range'][0]for r in rows);hi=max(r['certified_U_range'][1]for r in rows)
assert (lo,hi)==(-686,245)
assert all(r['contracts']['uniform_U_any_I8']['sum_bits']==11 and r['contracts']['uniform_U_any_I8']['high_base_bits']==6 for r in rows)
core=(OLD/'core.sv').read_text().replace('natural_u11','certified_u11')
core=core.replace('// Exact signed11 U + signed8 I -> signed12. One advancing edge.',
    '// Exact certified U in [-686,245] + signed8 I. Internal sum11, signextended output12.')
core=once(core,'wire signed[6:0]hu={u_in[11*l+10],u_in[11*l+5+:6]};','wire signed[5:0]hu=u_in[11*l+5+:6];')
core=once(core,'wire signed[6:0]hi={{4{i_in[11*l+7]}},i_in[11*l+5+:3]};','wire signed[5:0]hi={{3{i_in[11*l+7]}},i_in[11*l+5+:3]};')
core=once(core,'wire signed[6:0]base=hu+hi;','wire signed[5:0]base=hu+hi;')
core=once(core,'reg[6:0]base_reg=0;','reg[5:0]base_reg=0;')
core=once(core,"wire[6:0]high=base_reg+{6'd0,p[6*l+5]};","wire[5:0]high=base_reg+{5'd0,p[6*l+5]};")
core=once(core,'assign answer[12*l+:12]={high,p[6*l+:5]};','assign answer[12*l+:12]={high[5],high,p[6*l+:5]};')
# Apply the same valid interval sum-width reduction to every fabric full lane.
assert core.count('reg[11:0]sum_reg=0;')==2
core=core.replace('reg[11:0]sum_reg=0;','reg[10:0]sum_reg=0;')
core=core.replace("sum_reg<=take>l?sum:12'd0;","sum_reg<=take>l?sum[10:0]:11'd0;")
core=core.replace('assign answer[12*l+:12]=sum_reg;','assign answer[12*l+:12]={sum_reg[10],sum_reg};')
(P/'core.sv').write_text(core)
for name in('timing.sv','route.tcl'):(P/name).write_text((OLD/name).read_text().replace('natural_u11','certified_u11'))
tb=(OLD/'tb_native.sv').read_text().replace('natural_u11','certified_u11').replace('NATURAL_U11','CERTIFIED_U11')
tb=tb.replace("raw_u={8{11'd1023}}","raw_u={8{11'd245}}")
tb=once(tb,'if(status!=2||mem_i[k][10:8]!={3{mem_i[k][7]}})',
    'if(status!=2||$signed(mem_u[k]) < -686||$signed(mem_u[k]) > 245||mem_i[k][10:8]!={3{mem_i[k][7]}})')
(P/'tb_native.sv').write_text(tb)
verify=(OLD/'verify_native.py').read_text().replace('NATURAL_U11','CERTIFIED_U11')
verify=verify.replace('524288','238592').replace('groups[:2048]','groups[:932]').replace('offset-1024','offset-686')
verify=verify.replace('signed11 U, sign-extended signed8 I; exact signed12 U+I','Certified U [-686,245], signed8 I; exact signextended sum11')
(P/'verify_native.py').write_text(verify)
run=(OLD/'run_trial.py').read_text().replace('natural_u11','certified_u11').replace('NATURAL U11','CERTIFIED U11').replace('524288','238592')
run=once(run,"retried=True;command[-2]='resume';log=job(command,wd,'route_resume',stamps,2.3)",
    "retried=True;command[-2]='resume';command[command.index('-log')+1]='vivado_resume.log';command[command.index('-journal')+1]='vivado_resume.jou';log=job(command,wd,'route_resume',stamps,2.3)")
run=run.replace('same U11 operation','same certified-interval operation')
(P/'run_trial.py').write_text(run)
algebra=(OLD/'check_algebra.py').read_text().replace('range(-1024,1024)','range(-686,246)').replace('rng.randrange(-1024,1024)','rng.randrange(-686,246)')
algebra=algebra.replace('(-1024,-129,-128,-33,-32,-1,0,31,32,127,128,1023)','(-686,-129,-128,-33,-32,-1,0,31,32,127,128,245)')
algebra=algebra.replace('-64<=base<=high<=63','-32<=base<=high<=31').replace('high&127','high&63').replace('signed(bits,12)','signed(bits,11)').replace('),12)==u+i','),11)==u+i')
(P/'check_algebra.py').write_text(algebra)
(P/'CONTRACT.md').write_text('''# Certified-interval control trial

All five implementations accept postleak U in [-686,245] and any signed8 I.
This is a uniform safe superset of all three original shift3 LIF certificates.
Full-word U11 inputs outside that interval are not accepted by this contract.
S is in [-814,372], so full fabric sum registers use11 bits, signextended to
the original12-bit output interface. Precomputed full high bases fit signed6.
The same reductions apply to adaptive DSP, fixed8 DSP, hybrid, full LUT and
same-policy adaptive LUT. Native FOUR12 DSP still supports four full lanes.
Admission policy, one-edge protocol, original weights/thresholds/equations,
device,6ns clock and290-FF measurement fixture remain the same.
No new energy or full neuron-update claim is authorized by route/STA alone.
''')
sources=[Path(__file__),cert,ROOT/'sum_width_trial/check_certificates.py',*(OLD/n for n in('core.sv','timing.sv','route.tcl','tb_native.sv','verify_native.py','run_trial.py','check_algebra.py'))]
generated=[P/n for n in('core.sv','timing.sv','route.tcl','tb_native.sv','verify_native.py','run_trial.py','check_algebra.py','CONTRACT.md')]
(P/'source_preparation.json').write_text(json.dumps(dict(status='prepared',source_sha256={str(p):sha(p)for p in sources},generated_sha256={str(p):sha(p)for p in generated},certified_U_range=[lo,hi],scope='Fair static-bound specialization only; all fixed controls retained'),indent=2)+'\n')
print('CERTIFIED-INTERVAL SOURCES PREPARED')
