"""Isolated exact optimized LUT control E7; retain E2 and all prior diagnostics."""
from pathlib import Path
import hashlib,json,time
import numpy as np
P=Path(__file__).resolve().parent
ALT=P/'lutceil_e7';ALT.mkdir(parents=True,exist_ok=True)
assert not(ALT/'plan.json').exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[Path(__file__),P/'leak_core16.sv',P/'timing16.sv',P/'route16.tcl',P/'tb_native16.sv',P/'run_native16.py',P/'domain_acceptance.json',P/'preparation_v2.json']
plan=dict(status='declared_before_variant_tests',engine=7,operation='ceil(beta*U/256)',
          U_domain=[-32768,32767],beta_domain=[0,256],implementation='floor(signed low8 coefficient product /256) + indicator(nonzero product residue), beta256 identity branch',
          reason='Remove addition255 across full25bit product; use exact16bit quotient increment. This is a strengthened LUT baseline, not a claimed timing-model repair.',
          E2_unchanged=True,software_exhaustive_cases=65536*257,fixture_FF=94,
          source_sha256={str(p):sha(p)for p in inputs})
(ALT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
start=time.monotonic();u=np.arange(-32768,32768,dtype=np.int64)
for b in range(257):
    product=u*(b&255)
    optimized=u if b==256 else (product>>8)+((product&255)!=0)
    reference=-np.floor_divide(-(u*b),256)
    assert np.array_equal(optimized,reference)
    assert np.all((-32768<=optimized)&(optimized<=32767))
original=(P/'leak_core16.sv').read_text()
core=original.replace('module sequential_leak16 #','module sequential_leak16_lutceil #')
marker=' end else begin:two_scalar';assert core.count(marker)==1
branch=''' end else if(E==7)begin:lut_quotient_ceil
  // Exact general beta0..256 control, signed16 U. Original E2 retained above.
  for(genvar l=0;l<2;l=l+1)begin:lane
   wire signed[B-1:0]u=u_q[l*B+:B];wire[8:0]b=l==0?b0_q:b1_q;
   (* use_dsp="no" *)wire signed[B+8:0]product=u*$signed({1'b0,b[7:0]});
   wire[B-1:0]floor_bits=product[B+7:8];
   (* use_dsp="no" *)wire[B-1:0]ceil_bits=floor_bits+{{(B-1){1'b0}},(|product[7:0])};
   reg[B-1:0]r=0;
   always @(posedge clk)if(rst)r<=0;else if(issue)r<=count1>l?(b[8]?u:ceil_bits):{B{1'b0}};
   assign answer[l*B+:B]=r;
  end
 end else begin:two_scalar'''
core=core.replace(marker,branch)
old=original[original.index(' end else if(E==2)begin:lut'):original.index(' end else if(E==6)begin:shift128')]
new=core[core.index(' end else if(E==2)begin:lut'):core.index(' end else if(E==6)begin:shift128')]
assert old==new
(ALT/'leak_core16_lutceil.sv').write_text(core,encoding='utf-8')
(ALT/'leak_dsp.sv').write_bytes((P/'leak_dsp.sv').read_bytes())
timing=(P/'timing16.sv').read_text().replace('sequential_leak16','sequential_leak16_lutceil')
timing=timing.replace('`undef GUARD_ADD_FRONTIER_TOP','`GUARD_ADD_FRONTIER_TOP(top_sequential_leak16_lutceil_e7,7)\n`undef GUARD_ADD_FRONTIER_TOP')
(ALT/'timing16_lutceil.sv').write_text(timing,encoding='utf-8')
route=(P/'route16.tcl').read_text().replace('top_sequential_leak16_e[0-6]','top_sequential_leak16_lutceil_e[0-7]')
route=route.replace('$here/leak_core16.sv','$here/leak_core16_lutceil.sv').replace('$here/timing16.sv','$here/timing16_lutceil.sv')
(ALT/'route16_lutceil.tcl').write_text(route,encoding='utf-8')
tb=(P/'tb_native16.sv').read_text().replace('tb_sequential_leak16','tb_sequential_leak16_lutceil')
tb=tb.replace('localparam integer ENGINES=`SHIFT_COHORT?7:6;','localparam integer ENGINES=7;')
tb=tb.replace('sequential_leak16 #(.E(g),.B(16))','sequential_leak16_lutceil #(.E(g==6?7:g),.B(16))')
# The seventh native index is E7, not E6 shift; all coefficients remain legal.
tb=tb.replace('   if(`SHIFT_COHORT&&coefs[i]!=128)$fatal(1,"Shift cohort requires beta128 at row%0d",i);','')
(ALT/'tb_native16_lutceil.sv').write_text(tb,encoding='utf-8')
runner=(P/'run_native16.py').read_text()
runner=runner.replace('P=Path(__file__).resolve().parent;ROOT=P.parent.parent','P=Path(__file__).resolve().parent;ROOT=P.parent.parent.parent')
runner=runner.replace("P/'preparation_v2.json'","P/'preparation.json'").replace("P/'domain_acceptance.json'","P.parent/'domain_acceptance.json'")
runner=runner.replace("P/'leak_core16.sv'","P/'leak_core16_lutceil.sv'").replace("P/'tb_native16.sv'","P/'tb_native16_lutceil.sv'")
runner=runner.replace("'tb_sequential_leak16'","'tb_sequential_leak16_lutceil'")
runner=runner.replace("shift=0 if args.cohort=='general' else 1","shift=0")
runner=runner.replace("co=domain['cohorts'][args.cohort];verify(co['artifact_sha256'])","co=domain['cohorts'][args.cohort].copy();verify(co['artifact_sha256']);co['expected_requests_by_engine']=co['expected_requests_by_engine'][:6]+[co['expected_requests_by_engine'][2]]")
runner=runner.replace('rows.append(dict(engine=e,requests=req','rows.append(dict(engine=(7 if e==6 else e),native_index=e,requests=req')
(ALT/'run_native16_lutceil.py').write_text(runner,encoding='utf-8')
outputs=[ALT/n for n in('leak_core16_lutceil.sv','leak_dsp.sv','timing16_lutceil.sv','route16_lutceil.tcl','tb_native16_lutceil.sv','run_native16_lutceil.py')]
answer=dict(status='software_exhaustive_pass_prepared_uncompiled_unrouted',arithmetic_cases=65536*257,mismatches=0,
    E2_arithmetic_byte_identical=True,B=16,fixture_FF=94,launch_FF=55,capture_FF=39,engine=7,expected_DSP=0,
    native_engine_indices=[0,1,2,3,4,5,7],source_sha256=plan['source_sha256']|{str(ALT/'plan.json'):sha(ALT/'plan.json')},
    artifact_sha256={str(p):sha(p)for p in outputs},elapsed_seconds=time.monotonic()-start,
    compile_options=dict(native='run_native16_lutceil.py --cohort general|shift128|actual128 --stall0|1 --capture0|1 --attempt NAME',
         route='vivado -source route16_lutceil.tcl -tclargs top_sequential_leak16_lutceil_e7 6.0|9.0|12.0 HASH fresh ATTEMPT_DIR'),
    timing_discrepancy_relation='Quotient rounding changes final carry topology and may avoid the suspect25bit rounder; must still pass the same strict SDF audit. No timing model root cause inferred from a future E7 pass.',
    exclusions='No native, routed, timing orpower success yet. Optimized LUT is a required stronger control if it passes.')
(ALT/'preparation.json').write_text(json.dumps(answer,indent=2)+'\n')
print(json.dumps({k:answer[k]for k in('status','arithmetic_cases','mismatches','E2_arithmetic_byte_identical','engine','elapsed_seconds')},indent=2),flush=True)
