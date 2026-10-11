"""Only low-memory native replay of pinned original shift1/shift3 LIF streams."""
from pathlib import Path
import json,hashlib,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent;OLD=ROOT/'trained_reference_native_trial';STUDY=ROOT/'trained_reference_admission_study'
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sys.path.insert(0,str(OLD))
from prepare_restored_work import load_groups,sha,pins,verify
MAP={0:'natural_adaptive_DSP_E5',1:'natural_fixed8_DSP_E2',2:'natural_fixed8_LUT_E4',3:'natural_adaptive_LUT'}


def take_for(e,pairs,pos):
    av=min(8,len(pairs)-pos)
    if e in (1,2):return av
    n=min(av,5)
    while n<av and -128<=pairs[pos+n][0]<=127:n+=1
    return n


def source_pins():
    h=base.read(P/'harness_preparation.json')
    assert h['source_sha256']==sha(h['source_file']) and h['generated_tb_sha256']==sha(P/'tb_native.sv')
    assert h['generator_sha256']==sha(P/'prepare_trial.py')
    paths=[Path(__file__),P/'verify_trial.py',P/'prepare_trial.py',P/'tb_native.sv',P/'harness_preparation.json',
        ROOT/'frontier_natural.sv',ROOT/'adaptive_natural_lut.sv',OLD/'verify_restored_native.py',
        OLD/'prepare_restored_work.py',OLD/'range_certificate.json',STUDY/'manifest.json',
        STUDY/'restored_reference_summary.json',base.P/'run_selective_energy.py']
    verify(base.read(STUDY/'manifest.json')['files'])
    for shift in (1,3):
        paths.extend([STUDY/f'leak_shift{shift}'/name for name in ('stream_stim.txt','reference_ledger.json')])
        for stall in (0,1):
            paths.append(OLD/'results'/f'native_shift{shift}_stall{stall}_a1/native_checks.json')
    paths.extend(ROOT/'results'/f'model_seed{s}.npz' for s in range(3))
    return pins(paths)


def job(command,wd,label,stamps,gate=1.2):
    while base.free()<=gate:time.sleep(5)
    return base.job([str(x).replace('\\','/') for x in command],wd,label,stamps,gate)


def native(shift,stall):
    stamps=source_pins();wd=P/'results'/f'native_shift{shift}_stall{stall}_a0';assert not wd.exists();wd.mkdir(parents=True)
    source=STUDY/f'leak_shift{shift}';groups=load_groups(source/'stream_stim.txt')
    ledger=base.read(source/'reference_ledger.json');assert len(groups)==len(ledger['ledger'])==9216
    with (wd/'stream_stim.txt').open('w',newline='\n') as stream:
        stream.write(str(len(groups))+'\n')
        for gap,pairs in groups:
            stream.write(f'{len(pairs)} {gap}\n')
            for u,i in pairs:stream.write(f'{u&8191:04x} {i&8191:04x}\n')
    (wd/'reference_ledger.json').write_bytes((source/'reference_ledger.json').read_bytes())
    predictions=[]
    for e in range(4):
        requests=0;hist={str(k):0 for k in range(1,9)}
        for _,pairs in groups:
            pos=0
            while pos<len(pairs):
                n=take_for(e,pairs,pos);pos+=n;requests+=1;hist[str(n)]+=1
        predictions.append(dict(engine=e,implementation=MAP[e],requests=requests,take_histogram=hist))
    base.write(wd/'workload.json',dict(status='pass',shift=shift,groups=9216,neurons=635904,
        predictions=predictions,original_stream_sha256=sha(source/'stream_stim.txt'),
        stimulus_sha256=sha(wd/'stream_stim.txt'),ledger_sha256=sha(wd/'reference_ledger.json'),
        source_sha256=stamps,scope='Same original numeric operands encoded with sign extension13; original shifts and thresholds unchanged'))
    stamps|=pins([wd/'stream_stim.txt',wd/'reference_ledger.json',wd/'workload.json']);base.write(wd/'provenance.json',stamps)
    commands=[
        [base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}','-d','CAPTURE_TRACE=0',
         ROOT/'frontier_natural.sv',ROOT/'adaptive_natural_lut.sv',P/'tb_native.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_natural_lif_compare','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-R'],
        [sys.executable,'-B',P/'verify_trial.py','--directory',wd,'--shift',shift,'--stall',stall]]
    for n,command in enumerate(commands):job(command,wd,f'tool_{n}',stamps)
    check=base.read(wd/'native_checks.json');verify(stamps)
    print('NATURAL LIF PASS',shift,stall,[(r['engine'],r['service_clocks']) for r in check['rows']],flush=True)
    return check|dict(check_file=str(wd/'native_checks.json'))


if __name__=='__main__':
    assert '--run' in sys.argv
    cohorts=[native(shift,stall) for shift in (1,3) for stall in (0,1)]
    base.write(P/'acceptance.json',dict(status='pass',cohorts=cohorts,source_sha256=source_pins(),
        scope='Native arithmetic/protocol and actual retired-sum feedback of original LIFreferences only; no route,power,AdEx or new coefficient'))
