"""Create a new U13 harness from the archived F5 protocol harness."""
from pathlib import Path
import hashlib
import json

P = Path(__file__).resolve().parent
SOURCE = P.parent/'residue_frontier_f5_trial/tb_frontier_compare.sv'
OUTPUT = P/'tb_frontier_u13_compare.sv'
assert not OUTPUT.exists(), 'Preserve prior harness'
text = SOURCE.read_text()
substitutions = [
    ('frontier_driver', 'frontier_u13_driver'),
    ('guard_add_frontier_f5', 'guard_add_frontier_u13'),
    ('tb_frontier_compare', 'tb_frontier_u13_compare'),
    ('[87:0]', '[103:0]'),
    ('[95:0]', '[111:0]'),
    ('[10:0]', '[12:0]'),
    ('mem_i[k][10:8]!={3{mem_i[k][7]}}', 'mem_i[k][12:8]!={5{mem_i[k][7]}}'),
    ('U11/I8', 'U13/I8'),
    ('11*k+:11', '13*k+:13'),
    ("11'd1023", "13'd4095"),
    ("11'd127", "13'd127"),
    ("11'h400", "13'h1000"),
    ("11'h7ff", "13'h1fff"),
    ('%022h', '%026h'),
    ('%024h', '%028h'),
    ('[55+:11]', '[65+:13]'),
    ('[66+:11]', '[78+:13]'),
    ('[77+:11]', '[91+:13]'),
    ('12*k+:12', '14*k+:14'),
    ("12'(uu+ii)", "14'(uu+ii)"),
    ('reg clk=0;always #3 clk=~clk;', 'reg clk=0;initial begin #6;forever #3 clk=~clk;end'),
    ('FRONTIER_COMPARE PASS', 'FRONTIER_U13_COMPARE PASS'),
]
for before, after in substitutions:
    assert before in text, before
    text = text.replace(before, after)
assert '11*k' not in text and '12*k' not in text and '11]' not in text
OUTPUT.write_text(text)
manifest = dict(source_file=str(SOURCE.resolve()), source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                generator_file=str(Path(__file__).resolve()), generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                output_file=str(OUTPUT.resolve()), output_sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                substitutions=substitutions,
                scope='New widths and module names; preserved plain integer oracle, reset cancellation, stalls, source hold, output freeze, ordered prefix, poison tails and four-advance protocol.')
(P/'tb_preparation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('U13 HARNESS PREPARED',manifest['output_sha256'])
