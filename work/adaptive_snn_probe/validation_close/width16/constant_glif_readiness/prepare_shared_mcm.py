"""Prepare one shared GLIF checkpoint-coefficient LUT control; launch no vendor job.

The comparison domain is deliberately the complete frozen coefficient set, not
one favorable channel. Existing captures, model results and routes are read-only.
"""
from pathlib import Path
import ast, hashlib, json
import numpy as np

P = Path(__file__).resolve().parent
W = P.parent
ROOT = W.parent.parent
A = W.parent / 'activity/random_stratified_v2'
T = ROOT / 'sequential_paper_trial'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def pins(files):
    return {str(p.resolve()): sha(p) for p in files}


def save(name, obj):
    path = P / name
    assert not path.exists(), path
    path.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


def main():
    assert not (P/'preparation.json').exists(), 'Preserve every declared attempt.'
    model = json.loads((T/'stage2_results.json').read_text())
    rows = model['rows']
    assert model['status']=='complete_integer_neuron_public_test' and model['samples']==10000
    coeffs = sorted({b for row in rows.values() for key in ('coefficient0', 'coefficient1') for b in row[key]})
    assert coeffs == list(range(74,89)) + list(range(153,171))
    pairs = sorted({(a,b) for row in rows.values() for a,b in zip(row['coefficient0'], row['coefficient1'])})
    assert len(pairs) == 149
    source_result = json.loads((A/'results.json').read_text())
    assert source_result['status'] == 'pass'
    for group in ('source_sha256', 'artifact_sha256'):
        for path, digest in source_result[group].items():
            assert sha(Path(path)) == digest, path
    data = np.load(A/'activity_operands.npz')
    ref = np.load(W/'actual_glif_expected.npz')
    for key in ('U', 'beta', 'expected_leak'):
        assert np.array_equal(data[key], ref[key]), key

    # Independent channel reconstruction from source frame shape and saved raw
    # indices. This verifies the runtime coefficient includes previous-spike
    # selection; it does not add selection hardware to only one competitor.
    frames = {(r['layer'],r['time_step'],r['batch_start']):r for r in source_result['source_frames']}
    at = 0
    context_counts = {}
    for window in source_result['windows']:
        layer = window['layer']; length = window['length']; stop = at+length
        f = frames[layer,window['time_step'],window['batch_start']]
        k0 = np.asarray(rows[layer]['coefficient0'], dtype=np.int64)
        k1 = np.asarray(rows[layer]['coefficient1'], dtype=np.int64)
        channels = len(k0)
        assert f['raw_operations'] % (4*channels) == 0
        spatial = f['raw_operations']//(4*channels)
        channel = (data['raw_index'][at:stop]//spatial) % channels
        previous = data['previous_spike'][at:stop]
        actual = np.where(previous != 0, k1[channel], k0[channel])
        assert np.array_equal(actual, data['beta'][at:stop]), window['index']
        for c,s,b in zip(channel,previous,actual):
            key = f'{layer}:{int(c)}:{int(s)}:{int(b)}'
            context_counts[key] = context_counts.get(key,0)+1
        at=stop
    assert at == len(data['U']) == 262528
    assert set(map(int,data['beta'])) <= set(coeffs)

    # Exact arithmetic check with mathematical signed-integer operations.
    # Hardware uses a signed5 delta encoded modulo32, avoiding a general
    # multiplier. Floor+nonzero-remainder is independent of the division oracle.
    U = np.arange(-32768,32768,dtype=np.int64)
    exhaustive_mismatches = 0
    for beta in coeffs:
        mode = (beta>>7)&1
        delta_bits = ((beta&31) - (0 if mode else 16)) & 31
        delta = delta_bits - 32 if delta_bits&16 else delta_bits
        assert beta == (160 if mode else 80)+delta and abs(delta)<=10
        odd = {0:np.zeros_like(U),1:U,2:U<<1,3:U+(U<<1),4:U<<2,
               5:U+(U<<2),6:(U+(U<<1))<<1,7:(U<<3)-U,
               8:U<<3,9:U+(U<<3),10:(U+(U<<2))<<1}
        residual = odd[abs(delta)]
        product = ((U+(U<<2)) << (5 if mode else 4)) + (-residual if delta<0 else residual)
        assert np.array_equal(product,U*beta)
        assert product.min()>=-(1<<24) and product.max()<(1<<24)
        quotient = np.floor_divide(product,256)+(np.bitwise_and(product,255)!=0)
        reference = -np.floor_divide(-(U*beta),256)
        exhaustive_mismatches += int(np.count_nonzero(quotient != reference))
    assert exhaustive_mismatches == 0
    direct = -np.floor_divide(-(data['U']*data['beta']),256)
    assert np.array_equal(direct,data['expected_leak'])
    scalar_cases = len(U)*len(coeffs)

    core = r'''`timescale 1ns/1ps
// Shared exact checkpoint-coefficient control. Declared legal beta domain:
// 74..88 and153..170; every frozen GLIF channel/previous-spike value included.
// Full signed16 membrane domain. Two independent lanes, no DSPs.
module glif_mcm_lane(input wire signed[15:0]u,input wire[8:0]b,
 output wire[15:0]answer);
 wire mode=b[7];
 wire[4:0]delta=b[4:0]-(mode?5'd0:5'd16);
 wire[4:0]magnitude=delta[4]?(5'd0-delta):delta;
 wire signed[19:0]u20={{4{u[15]}},u};
 (* use_dsp="no" *)wire signed[19:0]m3=u20+(u20<<<1);
 (* use_dsp="no" *)wire signed[19:0]m5=u20+(u20<<<2);
 (* use_dsp="no" *)wire signed[19:0]m7=(u20<<<3)-u20;
 (* use_dsp="no" *)wire signed[19:0]m9=u20+(u20<<<3);
 reg signed[19:0]residual;
 always @* begin
  case(magnitude)
   0:residual=20'sd0;
   1:residual=u20;
   2:residual=u20<<<1;
   3:residual=m3;
   4:residual=u20<<<2;
   5:residual=m5;
   6:residual=m3<<<1;
   7:residual=m7;
   8:residual=u20<<<3;
   9:residual=m9;
   10:residual=m5<<<1;
   default:residual=20'sd0; // Caller declares the complete legal beta set.
  endcase
 end
 wire signed[24:0]m5wide={{5{m5[19]}},m5};
 wire signed[24:0]base=mode?(m5wide<<<5):(m5wide<<<4);
 wire signed[24:0]reswide={{5{residual[19]}},residual};
 (* use_dsp="no" *)wire signed[24:0]product=delta[4]?base-reswide:base+reswide;
 wire[15:0]floor_bits=product[23:8];
 (* use_dsp="no" *)assign answer=floor_bits+{15'd0,(|product[7:0])};
endmodule

module sequential_leak16_glif_mcm(
 input wire clk,rst,in_valid,out_ready,input wire[31:0]u_in,
 input wire[17:0]beta_in,input wire[1:0]available,
 output wire in_ready,out_valid,output wire[1:0]take,out_count,
 output wire[31:0]out_data,output wire narrow_mode);
 assign take=available;
 reg v1=0,v2=0;reg[1:0]count1=0,count2=0;
 reg[31:0]u_q=0;reg[17:0]b_q=0;
 wire advance2=!v2||out_ready;
 assign in_ready=!rst&&(!v1||advance2);
 wire accept=in_valid&&in_ready&&(available!=0);
 wire issue=v1&&advance2&&!rst;
 always @(posedge clk)begin
  if(rst)begin v1<=0;v2<=0;count1<=0;count2<=0;u_q<=0;b_q<=0;end
  else begin
   if(advance2)begin v2<=v1;if(v1)count2<=count1;end
   if(in_ready)begin
    v1<=accept;
    if(accept)begin
     count1<=take;
     u_q<={take==2?u_in[31:16]:16'd0,u_in[15:0]};
     b_q<={take==2?beta_in[17:9]:9'd80,beta_in[8:0]};
    end
   end
  end
 end
 assign out_valid=v2;assign out_count=count2;assign narrow_mode=1'b0;
 wire[31:0]answer;
 for(genvar l=0;l<2;l=l+1)begin:lane
  wire[15:0]arithmetic;
  glif_mcm_lane mcm($signed(u_q[l*16+:16]),b_q[l*9+:9],arithmetic);
  reg[15:0]r=0;
  always @(posedge clk)if(rst)r<=0;else if(issue)r<=count1>l?arithmetic:16'd0;
  assign answer[l*16+:16]=r;
 end
 assign out_data={count2>1?answer[31:16]:16'd0,count2>0?answer[15:0]:16'd0};
endmodule
'''
    # Attributes on an assign statement are supported by Vivado, but keep the
    # simple result adder attribute on an explicitly named wire for portability.
    core=core.replace('(* use_dsp="no" *)assign answer=floor_bits+{15\'d0,(|product[7:0])};',
                      '(* use_dsp="no" *)wire[15:0]ceil_bits=floor_bits+{15\'d0,(|product[7:0])};\n assign answer=ceil_bits;')
    (P/'leak_glif_mcm.sv').write_text(core,encoding='utf-8')
    timing=(W/'timing16.sv').read_text()
    timing=timing[:timing.index('`define GUARD_ADD_FRONTIER_TOP')]
    timing=timing.replace('sequential_leak16_timing #(parameter integer E=0)','sequential_leak16_glif_mcm_timing')
    timing=timing.replace('sequential_leak16 #(.E(E),.B(16))core','sequential_leak16_glif_mcm core')
    timing += '''module top_sequential_leak16_glif_mcm(input wire clk,rst,in_valid,out_ready,input wire[31:0]u_in,input wire[17:0]beta_in,input wire[1:0]available,
 output wire in_ready,out_valid,output wire[1:0]take,out_count,output wire[31:0]out_data,output wire narrow_mode);
 (* KEEP_HIERARCHY="yes",DONT_TOUCH="yes" *)sequential_leak16_glif_mcm_timing fixture(.*);
endmodule
'''
    (P/'timing_glif_mcm.sv').write_text(timing,encoding='utf-8')
    route=(W/'route16.tcl').read_text().replace('^top_sequential_leak16_e[0-6]$','^top_sequential_leak16_glif_mcm$')
    route=route.replace('read_verilog -sv $here/leak_core16.sv','read_verilog -sv $here/leak_glif_mcm.sv')
    route=route.replace(' read_verilog -sv $here/leak_dsp.sv\n','')
    route=route.replace('read_verilog -sv $here/timing16.sv','read_verilog -sv $here/timing_glif_mcm.sv')
    (P/'route_glif_mcm.tcl').write_text(route,encoding='utf-8')
    bench=(P/'tb_glif_mcm_template.sv').read_text()
    (P/'tb_glif_mcm.sv').write_text(bench.replace('__COEFFICIENT_INITIALIZATION__','\n'.join(f'  legal_beta[{i}]={b};' for i,b in enumerate(coeffs))),encoding='utf-8')
    for file in ('run_native_glif_mcm.py','run_route_glif_mcm.py'):
        ast.parse((P/file).read_text())
    files=[Path(__file__),P/'leak_glif_mcm.sv',P/'timing_glif_mcm.sv',P/'route_glif_mcm.tcl',P/'tb_glif_mcm_template.sv',P/'tb_glif_mcm.sv',
           P/'run_native_glif_mcm.py',P/'run_route_glif_mcm.py',T/'stage2_results.json',A/'results.json',A/'activity_operands.npz',
           W/'actual_glif_expected.npz',W/'actual_glif_stim.txt',W/'timing16.sv',W/'route16.tcl',
           ROOT/'selective_energy_trial/run_selective_energy.py',ROOT/'common_layout_trial/run_guard_add_selective_route.py']
    save('preparation.json',dict(status='prepared_no_vendor_launch',domain=dict(U=[-32768,32767],beta=coeffs),
         exactness_arithmetic_model=dict(cases=scalar_cases,mismatches=exhaustive_mismatches,RTL_not_yet_executed=True),
         complete_representative_capture=dict(scalars=262528,channel_previous_spike_coefficient_reconstruction='pass',context_count=len(context_counts),
              selected_beta_counts={str(b):int((data['beta']==b).sum()) for b in coeffs}),
         trained_channels=sum(len(r['coefficient0'])for r in rows.values()),trained_coefficient_pairs=149,
         mechanism='Shared LUT MCM: beta=80+delta or160+delta; shared3U,5U,7U,9U and shifts; select absolute delta multiple then signed correction and exact quotient ceiling.',
         protocol='Unchanged two-independent-lane signed16 interface, two advancing-edge elastic latency, stable ordered consumption,94 fixture FFs, runtime beta input unchanged.',
         fairness='No coefficient selection, averaging standalone channel circuits, specialization to best coefficient, membrane narrowing, precision loss, reordering or model rerun.',
         scope='Checkpoint-coefficient restricted zero-DSP leakage primitive only; coefficient/channel lookup and previous-spike selection remain common upstream in every compared design. No area/timing/energy claim until measured.',
         source_sha256=pins(files)))
    print(json.dumps(dict(status='prepared_no_vendor_launch',exhaustive_cases=scalar_cases,representative_operations=262528,
                         coefficients=coeffs,distinct_pairs=len(pairs),channels=sum(len(r['coefficient0'])for r in rows.values())),indent=2))


if __name__=='__main__':main()
