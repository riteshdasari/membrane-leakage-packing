"""Prepare a second bounded isolation candidate; first-trial evidence is read-only."""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent
FIRST=P.parent/'operand_isolation_trial'
COMMON=P.parent/'common_layout_trial'


def main():
    frozen=(COMMON/'guard_add_selective.sv').read_bytes()
    assert hashlib.sha256(frozen).hexdigest()=='b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48'
    text=frozen.decode().replace('module guard_add_selective #(parameter integer V=0)',
        'module guard_add_selective_isolated #(parameter integer V=3, parameter integer ISOLATE=1)',1)
    old="""  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  assign corrected_high=selected_hu5+adjustment;"""
    assert old in text
    new="""  // Fold zero isolation into the existing one-hot lane selection.
  // selected_mask has one bit set for work, and is zero when no lane is bad.
  // This keeps a separate v2/any-work enable out of the selected HU adder.
  reg[3:0]masked_hu;
  reg masked_negative;
  always @* begin
   masked_hu=0;masked_negative=0;
   for(integer r=0;r<6;r=r+1)begin
    masked_hu=masked_hu|(hu[r]&{4{selected_mask[r]}});
    masked_negative=masked_negative|(hi[r][0]&selected_mask[r]);
   end
  end
  wire selected_any=|selected_mask;
  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  wire signed[4:0]isolated_hu=ISOLATE?{masked_hu[3],masked_hu}:selected_hu5;
  wire signed[4:0]isolated_adjustment=ISOLATE?
   (selected_any?(masked_negative?5'b11111:5'b00001):5'd0):adjustment;
  assign corrected_high=isolated_hu+isolated_adjustment;"""
    text=text.replace(old,new,1)
    dest=P/'guard_add_selective_isolated.sv'
    assert not dest.exists(),'Preserve trial source'
    dest.write_text(text)
    for name in ('guard_add_selective_isolated_timing.sv','route_operand_isolation.tcl',
        'export_operand_isolation.tcl','run_operand_isolation.py',
        'annotation_operand_isolation.tcl','audit_operand_isolation.py',
        'tb_operand_isolation_compare.sv','verify_operand_isolation.py'):
        (P/name).write_bytes((FIRST/name).read_bytes())
    contract=(FIRST/'CONTRACT.md').read_text()
    start=contract.index('One implementation change:')
    end=contract.index('Keep the frozen V2/V3',start)
    contract=contract[:start]+'''One implementation change: fold zero isolation into the existing one-hot
selected_mask. OR the six masked membrane-high operands and current signs;
mask the ±1 adjustment to zero when selected_mask is zero. No separate late v2
gate is added. Stale invalid exceptional metadata and backpressured exceptions
may keep the corrector active. Actual output writes require a selected bit.
No new registers, lanes, precision, layout, scheduler or workload selection.

The first postselection trial remains unchanged in ../operand_isolation_trial:
152 LUT / 268 FF / 1 DSP, WNS -0.230 ns at 6 ns. Its worst path is classifier to
advance/metadata CE, predominantly routing, so no direct adder-delay cause is
claimed. Its timing-failed checkpoint cannot supply a valid 6 ns energy result.

'''+contract[end:]
    contract=contract.replace('Operand-isolation experiment','Folded operand-isolation experiment',1)
    contract=contract.replace('Inspect mapped isolated operands','Inspect mapped one-hot isolated operands')
    (P/'CONTRACT.md').write_text(contract)
    print('Prepared one-hot folded isolation; all first-trial files retained')


if __name__=='__main__':main()
