"""Explicit one-engine checkpoint retry; retain the original fixed16 failed attempt."""
from pathlib import Path
import argparse,hashlib,json,math,re,shutil,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sys.path.insert(0,str(ROOT/'common_layout_trial'))
import run_guard_add_selective_route as helper
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
LABELS=['adaptive_precomp','fixed_split2','LUT2','scalar_DSP2','scalar_DSP1','adaptive_post','shift2_beta128']
DSP=[1,1,0,2,1,1,0]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--engine',type=int,choices=range(7),required=True)
    ap.add_argument('--original-attempt',required=True);ap.add_argument('--attempt',required=True);args=ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt);e=args.engine
    original=Path(args.original_attempt).resolve();assert original.is_dir()
    original_job=read(original/'route.job.json');original_args=original_job['argv']
    assert original_args[original_args.index('-tclargs')+1:original_args.index('-tclargs')+3]==[f'top_sequential_leak16_e{e}','12']
    original_sources=read(original/'source_provenance.json');verify(original_sources)
    prep=read(P/'preparation_v2.json');verify(prep['source_sha256']);verify(prep['artifact_sha256'])
    for source in(P/'leak_core16.sv',P/'leak_dsp.sv',P/'timing16.sv',P/'route16.tcl'):
        assert original_sources[str(source)]==sha(source)
    nativefile=P/'hardware/native_general_s0_a0/acceptance.json';native=read(nativefile)
    assert native['status']=='pass'and native['B']==16;verify(native['source_sha256']);verify(native['artifact_sha256'])
    assert(original/'synth/design.dcp').exists()and(original/'synth/provenance.txt').exists()
    wd=P/'hardware'/f'route12_e{e}_{args.attempt}';assert not wd.exists();wd.mkdir(parents=True)
    stamps=prep['source_sha256']|prep['artifact_sha256']|pins([Path(__file__),P/'preparation_v2.json',nativefile,P/'route16.tcl',original/'synth/design.dcp',original/'synth/provenance.txt',original/'source_provenance.json',original/'route.job.json',ROOT/'selective_energy_trial/run_selective_energy.py',ROOT/'common_layout_trial/run_guard_add_selective_route.py'])
    write(wd/'checkpoint_origin.json',dict(status='completed_synthesis_reused',B=16,engine=e,original_source_sha256=original_sources,original_artifact_sha256=pins([original/'synth/design.dcp',original/'synth/provenance.txt',original/'source_provenance.json']),arithmetic_and_constraints_unchanged=True))
    stamps|=pins([wd/'checkpoint_origin.json']);top=f'top_sequential_leak16_e{e}'
    prov=hashlib.sha256(json.dumps(dict(top=top,period_ns=12,part='xc7a100tcsg324-1',sources=stamps),sort_keys=True).encode()).hexdigest()
    write(wd/'source_provenance.json',stamps);(wd/'synth').mkdir();shutil.copyfile(original/'synth/design.dcp',wd/'synth/design.dcp');(wd/'synth/provenance.txt').write_text(prov+'\n')
    while base.free()<=2.45:time.sleep(5)
    command=[base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'route16.tcl','-tclargs',top,12,prov,'resume',wd]
    log=base.job([str(c).replace('\\','/')for c in command],wd,'route',stamps,2.3)
    assert f'FRONTIER_TIMING_ROUTED {top}'in log.read_text();verify(stamps)
    full=helper.util(wd/'util.rpt');core=helper.util(wd/'core_util.rpt',False)
    account={k:int(v)for k,v in(line.split()for line in(wd/'fixture_accounting.txt').read_text().splitlines())}
    assert(account['launch_FF'],account['capture_FF'],account['fixture_FF'])==(55,39,94)
    assert full['FF']-core['FF']==94 and full['LUT']==core['LUT']and full['DSP']==core['DSP']==DSP[e]
    assert full['occupied_slices']==account['full_occupied_slices']==account['core_slices_touched']+account['fixture_slices_touched']-account['shared_slices']
    slack=list(map(float,(wd/'slack.txt').read_text().splitlines()));boundary=list(map(float,(wd/'boundary_slack.txt').read_text().splitlines()))
    assert len(slack)==len(boundary)==2 and all(math.isfinite(v)for v in slack+boundary)
    lines=(wd/'provenance.txt').read_text().splitlines();assert lines[0]==prov
    fields=dict(line.split(maxsplit=1)for line in lines[1:]);assert fields['TOP']==top and float(fields['TARGET_NS'])==12
    record=dict(status='pass'if min(slack+boundary)>=0 else'timing_failed',B=16,engine=e,label=LABELS[e],top=top,core=core,full_fixture=full,fixture_FF=94,slice_accounting=account,WNS_ns=slack[0],WHS_ns=slack[1],boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],clock_period_ns=12,latency_advancing_edges=2,external_input_phase_ns=6,reused_completed_synthesis=True,part='xc7a100tcsg324-1',source_sha256=stamps,provenance_sha256=prov,artifact_sha256=pins(p for folder in(wd,wd/'synth')for p in folder.iterdir()if p.is_file()),scope='Source-identical fixed16 checkpoint retry; common94FF fixture; retained originalattempt.')
    write(wd/'hardware.json',record);print('ROUTE16 CHECKPOINT RETRY',e,core,slack,boundary,flush=True)
if __name__=='__main__':main()
