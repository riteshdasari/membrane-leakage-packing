"""Create trial-local RTL from the frozen adaptive source; never edit references."""
from pathlib import Path
import hashlib
P = Path(__file__).resolve().parent
COMMON = P.parent/'common_layout_trial'


def main():
    source = (COMMON/'guard_add_selective.sv').read_bytes()
    assert hashlib.sha256(source).hexdigest() == 'b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48'
    text = source.decode().replace('module guard_add_selective #(parameter integer V=0)',
        'module guard_add_selective_isolated #(parameter integer V=3, parameter integer ISOLATE=1)', 1)
    old = """  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  assign corrected_high=selected_hu5+adjustment;"""
    assert old in text
    new = """  // Output use remains guarded by correction_step. This weaker enable
  // avoids extending the out_ready/output_space timing cone into arithmetic.
  // During backpressure with an exceptional output it intentionally stays on.
  wire isolation_enable=v2&&(|work_mask);
  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  wire signed[4:0]isolated_hu=(ISOLATE&&!isolation_enable)?5'd0:selected_hu5;
  wire signed[4:0]isolated_adjustment=(ISOLATE&&!isolation_enable)?5'd0:adjustment;
  assign corrected_high=isolated_hu+isolated_adjustment;"""
    text = text.replace(old, new, 1)
    dest = P/'guard_add_selective_isolated.sv'
    assert not dest.exists(), 'Preserve prepared RTL; edit the trial copy explicitly'
    dest.write_text(text, encoding='utf-8')
    timing = (COMMON/'guard_add_selective_timing.sv').read_text()
    timing = timing.replace('guard_add_selective_timing', 'guard_add_selective_isolated_timing')
    timing = timing.replace('guard_add_selective #(.V(V)) core', 'guard_add_selective_isolated #(.V(V),.ISOLATE(1)) core')
    start = timing.index('`GUARD_ADD_SELECTIVE_TOP(top_guard_add_selective_v0,0)')
    end = timing.index('`undef GUARD_ADD_SELECTIVE_TOP', start)
    timing = timing[:start]+'`GUARD_ADD_SELECTIVE_TOP(top_guard_add_selective_isolated_v3,3)\n'+timing[end:]
    (P/'guard_add_selective_isolated_timing.sv').write_text(timing)
    route = (COMMON/'route_guard_add_selective.tcl').read_text()
    route = route.replace('^top_guard_add_selective_v[0-3]$', '^top_guard_add_selective_isolated_v3$')
    route = route.replace('$here/guard_add_selective.sv', '$here/guard_add_selective_isolated.sv')
    route = route.replace('$here/guard_add_selective_timing.sv', '$here/guard_add_selective_isolated_timing.sv')
    # Source lives one sibling farther down than the frozen route script.
    route = route.replace('$here/../guard_add.sv', '$here/../guard_add.sv')
    (P/'route_operand_isolation.tcl').write_text(route)
    print('Prepared isolated core, unchanged fixture structure and matched route script')


if __name__ == '__main__': main()
