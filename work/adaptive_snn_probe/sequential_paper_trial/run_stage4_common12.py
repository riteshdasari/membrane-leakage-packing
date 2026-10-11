"""Six-control matched common-clock acceptance; preserve 6 ns failures and physical placements."""
from pathlib import Path
import math,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sys.path.insert(0,str(ROOT/'common_layout_trial'))
import run_guard_add_selective_route as helper
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
def main():
    complete=read(P/'stage4_common9_acceptance.json');assert complete['status']in('pass','completed_with_retained_failures')
    verify(complete['source_sha256']);verify(complete['artifact_sha256'])
    origins=[];stamps=pins([Path(__file__),P/'common12.tcl',P/'stage4_common9_acceptance.json'])
    for e in range(6):
        p=P/'hardware'/f'common9_e{e}_a0/hardware.json'
        d=read(p);assert d['engine']==e and d['clock_period_ns']==9
        verify(d['source_sha256']);verify(d['artifact_sha256'])
        out=P/'hardware'/f'common12_e{e}_a0';assert not out.exists();out.mkdir(parents=True)
        origins.append((p,d,out));stamps.update(pins([p,p.parent/'design.dcp']))
    wd=P/'hardware/common12_job_a0';assert not wd.exists();wd.mkdir(parents=True)
    script=wd/'inputs.txt'
    script.write_text(''.join(f'{{{d["top"]}}} {{{(p.parent/"design.dcp").as_posix()}}} {{{out.as_posix()}}}\n'for p,d,out in origins))
    stamps.update(pins([script]));write(wd/'provenance.json',stamps)
    while base.free()<=2.45:time.sleep(5)
    command=[base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'common12.tcl','-tclargs',script]
    log=base.job([str(c).replace('\\','/')for c in command],wd,'common12',stamps,2.3);verify(stamps)
    rows=[]
    for p,d,out in origins:
        assert f'COMMON12_RETIMED {d["top"]}'in log.read_text()
        assert(out/'physical_before.tsv').read_bytes()==(out/'physical_after.tsv').read_bytes()
        full=helper.util(out/'util.rpt');core=helper.util(out/'core_util.rpt',False)
        for key in('LUT','FF','DSP','RAMB18','RAMB36'):
            assert core[key]==d['core'][key]and full[key]==d['full_fixture'][key]
        core['occupied_slices_reported']=core['occupied_slices'];core['occupied_slices']=d['core']['occupied_slices']
        slack=list(map(float,(out/'slack.txt').read_text().splitlines()));assert len(slack)==2 and all(math.isfinite(x)for x in slack)
        record=dict(status='pass'if min(slack)>=0 else'timing_failed',engine=d['engine'],label=d['label'],top=d['top'],core=core,full_fixture=full,fixture_FF=78,slice_accounting=d['slice_accounting'],clock_period_ns=12,external_input_phase_ns=6.0,latency_advancing_edges=2,part=d['part'],WNS_ns=slack[0],WHS_ns=slack[1],original_hardware_file=str(p),original_6ns_status=d['status'],physical_cells_and_connections_unchanged=True,source_sha256=stamps,artifact_sha256=pins(q for q in out.iterdir()if q.is_file()),scope='Same physical routes optimized for6ns, operated at common12ns with matched falling-edge6ns raw input phase; no datapath or pipeline changes; OOC fixture, not board Fmax')
        write(out/'hardware.json',record);rows.append(str(out/'hardware.json'));print('COMMON12 ACCEPTANCE',d['engine'],core,slack,flush=True)
    write(P/'stage4_common12_acceptance.json',dict(status='pass'if all(read(Path(p))['status']=='pass'for p in rows)else'completed_with_retained_failures',rows=rows,source_sha256=stamps,artifact_sha256=pins(map(Path,rows))))
if __name__=='__main__':main()
