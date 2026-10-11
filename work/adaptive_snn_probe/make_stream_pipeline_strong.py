"""Keep the checked original core intact; change only LUT quotient arithmetic."""
from pathlib import Path
P = Path(__file__).resolve().parent
source = (P/'stream_pipeline_leak.sv').read_text()
source = source.replace('stream_pipeline_leak', 'stream_pipeline_strong_leak').replace('stream_pipeline_dsp', 'stream_pipeline_strong_dsp')
source = source.replace('parameter E=0, DC=25, CW=0', 'parameter E=0, DC=25, CW=0, STYLE=(DC==25?1:0)')
product = '''wire signed[7:0]quotient;
    if(STYLE==2)begin:split_quotient
     wire signed[2:0]h=u[10:8];
     wire signed[7:0]hx={{5{h[2]}},h};
     wire[12:0]rx={5'b0,u[7:0]};
     (* use_dsp="no" *) wire signed[7:0]hp;
     (* use_dsp="no" *) wire[12:0]lp;
     if(DC==25)begin
      assign hp=(hx<<<4)+(hx<<<3)+hx;
      assign lp=(rx<<4)+(rx<<3)+rx;
     end else begin assign hp=h*$signed({1'b0,COEF});assign lp=u[7:0]*COEF;end
     assign quotient=hp+$signed({3'b0,lp[12:8]});
    end else begin:full_quotient
     wire signed[15:0]ux={{5{u[10]}},u};
     (* use_dsp="no" *) wire signed[15:0]prod;
     if(DC==25&&STYLE==1)assign prod=(ux<<<5)-(ux<<<3)+ux;
     else if(DC==25)assign prod=(ux<<<4)+(ux<<<3)+ux;
     else assign prod=u*DCWIRE;
     assign quotient=prod[15:8];
    end'''
hybrid = '''wire signed[15:0]ux={{5{u[10]}},u};
    (* use_dsp="no" *) wire signed[15:0]prod;
    if(DC==25)assign prod=(ux<<<4)+(ux<<<3)+ux;else assign prod=u*dc0;'''
lut = '''wire signed[15:0]ux={{5{u[10]}},u};
   (* use_dsp="no" *) wire signed[15:0]prod;
   if(DC==25)assign prod=(ux<<<4)+(ux<<<3)+ux;else assign prod=u*dc;'''
assert source.count(hybrid)==source.count(lut)==1
source = source.replace(hybrid, product.replace('COEF','coef0').replace('DCWIRE','dc0'))
source = source.replace(lut, product.replace('COEF','coef0').replace('DCWIRE','dc'))
source = source.replace('m1<={u,prod[15:8]}', 'm1<={u,quotient}')
source = source.replace('next1[19*l+:19]={u,prod[15:8]}', 'next1[19*l+:19]={u,quotient}')
source = '// Strong LUT lane variants: STYLE1 signed-digit constant, STYLE2 split quotient.\n'+source
(P/'stream_pipeline_strong_leak.sv').write_text(source)
