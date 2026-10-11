"""Matched12ns optimized LUT E8 route, optional pinned synthesis checkpoint retry."""
from pathlib import Path
import argparse,hashlib,json,math,re,shutil,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sys.path.insert(0,str(ROOT/'common_layout_trial'))
import run_guard_add_selective_route as helper
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
def sources(nativefile):
    prep=read(P/'preparation.json');verify(prep['source_sha256']);verify(prep['artifact_sha256'])
    scalar=read(P/'scalar_cohort.json');verify(scalar['source_sha256']);verify(scalar['artifact_sha256'])
    native=read(nativefile);assert native['status']=='pass'and native['B']==16 and native['legal_state_signed_bits']==9 and native['cohort']=='pair'and native['stall']==0
    verify(native['source_sha256']);verify(native['artifact_sha256'])
    row,=[r for r in native['rows']if r['engine']==8];assert row['native_index']==1
    return prep['source_sha256']|prep['artifact_sha256']|scalar['source_sha256']|scalar['artifact_sha256']|pins([Path(__file__),nativefile,P/'preparation.json',P/'scalar_cohort.json',ROOT/'selective_energy_trial/run_selective_energy.py',ROOT/'common_layout_trial/run_guard_add_selective_route.py'])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--native-acceptance',required=True);ap.add_argument('--attempt',required=True)
    ap.add_argument('--resume-synth-from');args=ap.parse_args();assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
    nativefile=Path(args.native_acceptance).resolve();stamps=sources(nativefile)
    wd=P/'hardware'/f'route12_e8_{args.attempt}';assert not wd.exists();wd.mkdir(parents=True)
    reused=False;original=None
    if args.resume_synth_from:
        original=Path(args.resume_synth_from).resolve();assert original.is_dir()and original!=wd
        original_job=read(original/'route.job.json');original_args=original_job['argv']
        assert original_args[original_args.index('-tclargs')+1:original_args.index('-tclargs')+3]==['top_sequential_leak_static9_e8','12']
        producer=read(original/'source_provenance.json');verify(producer)
        for source in(P/'leak_core_static9.sv',P/'leak_dsp.sv',P/'timing_static9.sv',P/'route_static9.tcl'):
            assert producer[str(source)]==stamps[str(source)]==sha(source)
        assert(original/'synth/design.dcp').exists()and(original/'synth/provenance.txt').exists()
        origin=pins([original/'synth/design.dcp',original/'synth/provenance.txt',original/'source_provenance.json',original/'route.job.json'])
        stamps|=origin;write(wd/'checkpoint_origin.json',dict(status='completed_synthesis_reused',B=16,engine=8,original_source_sha256=producer,original_artifact_sha256=origin,arithmetic_and_constraints_unchanged=True))
        stamps|=pins([wd/'checkpoint_origin.json']);reused=True
    top='top_sequential_leak_static9_e8'
    provenance=hashlib.sha256(json.dumps(dict(top=top,period_ns=12,part='xc7a100tcsg324-1',sources=stamps),sort_keys=True).encode()).hexdigest()
    write(wd/'source_provenance.json',stamps)
    if reused:
        (wd/'synth').mkdir();shutil.copyfile(original/'synth/design.dcp',wd/'synth/design.dcp')
        (wd/'synth/provenance.txt').write_text(provenance+'\n')
    progress=P/f'route_e8_{args.attempt}_progress.json';assert not progress.exists()
    write(progress,dict(status='running',B=16,engine=8,directory=str(wd),source_sha256=stamps))
    try:
        verify(stamps)
        while base.free()<=2.45:time.sleep(5)
        command=[base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'route_static9.tcl','-tclargs',top,12,provenance,'resume'if reused else'fresh',wd]
        log=base.job([str(c).replace('\\','/')for c in command],wd,'route',stamps,2.3)
        assert f'FRONTIER_TIMING_ROUTED {top}'in log.read_text()
        full=helper.util(wd/'util.rpt');core=helper.util(wd/'core_util.rpt',False)
        account={k:int(v)for k,v in(line.split()for line in(wd/'fixture_accounting.txt').read_text().splitlines())}
        assert(account['launch_FF'],account['capture_FF'],account['fixture_FF'])==(55,39,94)
        assert full['FF']-core['FF']==94 and full['LUT']==core['LUT']and full['DSP']==core['DSP']==1
        assert full['occupied_slices']==account['full_occupied_slices']==account['core_slices_touched']+account['fixture_slices_touched']-account['shared_slices']
        slack=list(map(float,(wd/'slack.txt').read_text().splitlines()));boundary=list(map(float,(wd/'boundary_slack.txt').read_text().splitlines()))
        assert len(slack)==len(boundary)==2 and all(math.isfinite(v)for v in slack+boundary)
        lines=(wd/'provenance.txt').read_text().splitlines();fields=dict(line.split(maxsplit=1)for line in lines[1:])
        assert lines[0]==provenance and fields['TOP']==top and fields['VIVADO']=='2025.2'and fields['HD_CLK_SRC']=='BUFGCTRL_X0Y0'and float(fields['TARGET_NS'])==12
        verify(stamps)
        record=dict(status='pass'if min(slack+boundary)>=0 else'timing_failed',B=16,engine=8,label='static_signed9_pair_narrow_domain_cost_ablation',legal_state_signed_bits=9,top=top,core=core,full_fixture=full,fixture_FF=94,slice_accounting=account,WNS_ns=slack[0],WHS_ns=slack[1],boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],clock_period_ns=12,latency_advancing_edges=2,external_input_phase_ns=6,reused_completed_synthesis=reused,part='xc7a100tcsg324-1',source_sha256=stamps,provenance_sha256=provenance,artifact_sha256=pins(p for folder in(wd,wd/'synth')for p in folder.iterdir()if p.is_file()),scope='NARROW-DOMAIN staticpair costablation only: signed9legallysignextendedon16bitports, coefficients0..256. NoactualUrangecheckorfull16fallback. E5minusE8measurescombinedadmission/widesupportcost, notliteralcontroller-onlyoverhead.')
        write(wd/'hardware.json',record);write(progress,dict(status=record['status'],hardware_file=str(wd/'hardware.json'),hardware_sha256=sha(wd/'hardware.json')))
        print('ROUTE16 E8',core,slack,boundary,flush=True)
    except Exception as exc:
        write(progress,dict(status='retained_failure',B=16,engine=8,directory=str(wd),reason=repr(exc),source_sha256=stamps));raise
if __name__=='__main__':main()
