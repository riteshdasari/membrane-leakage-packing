"""Freeze the new cached runner; preserve all original preparation and v1 sources."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pins(paths):return{str(Path(p).resolve()):sha(p)for p in paths}
def main():
    target=P/'cached_native_v2_gate.json';assert not target.exists()
    parents=[P/'preparation.json',P/'scalar_cohort.json']
    for parent in parents:
        record=json.loads(parent.read_text())
        for kind in('source_sha256','artifact_sha256'):
            for path,wanted in record[kind].items():assert sha(path)==wanted,(kind,path)
    scripts=[P/'run_native_static9_v2.py',P/'import_completed_native_cached.py']
    for script in scripts:ast.parse(script.read_text())
    original=P/'run_native_static9.py';before=original.read_text();after=scripts[0].read_text()
    assert "a['beta'][pos]"in before and "a['expected_leak'][pos]"in before
    assert "coefficients[pos]"in after and "expected_leak[pos]"in after
    assert "with np.load(output)as a:"in after and "cached_native_v2_gate.json"in after
    source=[Path(__file__),original,*parents,
            P.parent.parent.parent/'selective_energy_trial/run_selective_energy.py',
            Path('C:/AMDDesignTools/2025.2/data/verilog/src/glbl.v')]
    record=dict(status='cached_native_v2_source_gate_pass',B=16,legal_state_signed_bits=9,
                source_sha256=pins(source),artifact_sha256=pins(scripts),
                change='Load the four NPZ arrays once before the output-row loop; retain vendor commands, original expected-output comparisons, count/latency gates and original v1 preparation pins. Add a separate gate pinning preserved v1 and new v2/importer.',
                original_v1_untouched=True,independent_cached_importer=True,
                scope='Source/preparation gate only; this is not vendor or model acceptance. Original preparation and runner remain byte-identical.')
    target.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(status=record['status'],gate=str(target.resolve()),runner_sha256=sha(scripts[0]),importer_sha256=sha(scripts[1]))))
if __name__=='__main__':main()
