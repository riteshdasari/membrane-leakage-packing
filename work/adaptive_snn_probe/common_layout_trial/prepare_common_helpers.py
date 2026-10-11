"""Create isolated common-layout verification/route helpers from frozen templates.

No HDL jobs run here. Refuse to overwrite any existing generated helper.
"""
from pathlib import Path
P = Path(__file__).resolve().parent
B = P.parent / 'baseline_retime_trial'

def save(name, text):
    target = P / name
    assert not target.exists(), target
    target.write_text(text, encoding='utf-8')

tb = (B / 'tb_guard_add_retime.sv').read_text().replace('retime', 'common').replace('RETIME', 'COMMON')
tb = tb.replace('guard_add #(.E(V))dut', 'guard_add_retime #(.E(V))dut')
tb = tb.replace('guard_add_common #(.E(V+2))dut', 'guard_add_common #(.V(V))dut')
save('tb_guard_add_common.sv', tb)

check = (B / 'check_guard_add_retime.py').read_text().replace('retime', 'common').replace('RETIME', 'COMMON')
check = check.replace("'../guard_add.sv', '../check_guard_add.py']", "'../guard_add.sv', '../check_guard_add.py',\n           '../baseline_retime_trial/guard_add_retime.sv']")
check = check.replace('"{ORIGINAL}/guard_add.sv" "{P}/tb_guard_add_common.sv"', '"{ORIGINAL}/guard_add.sv" "{ORIGINAL}/baseline_retime_trial/guard_add_retime.sv" "{P}/tb_guard_add_common.sv"')
check = check.replace('arithmetic_issues=req if variant in (0, 2) else 0', 'arithmetic_issues=req if variant != 3 else 0')
check = check.replace('Original guard_add E2/E3 instantiated directly', 'Retimed guard_add_retime E2/E3 instantiated directly')
check = check.replace('Exact hybrid/LUT baseline-retiming equivalence', 'Fixed common-layout high-part correction equivalence')
check = check.replace('retimed hybrid/LUT', 'two fixed common-layout variants')
save('check_guard_add_common.py', check)

snn = (B / 'check_guard_add_retime_snn.py').read_text().replace('retime', 'common').replace('RETIME', 'COMMON')
snn = snn.replace('Baseline retiming only', 'Fixed common-layout correction only')
save('check_guard_add_common_snn.py', snn)

fixture = (B / 'guard_add_retime_timing.sv').read_text().replace('retime', 'common').replace('RETIME', 'COMMON')
fixture = fixture.replace('parameter E=2', 'parameter V=0').replace('#(.E(E))', '#(.V(V))')
fixture = fixture.replace('#(.E(ENGINE))', '#(.V(ENGINE))')
fixture = fixture.replace('top_guard_add_common_hybrid,2', 'top_guard_add_common_v0,0')
fixture = fixture.replace('top_guard_add_common_lut,3', 'top_guard_add_common_v1,1')
save('guard_add_common_timing.sv', fixture)

tcl = (B / 'route_guard_add_retime.tcl').read_text().replace('retime', 'common').replace('RETIME', 'COMMON')
tcl = tcl.replace('^top_guard_add_common_(hybrid|lut)$', '^top_guard_add_common_v[01]$')
save('route_guard_add_common.tcl', tcl)

route = (B / 'run_guard_add_retime_route.py').read_text().replace('retime', 'common').replace('RETIME', 'COMMON')
route = route.replace("'../guard_add.sv', '../check_guard_add.py']", "'../guard_add.sv', '../check_guard_add.py',\n                      '../baseline_retime_trial/guard_add_retime.sv']")
route = route.replace('TOPS = dict(top_guard_add_common_hybrid=2, top_guard_add_common_lut=3)', 'TOPS = dict(top_guard_add_common_v0=0, top_guard_add_common_v1=1)')
route = route.replace('VARIANTS = dict(top_guard_add_common_hybrid=0, top_guard_add_common_lut=1)', 'VARIANTS = dict(TOPS)')
route = route.replace("(row['requests'] if engine == 2 else 0)", "(row['requests'] if row['variant'] != 3 else 0)")
route = route.replace('(1 if TOPS[top] == 2 else 0)', '1')
route = route.replace('Exact common fixed guard-add baseline', 'Exact fixed common-layout guard-add variant')
save('run_guard_add_common_route.py', route)
print('Created six isolated helpers; no HDL tools executed.')
