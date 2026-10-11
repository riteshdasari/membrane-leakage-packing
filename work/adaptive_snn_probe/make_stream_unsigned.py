"""Use unsigned wide residuals: remove centering adders and wide DSP biases."""
from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'stream_compact_leak.sv').read_text()
def change(a,b):
 global s
 assert s.count(a)==1,a
 s=s.replace(a,b)
change('wire signed[3:0]h=$signed({u[10],u[10:8]})+$signed({3\'b0,u[7]});',
 "wire signed[3:0]h=$signed(u[10:8]);")
change("wire[7:0]q0={~u0[7],u0[6:0]},q1={~u1[7],u1[6:0]};",
 'wire[7:0]q0=u0[7:0],q1=u1[7:0];')
change("wire[15:0]kw=16'd32768-({11'b0,coef}<<7);", "wire[15:0]kw=16'd0;")
change('wire signed[4:0]floor_low=p[16*l+12-:5];',
 "wire signed[10:0]floor_low={6'b0,p[16*l+12-:5]};")
s=s.replace('stream_compact','stream_unsigned')
s=s.replace('// E1: fixed wide DSP pair. E2: LUT pair. E3: LUT triple.',
 '// Wide pair: U=256*h+r, r unsigned8; no rounding of h or DSP C bias.\n// E1: fixed wide DSP pair. E2: LUT pair. E3: LUT triple.')
(P/'stream_unsigned_leak.sv').write_text(s)
for name in ['tb_stream_compact_leak.sv','check_stream_compact.py','check_stream_compact_models.py','route_stream_compact.tcl','run_stream_compact_route.py']:
 (P/name.replace('compact','unsigned')).write_text((P/name).read_text().replace('stream_compact','stream_unsigned'))
print('Created isolated unsigned-wide variant for adaptive and fixed engines')
