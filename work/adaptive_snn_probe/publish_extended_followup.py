"""Publish new bounded evidence without replacing the preceding delivery."""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parents[1]/'outputs'
STEM='membrane_adaptive_extended_checks'
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
assert not(OUT/f'{STEM}.md').exists()
certificate=read(ROOT/'sum_width_trial/certificates.json');assert certificate['status']=='pass_interval_certificate'
review=read(ROOT/'followup_width_review/independent_checks.json')
repair=read(ROOT/'followup_width_review/histogram_repair/acceptance.json');assert repair['status']=='pass'
screen=read(ROOT/'followup_width_review/histogram_repair/results.json');assert len(screen['rows'])==72
completion=read(ROOT/'certified_u11_trial/completion.json');assert completion['status']in('complete','completed_with_retained_failures')
native=read(ROOT/'certified_u11_trial/native_acceptance.json');assert native['status']=='pass'and len(native['cohorts'])==6
hw=read(ROOT/'certified_u11_trial/hardware_acceptance.json');assert len(hw['rows'])==5
for cohort in native['cohorts']:
    assert all(row['status']=='pass'for row in cohort['rows'])
    assert len({row['numeric_retirement_sha256']for row in cohort['rows']})==1
    if cohort['kind']!='main':
        assert all(item['state_spike_count_class_disagreements']==0 for row in cohort['rows']for item in row['actual_retired_feedback'])
energy=read(ROOT/'followup_energy_review/independent_acceptance.json')
accepted={r['engine']:r for r in energy['engines']if r['accepted_energy']}
assert set(accepted)=={0,2,3,4}
ratios={f'adaptive_vs_{e}_dynamic_percent':100*(accepted[0]['estimated_dynamic_energy_pJ_per_scalar_update']/accepted[e]['estimated_dynamic_energy_pJ_per_scalar_update']-1)for e in(2,3,4)}
cohorts=[]
for beta in(128,224,231,240,248,252,254,256):
    for T in(32,128,256):
        rows=[r for r in screen['rows']if r['beta']==beta and r['timesteps']==T]
        assert len(rows)==3
        absolute=sum(r['policy_stats']['absolute_U8']['service_clocks_one_edge_analytic']for r in rows)
        shared=sum(r['policy_stats']['shared_high_only']['service_clocks_one_edge_analytic']for r in rows)
        union=sum(r['policy_stats']['union_U8_shared_high']['service_clocks_one_edge_analytic']for r in rows)
        fixed=sum(r['fixed8']['service_clocks_one_edge_analytic']for r in rows)
        assert union<=absolute and fixed<=union
        cohorts.append(dict(beta=beta,timesteps=T,absolute_service_clocks=absolute,shared_service_clocks=shared,
            union_service_clocks=union,fixed8_service_clocks=fixed,union_service_reduction_percent=100*(absolute-union)/absolute,
            unchanged_original_control=beta==224 and T==32))
adex=read(ROOT/'adex_component_screen/results.json')
current_width=read(ROOT/'current_width_screen/v2/results.json')
diagnostic=read(ROOT/'u11_fixed_functional_diagnostic/acceptance.json')
summary=dict(status='bounded_extended_checks_closed_with_explicit_limits',
    certified_domain='U in[-686,245], any signed8 I; signed11 internal sums signextended to12; highbase signed6',
    certified_native=native,certified_hardware=hw,certified_completion=completion,
    original_generic_U11_energy=energy,energy_comparisons=ratios,
    software_range_cohorts=cohorts,sum_width_certificates=certificate,
    independent_width_audit=review,histogram_repair=repair,
    adex_component_screen=adex,current_width_screen=current_width,fixed8_mapped_functional_diagnostic=diagnostic,
    trained_benchmark_status='Not executed beyond saved three-seed digits architecture; CIFAR10/DVS checkpoints/framework not locally available. Published sources and fair trace gate documented separately.',
    prior_report_preserved=True,
    contribution_status='Exact construction and controller remain useful research artifacts; current additions do not establish a strong adaptive advantage over strongest fixed controls. Novelty is qualified and does not replace benefit.',
    further_untested=['Broader directly trained LIF model/dataset traces and full test accuracy',
        'Complete AdEx fixed-point reference, official runtime comparison and hardware',
        'Board energy and external-I/O timing closure',
        'Timed replay/energy of newly specialized bounded-domain RTL',
        'Application-backed invariant intrinsic product packing at natural latency; generic constant leakage trials already exist'])
sp=OUT/f'{STEM}.summary.json';write(sp,summary)
lines=['# Further checks of membrane-aware adaptive packing','',
    'The work remains useful, but these checks do not yet establish a strong adaptive paper contribution. The exact arithmetic, safety proofs, verified RTL and strong fixed controls are reusable evidence; the measured tradeoff must determine the paper claim.','',
    '## New hardware control','',
    'A uniform safe interval covering all three original shift3 model certificates is U=[-686,245], with any signed8 current. All five designs use this same specialized caller contract. Full fabric sums shrink to11 bits and high-part metadata to6 bits, with exact signextension to the original12-bit interface. This contract is narrower than the earlier full-word U11 primitive.','',
    'All six native arithmetic/protocol cohorts passed: every238,592 legal scalar pair plus mixed lanes/prefix failures, and the unchanged shift1/shift3 model streams under both stall settings. Model hardware replay covers the first48 held-out inputs per seed; actual retired sums reproduce every saved membrane,spike,count and class in that replay. Full360-example accuracy remains a software-reference result.','',
    'Routed core resources follow, excluding the same290-FF fixture. Internal6ns setup/hold closure is reported separately from raw external ports:','']
labels={0:'Adaptive DSP',1:'Fixed8 precomputed DSP',2:'Native FOUR12 DSP+four LUT lanes',3:'Fixed LUT8',4:'Same-policy adaptive LUT'}
for row in hw['rows']:
    c=row['core'];lines.append(f"- {labels[row['engine']]}: {c['LUT']} LUT,{c['FF']} FF,{c['DSP']} DSP; {c['occupied_slices']} touched slices; WNS{row['WNS_ns']:.3f}ns,WHS{row['WHS_ns']:.3f}ns; {row['status']}.")
lines+=['','These new rows do not inherit the earlier generic-domain energy estimates. Their timed replay and energy remain unmeasured.','',
    '## Closed energy gap for the earlier one-edge U11 cores','',
    'The original unstalled shift3 trace retires635,904 scalar additions per engine. Four complete SDF replays passed, including all known invalid output rows. Their physical activity and power annotations passed strict independent audits. The fixed8 precomputed engine retained a timed data failure and has no accepted energy number.','']
for e in(0,2,3,4):lines.append(f"- {labels[e]}: {accepted[e]['estimated_dynamic_energy_pJ_per_scalar_update']:.6f}pJ/update vendor-estimated dynamic energy.")
lines+=['',f"Adaptive is {ratios['adaptive_vs_2_dynamic_percent']:.4f}% higher than the strongest fixed native hybrid and {-ratios['adaptive_vs_4_dynamic_percent']:.4f}% lower than the same-policy adaptive LUT. The fixed-LUT difference is below the combined export serialization bound and does not establish energy separation. These are complete290-FF measurement-fixture estimates, not core-only/board/full-neuron energy.",
    '',f"The fixed8 mapped-functional diagnostic status is `{diagnostic['status']}`. Its timing and energy gates remain excluded even if this diagnostic passes.",'',
    'The first postprocessor had a helper-import error after four complete numerical replays. A stale subagent also changed a frozen runner log line; the source gate rejected acceptance. The exact original SHA256 was restored and all source/artifact pins independently rechecked. Original failures remain retained. Auditor version2 changes only two stale returned fixture labels(338→290), with identical strict gates/calculations.','',
    '## Range, shared-high and proof checks','',
    'All72 predeclared coefficient/horizon/seed variants are retained, including poor accuracy cases. Only beta224/T32 reproduces the original shift3 dynamics. The shared-high union remains software-only and gives a small scheduling improvement; fixed8 uses no more service clocks in any cohort. It has no mapped cost or energy advantage.','',
    f"The largest aggregate union service reduction over the original admission policy is {max(r['union_service_reduction_percent']for r in cohorts):.4f}% across the24 predeclared three-seed cohorts. This is an analytic service count, not a clock-frequency/area result.",
    '', 'An independent audit recomputed all72 interval rows and216 sum/high-width contracts, including reset-discontinuity enumeration and directed residue cases. Ten generic-versus-specialized rows change native lane count; using membrane width+1 blindly would manufacture a SIMD cliff. The actual sum certificate decides FOUR12 versus TWO24.','',
    'The original software screen shallow-copied its nested histograms. A separate full72-row rerun repaired144 earlier-horizon histograms, validated all216 distributions, and proved every other result field identical. The original erroneous files remain retained. Fixed8 zero histogram placeholders are not measured distributions.','',
    '## AdEx and broader benchmarks','',
    'The eight published AdEx single-neuron cases were independently screened with their original Euler dynamics. Only one passed the strict scalar/vector numerical gate; six had matching spike lists, while two diverged in spike timing. All failures remain. Seven vector cases show a narrow stored voltage with a wide intrinsic intermediate under the illustrative units. This is component scope evidence, not Brian2 validation, integer exactness,8-lane workload or classifier accuracy.','',
    'Trained SNN benchmarks are still needed. A small primitive paper can use traced neuron updates from trained static-image LIF CNNs and event-based LIF networks, with unchanged reference accuracy and exact state/spike replay. The published benchmark sources, local availability and numerical admission gate are documented in [benchmark_contract.md](../work/adaptive_snn_probe/benchmark_followup/benchmark_contract.md). No broader trained-model execution is being claimed.','',
    'A further48-case U/current-width screen proves that narrowing U alone saves no high-base metadata when the current is equally wide or wider. The original signed4 tail metadata is only legal for signed8 current. Native ONE48 must remain a control above24 sum bits; a separately retained version2 corrects that omission in the first analytic screen. No mapped result follows from these formulas.','',
    'Eight packed residue fields are not eight complete wide additions implemented solely in DSP fabric: high-part arithmetic and reconstruction remain in LUTs/registers. Count useful completed neuron operations and total hardware cost; lane count alone can exaggerate DSP efficiency. The native four-DSP-lane plus four-LUT-lane control also completes eight additions per request.','',
    'Fixed8 attains the minimum number of requests for the current eight-addition interface. A different workload cannot reverse that capacity bound. A strong adaptive claim must therefore demonstrate a meaningful resource/energy frontier or a different justified operation; it cannot rest on novel naming or deliberately weak controls.','',
    'Complete AdEx,broader trained SNN traces,new-specialization energy,board measurements and a genuine application-backed product candidate remain explicitly untested. Earlier constant/programmable leakage experiments must be retained before calling a product idea new.']
rp=OUT/f'{STEM}.md';rp.write_text('\n'.join(lines)+'\n')
# Close pinned ancestors and newly delivered evidence, excluding simulator build trees.
files={}
def add(p,expected=None):
    p=Path(p).resolve();actual=sha(p)
    if expected is not None:assert actual==expected,('Changed pinned file',str(p))
    files[str(p)]=dict(sha256=actual,bytes=p.stat().st_size)
def visit(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if isinstance(k,str)and(len(k)>2 and k[1]==':'):
                if isinstance(v,str)and len(v)==64 and all(c in'0123456789abcdef'for c in v):add(k,v)
                elif isinstance(v,dict)and 'sha256'in v:add(k,v['sha256'])
            visit(v)
    elif isinstance(value,list):
        for v in value:visit(v)
for name,record in read(OUT/'membrane_adaptive_packing_verdict.manifest.json')['files'].items():add(name,record['sha256'])
for folder in('range_horizon_trial','sum_width_trial','followup_width_review','natural_energy_trial',
        'followup_energy_review','followup_adex_review','certified_u11_trial','adex_component_screen',
        'benchmark_followup','current_width_screen','u11_fixed_functional_diagnostic'):
    for p in(ROOT/folder).rglob('*'):
        if not p.is_file()or any(x in('xsim.dir','.Xil','__pycache__')for x in p.parts):continue
        if p.suffix in('.py','.sv','.tcl','.md','.json','.log','.rpt','.txt','.npz','.saif','.v','.sdf','.dcp','.jou','.xml'):
            add(p)
            if p.suffix=='.json':visit(read(p))
for p in(Path(__file__),ROOT/'verify_extended_followup.py',ROOT/'finish_extended_followup.py',sp,rp):add(p)
mp=OUT/f'{STEM}.manifest.json';write(mp,dict(status='pass_hash_closure',files=files,
    bytes=sum(r['bytes']for r in files.values()),report_sha256=sha(rp),summary_sha256=sha(sp),
    scope='New evidence plus preserved prior closure; simulator generated build trees excluded, all recorded pins checked'))
print(json.dumps(dict(status=summary['status'],files=len(files),manifest_sha256=sha(mp),
    energy_comparisons=ratios,hardware=[dict(engine=r['engine'],core=r['core'])for r in hw['rows']]),indent=2),flush=True)
