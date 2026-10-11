"""Prepare strict12ns fixed16 SDF/SAIF power audit without launching any tools."""
from pathlib import Path
import hashlib,json,ast
P=Path(__file__).resolve().parent;TRIAL=P.parent.parent/'sequential_paper_trial'
assert not(P/'energy16_preparation.json').exists()
export=(TRIAL/'export12.tcl').read_text();(P/'export16_12.tcl').write_text(export,encoding='utf-8')
power=(TRIAL/'power12.tcl').read_text().replace('$engine > 5','$engine > 6').replace('Engine outside 0..5','Engine outside 0..6').replace('tb_sequential_energy_replay/dut','tb_sequential_energy_replay16/dut')
(P/'power16_12.tcl').write_text(power,encoding='utf-8')
audit=(TRIAL/'audit_power12.py').read_text()
audit=audit.replace("P=Path(__file__).resolve().parent;OLD=P.parent/'selective_energy_trial'","P=Path(__file__).resolve().parent;OLD=P.parent.parent/'selective_energy_trial'")
audit=audit.replace("ROOT='tb_sequential_energy_replay/dut';SCALARS=17408;PERIOD_PS=12000","ROOT='tb_sequential_energy_replay16/dut';PERIOD_PS=12000")
audit=audit.replace('import xml.etree.ElementTree as ET','import xml.etree.ElementTree as ET\nimport numpy as np')
audit=audit.replace('e in range(6)','e in range(7)').replace('engine in range(6)','engine in range(7)')
old="""    native=read(P/'stage4_native_acceptance_v4.json');assert native['status']=='pass'
    verify(native['source_sha256']);verify(native['artifact_sha256'])
"""
assert audit.count(old)==1;audit=audit.replace(old,'')
audit=audit.replace("check['kind']=='actual'and check['stall']==0","check['B']==16 and check['cohort'] in ('actual_glif','actual128') and check['stall']==0 and check['capture']==1")
needle="    row,=[r for r in check['rows']if r['engine']==e];assert row==d['native_row']"
insert="""    row,=[r for r in check['rows']if r['engine']==e];assert row==d['native_row']
    expectation_path=Path(d['cohort_expectation_file']);expectation=read(expectation_path)
    assert d['source_sha256'][str(expectation_path)]==sha(expectation_path)
    verify(expectation['source_sha256']);cohort=expectation['cohorts'][check['cohort']]
    verify(cohort['artifact_sha256']);actual=np.load(cohort['expected_outputs_file'])
    assert row['neurons']==cohort['operations'] and row['requests']==cohort['expected_requests_by_engine'][e]
    ends=np.repeat(np.cumsum(actual['frame_lengths']),actual['frame_lengths'])
    if e==6:assert check['cohort']=='actual128'and np.all(actual['beta']==128)
"""
assert audit.count(needle)==1;audit=audit.replace(needle,insert)
olddecoder="""            want=0
            for k in range(take):
                u=(U>>(12*k))&4095;u=u-4096 if u&2048 else u;b=(B>>(9*k))&511
                assert b<=256;want|=(-((-u*b)//256)&4095)<<(12*k)
            queue.append((take,want));requests+=1;neurons+=take"""
newdecoder="""            want=0
            source=[]
            assert av==(2 if ends[neurons]-neurons>=2 else 1)
            for k in range(av):
                u=(U>>(16*k))&65535;u=u-65536 if u&32768 else u;b=(B>>(9*k))&511
                assert b<=256 and u==int(actual['U'][neurons+k]) and b==int(actual['beta'][neurons+k])
                source.append((u,b))
            pair=av==2
            if e==4:pair=False
            elif e==1:pair=pair and source[0][1]==source[1][1]
            elif e in (0,5):pair=pair and source[0][1]==source[1][1]and -256<=source[0][0]<=255 and -256<=source[1][0]<=255 and(e==5 or source[0][1]>=64)
            assert take==(2 if pair else 1)
            for k,(u,b)in enumerate(source[:take]):
                scalar=-((-u*b)//256);assert scalar==int(actual['expected_leak'][neurons+k])
                want|=(scalar&65535)<<(16*k)
            queue.append((take,want,int(e in (0,5)and take==2),index));requests+=1;neurons+=take"""
assert audit.count(olddecoder)==1;audit=audit.replace(olddecoder,newdecoder)
audit=audit.replace("            assert queue and(count,data)==queue.popleft();retired+=1;retired_neurons+=count;last=index","            assert queue\n            qcount,qdata,qmode,qcycle=queue.popleft()\n            assert (count,data,mode)==(qcount,qdata,qmode)and index-qcycle==2\n            retired+=1;retired_neurons+=count;last=index")
audit=audit.replace("neurons==retired_neurons==SCALARS","neurons==retired_neurons==row['neurons']==cohort['operations']")
audit=audit.replace("== 78 and accounting['launch_FF'] == 47 and accounting['capture_FF'] == 31","== 94 and accounting['launch_FF'] == 55 and accounting['capture_FF'] == 39")
audit=audit.replace("hardware['full_fixture']['FF'] - hardware['core']['FF'] == 78","hardware['full_fixture']['FF'] - hardware['core']['FF'] == 94")
audit=audit.replace("assert hardware['clock_period_ns'] == 12 and hardware['part']","assert hardware['B']==16 and hardware['clock_period_ns'] == 12 and hardware['part']")
audit=audit.replace('[1,1,0,2,1,1][engine]','[1,1,0,2,1,1,0][engine]')
audit=audit.replace("/SCALARS","/check['scalar_updates']").replace('fixture_FF=78','fixture_FF=94').replace('common 78-FF','common 94-FF')
audit=audit.replace("scope='New leakage trace, golden fixture, exact routed/SDF replay and SAIF interval audit'","scope='Fixed16 actual source operands, signed9 pair metadata, golden fixture, exact routed/SDF replay and SAIF interval audit'")
assert 'SCALARS'not in audit and 'range(6)'not in audit and '>>12'not in audit
ast.parse(audit);(P/'audit_power16_12.py').write_text(audit,encoding='utf-8')
inputs=[Path(__file__),TRIAL/'audit_power12.py',TRIAL/'export12.tcl',TRIAL/'power12.tcl',P/'preparation_v2.json',P/'domain_acceptance_glif_v2.json']
outputs=[P/n for n in('export16_12.tcl','power16_12.tcl','audit_power16_12.py','tb_energy16_12.sv')]
pin=lambda ps:{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in ps}
answer=dict(status='prepared_unexecuted',B=16,clock_ns=12,fixture_FF=94,launch_FF=55,capture_FF=39,
            source_sha256=pin(inputs),artifact_sha256=pin(outputs),
            audit='Every native source operand and frame-end admission independently checked from expected_npz, exact retirement/count/mode/natural2edge latency, all rows routed/SDF replay, full physical SAIF alias/constants/source audits inherited from frozen predecessor; no unknown physical activity accepted')
(P/'energy16_preparation.json').write_text(json.dumps(answer,indent=2)+'\n')
print('ENERGY16 AUDITOR EXPORT POWER PREPARED NO TOOLS',flush=True)
