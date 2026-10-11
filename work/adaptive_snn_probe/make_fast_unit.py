"""Generate a separate implementation; do not mutate a running build's source.
Move range check before leak by inverting monotone integer leak exactly.
Also strengthen LUT reference with a five-bit pair pre-adder.
"""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
s=(P/'persistent_unit.sv').read_text()
s=s.replace('persistent_unit','persistent_unit_fast').replace('top_persist','top_fast')
old='  assign fits[i]=(leaked[i]>=(-128-LOW))&&(leaked[i]<=(127-HIGH));'
assert old in s
s=s.replace(old,'  assign fits[i]=(u[i]>=MON_LOW)&&(u[i]<=MON_HIGH);')
marker=' localparam WL=48/WIDE_BITS,REST=6-WL;'
assert marker in s
s=s.replace(marker,''' // Constant divisions below are elaboration-time arithmetic, not hardware dividers.
 function integer floor_div(input integer a,b);
  begin floor_div=(a<0)?-((-a+b-1)/b):a/b;end
 endfunction
 localparam MON_LOW=LEAK?floor_div((-129-LOW)*(1<<SH),(1<<SH)-1)+1:(-128-LOW);
 localparam MON_HIGH=LEAK?floor_div((127-HIGH)*(1<<SH),(1<<SH)-1):(127-HIGH);
'''+marker)
old='   wire signed[3:0]da=wa[i*4+:4],db=wb[i*4+:4];'
assert old in s
s=s.replace(old,old+'\n   wire signed[4:0]pair={da[3],da}+{db[3],db};')
old="mem[i]<=mem[i]+{{12{da[3]}},da}+{{12{db[3]}},db};"
assert old in s
s=s.replace(old,'mem[i]<=mem[i]+{{(STATE_BITS-5){pair[4]}},pair};')
(P/'persistent_unit_fast.sv').write_text(s)
(P/'tb_persistent_unit_fast.sv').write_text((P/'tb_persistent_unit.sv').read_text().replace('persistent_unit #','persistent_unit_fast #'))
check=(P/'check_persistent_unit.py').read_text().replace('persistent_unit.sv','persistent_unit_fast.sv').replace('tb_persistent_unit.sv','tb_persistent_unit_fast.sv').replace('persist_unit_','fast_unit_').replace('persistent_unit_checks.json','fast_unit_checks.json')
(P/'check_fast_unit.py').write_text(check)
check=(P/'check_persistent_model_trace.py').read_text().replace('persistent_unit.sv','persistent_unit_fast.sv').replace('tb_persistent_unit.sv','tb_persistent_unit_fast.sv').replace("'persistent_model_trace'","'fast_model_trace'").replace('persistent_model_trace.json','fast_model_trace.json')
(P/'check_fast_model_trace.py').write_text(check)
(P/'route_fast_unit.tcl').write_text((P/'route_persistent_unit.tcl').read_text().replace('persistent_unit.sv','persistent_unit_fast.sv'))
(P/'run_fast_route.py').write_text((P/'run_persistent_route.py').read_text().replace('persistent_unit.sv','persistent_unit_fast.sv').replace('persistent_unit_hardware.json','fast_unit_hardware.json').replace('route_persistent_unit.tcl','route_fast_unit.tcl'))
checks=0
for sh in [1,3]:
 for low,high in [(-64,56),(-32,43),(-128,127),(-3,9)]:
  a=-128-low;b=127-high;scale=1<<sh
  lower=((a-1)*scale)//(scale-1)+1;upper=(b*scale)//(scale-1)
  for u in range(-32768,32768):
   leaked=u-(u>>sh)
   assert (a<=leaked<=b)==(lower<=u<=upper),(sh,low,high,u)
   checks+=1
(P/'results'/'preleak_bound_audit.json').write_text(json.dumps(dict(cases=checks,failures=0,default_shift3_preleak_bounds=[-74,81]),indent=2))
print('PRELEAK RANGE EQUIVALENCE PASS',checks,flush=True)
