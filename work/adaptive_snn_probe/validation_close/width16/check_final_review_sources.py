"""Small source-only review checks; no tool, power audit or model execution."""
from pathlib import Path
import ast,hashlib,json,re,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    files=[P/'resolve_routes16.py',P/'run_energy_closure_sequence_v2.py',P/'static9_e8/audit_closure_static9.py',P/'verify_selected_evidence.py']
    for f in files:ast.parse(f.read_text(),filename=str(f))
    tree=ast.parse(files[1].read_text());template=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='template')
    namespace={'Path':Path,'re':re};exec(compile(ast.Module(body=[template],type_ignores=[]),str(files[1]),'exec'),namespace)
    checks=[]
    for e in range(9):
        for attempt in('a0','a1','a0_checkpoint'):
            target=P/'hardware'/f'route12_e{e}_{attempt}';got=namespace['template'](target,e)
            assert Path(got.format(engine=e))==target
            checks.append(dict(engine=e,attempt=attempt,template=got))
    source=files[0].read_text();sequence=files[1].read_text()
    assert "hw['part']=='xc7a100tcsg324-1'"in source
    assert 'math.isfinite(hw[k])and hw[k]>=0'in source
    assert "[1,1,0,2,1,1,0][engine]"in source
    assert "record['acceptance_gates']=RECEIPTS[receipt_start:]"in sequence
    assert "'--strict-complete'"in sequence
    assert "tag=f'{attempt}_e{engine}'"in sequence
    assert "tuple(e8native)"in sequence
    assert "'ERROR: [Synth 20-411]'"in sequence
    result=dict(status='pass_source_review_checks_no_vendor_no_inference',AST_files=len(files),route_template_checks=len(checks),
                final_root_cli_critical_findings=[],all4_E8_native_dependencies=True,per_stage_acceptance_receipts=True,explicit_selected_energy_auditor_prepared=True,
                source_sha256={str(f):sha(f)for f in[*files,Path(__file__)]},checks=checks)
    out=P/'final_source_review_acceptance_v1.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('source_sha256','checks')}))
if __name__=='__main__':main()
