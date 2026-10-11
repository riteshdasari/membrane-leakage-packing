"""Additive EOF-only SDF derivative and exact annotation-path binding audit."""
from pathlib import Path
import importlib.util, re, sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
L=P.parent/'lut_isolation'
sys.path.insert(0,str(P.parent.parent/'selective_energy_trial'))
import run_selective_energy as b


def modules():
    sys.path.insert(0,str(L))
    import create_eof_only_sdf_derivative as helper
    import sdf_structure_audit_v1 as parser
    return helper,parser


def create(raw,target,hardware,additional_pins):
    raw,target,hardware=map(lambda x:Path(x).resolve(),(raw,target,hardware))
    assert raw!=target and not target.exists()
    artifacts=b.read(raw/'artifacts.json');b.verify(artifacts)
    provenance=b.read(raw/'provenance.json');b.verify(provenance)
    dcp=hardware.parent/'design.dcp';hw=b.read(hardware)
    b.verify(hw['source_sha256']);b.verify(hw['artifact_sha256'])
    assert hw['status']=='pass' and provenance[str(hardware)]==b.sha(hardware) and provenance[str(dcp)]==b.sha(dcp)
    helper,parser=modules()
    import verify_eof_only_sdf_derivative_v1 as independent
    target.mkdir(parents=True)
    cert=helper.create(raw/'routed.sdf',target/'routed.sdf',target/'sdf_structure_certificate.json')
    before=(raw/'routed.v').read_bytes()
    old=str(raw/'routed.sdf').replace('\\','/').encode()
    new=str(target/'routed.sdf').replace('\\','/').encode()
    pattern=b'$sdf_annotate("'+old+b'",'
    replacement=b'$sdf_annotate("'+new+b'",'
    assert before.count(pattern)==1
    after=before.replace(pattern,replacement)
    assert after.replace(replacement,pattern)==before
    (target/'routed.v').write_bytes(after)
    binding=dict(status='pass_exact_annotation_path_binding',raw_export_dir=str(raw),derived_export_dir=str(target),
        raw_verilog_file=str(raw/'routed.v'),raw_verilog_sha256=b.sha(raw/'routed.v'),
        derived_verilog_file=str(target/'routed.v'),derived_verilog_sha256=b.sha(target/'routed.v'),
        raw_SDF_argument=old.decode(),derived_SDF_argument=new.decode(),
        changed_quoted_sdf_annotation_arguments=1,all_other_verilog_bytes_identical=True,
        numerical_paths_and_timing_checks_unchanged=True,
        hardware_file=str(hardware),hardware_sha256=b.sha(hardware),dcp_file=str(dcp),dcp_sha256=b.sha(dcp),
        sdf_certificate_file=str(target/'sdf_structure_certificate.json'),sdf_certificate_sha256=b.sha(target/'sdf_structure_certificate.json'),
        raw_artifacts_manifest=str(raw/'artifacts.json'),raw_artifacts_manifest_sha256=b.sha(raw/'artifacts.json'),
        raw_provenance_file=str(raw/'provenance.json'),raw_provenance_sha256=b.sha(raw/'provenance.json'),
        helper_file=str(Path(helper.__file__).resolve()),helper_sha256=b.sha(helper.__file__),
        parser_file=str(Path(parser.__file__).resolve()),parser_sha256=b.sha(parser.__file__),
        independent_SDF_verifier_file=str(Path(independent.__file__).resolve()),independent_SDF_verifier_sha256=b.sha(independent.__file__),
        binder_file=str(Path(__file__).resolve()),binder_sha256=b.sha(__file__),
        timing_replay_accepted=False,causal_discrepancy_resolved=False)
    b.write(target/'export_binding_certificate.json',binding)
    stamps=provenance|additional_pins|b.pins([Path(__file__),helper.__file__,parser.__file__,independent.__file__,raw/'artifacts.json',raw/'provenance.json',
        raw/'routed.v',raw/'routed.sdf',target/'sdf_structure_certificate.json',target/'export_binding_certificate.json',hardware,dcp])
    b.write(target/'provenance.json',stamps)
    b.write(target/'artifacts.json',b.pins([target/name for name in ('routed.v','routed.sdf','provenance.json','sdf_structure_certificate.json','export_binding_certificate.json')]))
    verify(target)
    return binding


def verify(directory):
    directory=Path(directory).resolve()
    manifest=b.read(directory/'artifacts.json');b.verify(manifest)
    provenance=b.read(directory/'provenance.json');b.verify(provenance)
    binding=b.read(directory/'export_binding_certificate.json')
    assert binding['status']=='pass_exact_annotation_path_binding' and binding['derived_export_dir']==str(directory)
    helper,parser=modules()
    import verify_eof_only_sdf_derivative_v1 as independent
    assert binding['independent_SDF_verifier_file']==str(Path(independent.__file__).resolve()) and binding['independent_SDF_verifier_sha256']==b.sha(independent.__file__)
    for key in ('helper','parser','binder'):
        assert b.sha(binding[key+'_file'])==binding[key+'_sha256']
    assert binding['helper_sha256']==b.sha(helper.__file__) and binding['parser_sha256']==b.sha(parser.__file__)
    assert binding['binder_file']==str(Path(__file__).resolve()) and binding['binder_sha256']==b.sha(__file__)
    for key in ('raw_verilog','derived_verilog','hardware','dcp','sdf_certificate','raw_provenance'):
        assert b.sha(binding[key+'_file'])==binding[key+'_sha256']
    assert b.sha(binding['raw_artifacts_manifest'])==binding['raw_artifacts_manifest_sha256']
    raw=Path(binding['raw_export_dir']);b.verify(b.read(raw/'artifacts.json'));b.verify(b.read(raw/'provenance.json'))
    cert=b.read(binding['sdf_certificate_file'])
    independent_check=independent.verify(binding['sdf_certificate_file'])
    assert independent_check['status']=='pass_independent_SDF_derivative_reverification'
    assert cert['status']=='pass_certified_additive_SDF_structure_derivative'
    assert Path(cert['source'])==raw/'routed.sdf' and Path(cert['derivative'])==directory/'routed.sdf'
    assert b.sha(cert['source'])==cert['source_sha256'] and b.sha(cert['derivative'])==cert['derivative_sha256']
    original=Path(cert['source']).read_bytes();derived=Path(cert['derivative']).read_bytes()
    assert derived==original+bytes.fromhex(cert['exact_appended_hex'])
    old_record,old_text,repaired,_=parser.describe(cert['source'])
    new_record,new_text,_,_=parser.describe(cert['derivative'])
    assert old_record==cert['source_structural_audit'] and new_record==cert['derivative_structural_audit']
    assert repaired==new_text and new_record['strict_structurally_balanced']
    assert cert['exact_appended_hex'] in ('','0a2929290a') and cert['appended_closing_parentheses'] in (0,3)
    assert old_record['direct_root_cell_count']==new_record['direct_root_cell_count'] and old_record['cell_instances_sha256']==new_record['cell_instances_sha256']
    _,_,ot=parser.parse(old_text,allow_eof=True);_,_,nt=parser.parse(new_text)
    assert [(x.kind,x.text) for x in nt[:len(ot)]]==[(x.kind,x.text) for x in ot]
    assert [x.kind for x in nt[len(ot):]]==[')']*cert['appended_closing_parentheses']
    old=('$sdf_annotate("'+binding['raw_SDF_argument']+'",').encode()
    new=('$sdf_annotate("'+binding['derived_SDF_argument']+'",').encode()
    before=Path(binding['raw_verilog_file']).read_bytes();after=Path(binding['derived_verilog_file']).read_bytes()
    assert before.count(old)==1 and after.count(new)==1 and before.replace(old,new)==after and after.replace(new,old)==before
    assert Path(binding['hardware_file']).parent/'design.dcp'==Path(binding['dcp_file'])
    assert provenance[binding['dcp_file']]==binding['dcp_sha256']
    return dict(status='pass_exact_derived_export_reproduction',export_binding_file=str(directory/'export_binding_certificate.json'),
        export_binding_sha256=b.sha(directory/'export_binding_certificate.json'),
        SDF_structure_certificate_file=str(directory/'sdf_structure_certificate.json'),SDF_structure_certificate_sha256=b.sha(directory/'sdf_structure_certificate.json'),
        raw_SDF_sha256=cert['source_sha256'],derived_SDF_sha256=cert['derivative_sha256'],
        appended_closing_parentheses=cert['appended_closing_parentheses'],numerical_timing_changes=0,
        annotation_path_string_changes=1,causal_discrepancy_resolution_claimed=False)
