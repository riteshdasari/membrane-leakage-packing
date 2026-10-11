"""Numerical proof evidence for CW0 whole-product C folding; no Vivado run.

This checks the packing algebra and declared mathematical leakage oracle.
It does not simulate RTL, pipeline control, memory, or a full neuron update.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

P=Path(__file__).resolve().parent;R=P/'results'
RTL=P/'stream_pipeline_whole_leak.sv'
VALUES=[-1024,-1023,-1000,-513,-512,-511,-257,-256,-255,-129,-128,-127,
        -65,-64,-63,-33,-32,-31,-1,0,1,15,16,31,32,63,64,127,128,129,
        255,256,257,511,512,513,1000,1022,1023]
def sha(data):return hashlib.sha256(data).hexdigest()
def leakage_oracle(u,d):return -((-(u*(256-d)))//256)
def c_field(u,d):
 h=u//256;hp=d*h
 assert -128<=hp<=127
 return ((hp&255)^128)<<8
def decoded_quotient(field):
 bits=((field>>8)&255)^128
 return bits-256 if bits&128 else bits
def main():
 pin=sha(RTL.read_bytes());minimum=65536;maximum=-1;scalar=0
 for d in range(32):
  for u in range(-1024,1024):
   field=c_field(u,d)+d*(u%256)
   assert field==32768+d*u and 0<=field<65536
   q=decoded_quotient(field)
   assert q==(d*u)//256
   assert u-q==leakage_oracle(u,d)
   minimum=min(minimum,field);maximum=max(maximum,field);scalar+=1
 assert (minimum,maximum)==(1024,64481)
 pairs=0;stale_bypass=0
 stale_words=[0,0xffffffff,0x80008000,0x7fff7fff,0x5555aaaa]
 for d in range(32):
  for a in VALUES:
   for b in VALUES:
    A=(a%256)+((b%256)<<16)
    C=c_field(a,d)+(c_field(b,d)<<16)
    assert 0<=A<2**24 and 0<=C<2**32
    product=d*A+C
    assert product&65535==32768+d*a
    assert (product>>16)&65535==32768+d*b
    assert product>>32==0
    bypass=d==0 or (a==0 and b==0)
    for lane,u in enumerate([a,b]):
     q=0 if bypass else decoded_quotient((product>>(16*lane))&65535)
     assert (u-q)&2047==leakage_oracle(u,d)&2047
    if bypass:
     for held in stale_words:
      # The bypass flag masks extracted quotient, not the biased packed bits.
      for lane,u in enumerate([a,b]):
       held_q=decoded_quotient((held>>(16*lane))&65535)
       q=0 if bypass else held_q
       assert (u-q)&2047==leakage_oracle(u,d)&2047
      stale_bypass+=1
    pairs+=1
 assert scalar==65536 and pairs==48672
 assert sha(RTL.read_bytes())==pin,'RTL changed while arithmetic screen ran'
 result=dict(scope='CW0 wide-pair packing algebra only; no RTL simulation or hardware measurement',
  created_utc=datetime.now(timezone.utc).isoformat(),
  source_sha256={RTL.name:pin},script_sha256={Path(__file__).name:sha(Path(__file__).read_bytes())},
  contract=dict(U_min=-1024,U_max=1023,delta_min=0,delta_max=31,
                oracle='ceil((256-delta)*U/256), computed by signed mathematical ceiling division',
                decomposition='U=256*h+r; h=floor(U/256), r=U mod256',
                c_field='256*(128+delta*h), encoded by inversion of signed-eight-bit product sign',
                dsp_field='32768+delta*U',quotient='signed8({~P[15],P[14:8]})',
                output='U-quotient; bypass forces quotient0'),
  rows=[dict(test='all scalar U/delta combinations',cases=scalar,mismatches=0,
             minimum_field=minimum,maximum_field=maximum),
        dict(test='adversarial packed pairs',cases=pairs,mismatches=0,
             membranes=VALUES,coefficients=list(range(32)),carry_into_bit32=0),
        dict(test='arbitrary stale DSP words under bypass',cases=stale_bypass,mismatches=0,
             stale_words=[f'{x:08x}'for x in stale_words])],
  exhaustive_bound_proof=dict(delta_times_U_min=-31744,delta_times_U_max=31713,
                             biased_field_min=1024,biased_field_max=64481,
                             reasoning='Each independent field fits unsigned16, so low-lane product plus C cannot carry into the next lane; upper field cannot carry into bit32.'),
  limitations=['Packing algebra matches pinned source expressions but does not execute HDL.',
               'Narrow triple and CW1 centered arithmetic retain earlier methods and are outside this new whole-product proof.',
               'Pipeline stalls/reset/order and all engine outputs require the separate RTL suites.'])
 R.mkdir(exist_ok=True);dest=R/'stream_pipeline_whole_math_checks.json'
 dest.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
