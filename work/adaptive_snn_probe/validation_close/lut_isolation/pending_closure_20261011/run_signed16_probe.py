"""Root-dispatched diagnostic only: original fixed16 DUT/SDF plus observations."""
from pathlib import Path
import argparse,json,re,shutil,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
W=P.parent.parent/'width16'
sys.path.insert(0,str(W));sys.path.insert(0,str(P.parent))
import certify_energy_export
sys.path.insert(0,str(P.parent.parent.parent/'selective_energy_trial'))
import run_selective_energy as b


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',action='store_true');ap.add_argument('--attempt',default='a0')
    a=ap.parse_args();assert a.run and re.fullmatch('[A-Za-z0-9_-]+',a.attempt)
    prepared=P/'signed16_probe_prepared';prep=b.read(prepared/'preparation.json')
    b.verify(prep['source_sha256']);b.verify(prep['prepared_sha256'])
    export=W/'hardware/export12_ottt_e2_ottt_stress_a0_e2'
    assert certify_energy_export.verify(export)['status']=='pass_exact_derived_export_reproduction'
    wd=P/'run_signed16_probe'/a.attempt;assert not wd.exists();wd.mkdir(parents=True)
    for name in ['monitor.sv','CARRY4_vendor.v','run.tcl']:shutil.copyfile(prepared/name,wd/name)
    stamps=b.pins([Path(__file__),prepared/'preparation.json',*[Path(x) for x in prep['source_sha256']],*[wd/n for n in ['monitor.sv','CARRY4_vendor.v','run.tcl']]])
    b.write(wd/'provenance.json',stamps)
    commands=[
      [b.VIVADO/'bin/xvlog.bat','-d','XIL_TIMING',wd/'CARRY4_vendor.v'],
      [b.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=2','-d','DUT_TOP=top_sequential_leak16_e2',export/'routed.v',wd/'monitor.sv'],
      [b.VIVADO/'bin/xvlog.bat',b.VIVADO/'data/verilog/src/glbl.v'],
      [b.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays',
       '-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','work',
       '-L','simprims_ver','-L','secureip','-L','unisims_ver','tb_sequential_energy_replay16','glbl','-s','sim'],
      [b.VIVADO/'bin/xsim.bat','sim','-testplusarg','TRACE='+prep['trace'],'-testplusarg','ROWS=7340',
       '-testplusarg','ROI_FIRST=3','-testplusarg','ROI_LAST=3678','-tclbatch',wd/'run.tcl']]
    logs=[]
    for i,cmd in enumerate(commands):
        argv=[str(x).replace('\\','/') for x in cmd]
        assert not any(x in argv for x in ['-notimingchecks','-nospecify','-sdfnowarn','-sdfnoerror'])
        b.write(wd/'progress.json',dict(stage=i,argv=argv,diagnostic_only=True))
        try:log=b.job(argv,wd,f'tool_{i}',stamps,1.2)
        except AssertionError:
            log=wd/f'tool_{i}.log'
            if i!=4 or not log.exists() or 'REPLAY mismatch E2 row' not in log.read_text(errors='replace'):raise
        logs.append(log)
    texts=[p.read_text(errors='replace') for p in logs];elab,out=texts[3:5]
    annotation=[x for x in elab.splitlines() if 'SDF backannotation was successful' in x]
    gates=dict(work_CARRY4_bound='Compiling module work.CARRY4' in elab,
      certified_original_DUT_annotation=len(annotation)==1 and '/export12_ottt_e2_ottt_stress_a0_e2/routed.sdf' in annotation[0] and 'tb_sequential_energy_replay16/dut' in annotation[0],
      annotation_not_ignored='$sdf_annotate will be ignored' not in elab,
      no_compile_warning_or_error=not any(re.search(r'\b(?:WARNING|ERROR):',t) for t in texts[:4]),
      no_runtime_timing_warning=not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation',out),
      observation_window_complete='FIXED16_PROBE_WINDOW_COMPLETE' in out,
      snapshots_present='FIXED16_SNAPSHOT' in out)
    mismatch=[dict(row=int(r),got=g,expected=e) for r,g,e in re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)',out)]
    result=dict(status='completed_observation_only_signed16_probe' if all(gates.values()) else 'rejected_signed16_probe',gates=gates,
      replay_mismatches=mismatch,original_failure_reproduced=any(x['row']==2175 for x in mismatch),
      snapshots=[x for x in out.splitlines() if x.startswith('FIXED16_SNAPSHOT')],annotation_success_lines=annotation,
      commands=[[str(x).replace('\\','/') for x in cmd] for cmd in commands],artifact_sha256=b.pins(logs),
      original_netlist_SDF_vendor_model_modified=False,timing_checks_disabled=False,
      diagnostic_only=True,full_trace_energy_acceptance=False,cause_established=False)
    b.verify(stamps);b.write(wd/'diagnostic.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
