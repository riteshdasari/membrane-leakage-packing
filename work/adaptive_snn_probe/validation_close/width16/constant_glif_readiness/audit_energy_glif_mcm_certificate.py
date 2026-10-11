# The complete new trace/physical audit is still required after this certificate.
_uncertified_annotation=annotation


def annotation(directory):
 _directory=Path(directory).resolve();_evidence=read(_directory/'evidence.json')
 _replay=read(Path(_evidence['replay_dir'])/'replay_checks.json')
 _export=Path(_replay['export_artifacts_file']).resolve().parent
 _spec=importlib.util.spec_from_file_location('glif_mcm_certified_export_reproduction',W/'certify_energy_export.py')
 _binder=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_binder)
 _certificate=_binder.verify(_export)
 _result=_uncertified_annotation(_directory)
 _result['certified_export_audit']=_certificate
 return _result
