"""One native source-cap2 experiment; no route or power tools.

Preserves frozen cores and test sources. Trial-local test changes are limited
to workload delivery capacity, adding the same-policy LUT shadow as engine6,
and additional checks over settled idle/prelude/work controls.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
BASE = P.parent
N = BASE/'natural_frontier_trial'
A = BASE/'adaptive_natural_lut_trial'
W = BASE/'residue_frontier_u13_trial'
sys.path.insert(0,str(W))
import run_u13_physical as run


def prepare_tb(target):
    original = N/'tb_native.sv'
    text = original.read_text()
    old = 'av=(length-index>=8)?8:(length-index);'
    assert text.count(old)==1
    text = text.replace(old,'av=(length-index>=2)?2:(length-index);')
    old = ''' frontier_natural #(.E(E))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
  .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));'''
    assert text.count(old)==1
    text = text.replace(old,''' generate if(E==6)begin:adaptive_lut
  adaptive_natural_lut dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end else begin:frontier
  frontier_natural #(.E(E))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end endgenerate''')
    # Only E6 writes the complete common source/pin trace. Every engine still
    # maintains its trace row counters, protocol oracle, and retired stream.
    text = text.replace('if(`CAPTURE_TRACE)', 'if(`CAPTURE_TRACE&&E==6)')
    text = text.replace('if(E==5)begin','if(E==5||E==6)begin')
    text = text.replace('((E==5)&&(expected_take>5))','(((E==5)||(E==6))&&(expected_take>5))')
    text = text.replace('wire[5:0]done;', 'wire[6:0]done;')
    text = text.replace('e<6;', 'e<7;')
    text = text.replace('tb_frontier_u13_compare;', 'tb_natural_supply2_compare;')
    text = text.replace('"FRONTIER_U13_COMPARE PASS STALL %0d"','"NATURAL_SUPPLY2_COMPARE PASS STALL %0d"')
    text = text.replace('if(take<1||take>av||tail-head>=30)',
        'if(take<1||take>av||av>2||take>2||tail-head>=30)')
    # This oracle deliberately computes the actual core admission from av and
    # raw_u outside work, where retained reset preludes still offer av=8.
    insertion = '''
 integer settled_pin_samples=0,max_accepted_av=0,probe_take,probe_u;
 always @(negedge clk)begin
  #0.021;
  if(trace_on&&!done)begin
   probe_take=av;
   if(E==0&&av>6)probe_take=6;
   if(E==5||E==6)begin
    probe_take=av<5?av:5;
    probe_u=$signed(raw_u[65+:13]);
    if(av>5&&probe_u>=-128&&probe_u<=127)begin
     probe_take=6;probe_u=$signed(raw_u[78+:13]);
     if(av>6&&probe_u>=-128&&probe_u<=127)begin
      probe_take=7;probe_u=$signed(raw_u[91+:13]);
      if(av>7&&probe_u>=-128&&probe_u<=127)probe_take=8;
     end
    end
   end
   if(take!==4'(probe_take)||mode!==(((E==5)||(E==6))&&(probe_take>5)))
    $fatal(1,"Actual idle/prelude/work take mismatch E%0d",E);
   settled_pin_samples=settled_pin_samples+1;
  end
 end
 always @(posedge clk)if(running&&!done&&iv&&ir&&av!=0)begin
  if(av>2||take>2)$fatal(1,"Supply cap exceeded E%0d",E);
  if(av>max_accepted_av)max_accepted_av=av;
 end
 always @(posedge done)begin
  $display("NATURAL_SUPPLY2 E %0d SETTLED_PIN_SAMPLES %0d MAX_ACCEPTED_AV %0d",E,settled_pin_samples,max_accepted_av);
 end
'''
    marker = '\nendmodule\n\nmodule tb_natural_supply2_compare;'
    assert text.count(marker)==1
    text = text.replace(marker, insertion+marker)
    target.write_text(text,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--attempt',type=int,default=0)
    args=parser.parse_args()
    if not args.run:
        print('No tools launch without --run',flush=True)
        return
    wd=P/f'native_models_0_a{args.attempt}'
    assert not wd.exists(),'Preserve prior attempt'
    wd.mkdir(parents=True)
    for folder in (N,A):
        acceptance=run.read(folder/'native_acceptance.json')
        assert acceptance['status']=='pass' and len(acceptance['cohorts'])==4
        run.verify(acceptance['source_sha256'])
    assert run.sha(N/'tb_native.sv')=='278e125ebb6d69d0bf5f44c85bdb04310e868ea62e2c7a44013ba4b906e48a54'
    prepare_tb(wd/'tb_supply2.sv')
    source=W/'original_if/stream_stim.txt'
    shutil.copyfile(source,wd/'stream_stim.txt')
    assert run.sha(source)==run.sha(wd/'stream_stim.txt')
    paths=[Path(__file__),P/'verify_natural_supply2.py',wd/'tb_supply2.sv',wd/'stream_stim.txt',
        BASE/'frontier_natural.sv',BASE/'adaptive_natural_lut.sv',N/'tb_native.sv',
        N/'native_acceptance.json',A/'native_acceptance.json',W/'prepare_u13_work.py',
        W/'verify_frontier_u13.py',W/'original_if/profile.json',W/'original_if/reference_ledger.json',source,
        W/'run_u13_physical.py',run.ENERGY/'run_selective_energy.py']
    stamps=run.pins(paths)
    stamps|=run.read(N/'native_acceptance.json')['source_sha256']
    stamps|=run.read(A/'native_acceptance.json')['source_sha256']
    profile=run.read(W/'original_if/profile.json');run.verify(profile['source_sha256'])
    stamps|=profile['source_sha256']
    run.write(wd/'provenance.json',stamps)
    commands=[
        [run.base.VIVADO/'bin/xvlog.bat','-sv','-d','STALL=0','-d','CAPTURE_TRACE=1',
         BASE/'frontier_natural.sv',BASE/'adaptive_natural_lut.sv',wd/'tb_supply2.sv'],
        [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
        [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver',
         'tb_natural_supply2_compare','glbl','-s','sim'],
        [run.base.VIVADO/'bin/xsim.bat','sim','-R'],
        [sys.executable,'-B',P/'verify_natural_supply2.py','--directory',wd,
         '--output',wd/'supply2_checks.json']]
    for number,command in enumerate(commands):
        run.tool(command,wd,f'tool_{number}',stamps,1.2)
    checked=run.read(wd/'supply2_checks.json')
    assert checked['status']=='pass' and len(checked['rows'])==7
    run.verify(stamps)
    run.write(P/'acceptance.json',dict(status='pass',checked_file=str(wd/'supply2_checks.json'),
        checked_sha256=run.sha(wd/'supply2_checks.json'),source_sha256=stamps,
        all_seven_exact=True,all_original_IF_states_spikes_counts_classes_match=True,
        accepted_supply_never_exceeded_two=True,requests_per_engine=317952,
        service_clocks_per_engine=327168,
        scope='One unstalled native run, six one-edge DSP/fixed engines plus same-policy adaptiveLUT. Actual ready/valid source cap2; no SRAM, routed timing, power or board claim.'))
    print('NATURAL SUPPLY2 CONTROL PASS',wd,flush=True)


if __name__=='__main__':main()
