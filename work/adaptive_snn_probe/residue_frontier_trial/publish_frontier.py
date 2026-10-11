"""Publish completed frontier measurements; fail closed on missing validation."""
from pathlib import Path
import json
import sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
import run_frontier as run
import audit_frontier_power_v4 as audit
OUT = P.parents[2]/'outputs'
STEM = 'membrane_residue_frontier_trial'
NAMES = ['Fixed six residue lanes','Fixed eight, late recovery',
         'Fixed eight, precomputed recovery','Fixed eight DSP/LUT hybrid',
         'Fixed eight LUT-only','Adaptive six/seven/eight prefix admission']


def link(path, title):
    return f'[{title}](<{Path(path).resolve().as_posix()}>)'


def main():
    targets = [OUT/(STEM+s) for s in ('.md','.summary.json','.manifest.json')]
    assert not any(p.exists() for p in targets), 'Preserve publications'
    allpins = {}
    def add(mapping):
        run.verify(mapping)
        for name, digest in mapping.items():
            assert name not in allpins or allpins[name] == digest, ('Pin conflict',name)
            allpins[name] = digest
    add(run.frozen()); add(run.sources()); add(run.functional())
    # Historical failed preparation used preserved executed source versions.
    historical = P/'results/native_models_0_a0'
    replacements = {'prepare_frontier_work.py':historical/'prepare_executed.py',
                    'run_frontier.py':historical/'run_executed.py'}
    failures = []
    jobs = []
    for wd in sorted((P/'results').iterdir()):
        if not wd.is_dir(): continue
        for jobfile in sorted(wd.glob('*.job.json')):
            job = run.read(jobfile)
            stamps = {}
            for name,digest in job['source_sha256'].items():
                path = Path(name)
                if run.sha(path) != digest:
                    assert wd == historical and path.name in replacements
                    path = replacements[path.name]
                    assert run.sha(path) == digest
                stamps[str(path)] = digest
            add(stamps)
            if job['returncode']:
                logfile = jobfile.with_name(jobfile.name.replace('.job.json','.log'))
                text = logfile.read_text(errors='replace')
                allowed = (wd == historical and jobfile.name == 'prepare.job.json') or (
                    wd.name.startswith('route_e') and jobfile.name == 'route.job.json'
                    and 'ERROR: [Synth 20-411]' in text
                    and (wd/'route_resume.job.json').exists()
                    and run.read(wd/'route_resume.job.json')['returncode'] == 0) or (
                    wd.name=='supply2_models_0_a0' and jobfile.name=='verify.job.json'
                    and "d['take']==n" in text
                    and (wd/'verify_repaired.job.json').exists()
                    and run.read(wd/'verify_repaired.job.json')['returncode']==0) or (
                    wd.name=='power_e0_a0' and jobfile.name=='audit.job.json'
                    and 'too many values to unpack' in text
                    and run.read(P/'results/power_e0_a1/audit_v4.job.json')['returncode']==0)
                assert allowed, ('Unexpected failed job',jobfile)
                failures.append(dict(job=str(jobfile),returncode=job['returncode'],
                                     scope='Preparation-order assertion, verified-checkpoint tool recovery, idle-policy verifier correction, or explicit-top checkpoint attribution audit correction'))
            jobs.append(dict(file=str(jobfile),returncode=job['returncode'],
                             seconds=job['seconds'],free_GiB_at_start=job['free_GiB_at_start'],
                             sampled_peak_tool_tree_RSS_sum_GiB=job['sampled_peak_tool_tree_RSS_sum_GiB']))
    native = []
    for name in run.functional():
        d = run.read(name)
        for key in ('source_sha256','candidate_file_sha256'): add(d[key])
        add(run.read(Path(name).parent/'provenance.json'))
        native.append(d | dict(check_file=name,check_sha256=run.sha(name)))
    models, = [x for x in native if x['kind']=='models' and not x['backpressure']]
    stress, = [x for x in native if x['kind']=='main' and not x['backpressure']]
    assert len({row['numeric_retirement_sha256'] for x in native if x['kind']=='models' for row in x['rows']}) == 1
    hardware = []; powers = {}
    for e in range(6):
        wd = P/'results'/f'route_e{e}_a0'
        hw = run.read(wd/'hardware.json')
        assert hw['engine']==e and hw['clock_period_ns']==6
        add(hw['source_sha256']); add(hw['artifact_sha256']); add(hw['functional_check_sha256'])
        assert hw['full_fixture']['FF']-hw['core']['FF']==290
        hardware.append(hw)
        if hw['status']=='pass':
            powerdir = P/'results'/f'power_e{e}_a1'
            checked = audit.annotation(powerdir)
            assert checked == run.read(powerdir/'power_audit.json')
            evidence = run.read(powerdir/'evidence.json')
            add(evidence['source_sha256']); add(evidence['artifact_sha256'])
            replay = run.read(Path(evidence['replay_dir'])/'replay_checks.json')
            assert Path(evidence['replay_dir']).name == f'replay_e{e}_a3'
            assert replay['timing_simulation_method']=='AMD transport, zero pulse error and rejection, slow/max'
            add(replay['source_sha256']); add(replay['artifact_sha256'])
            powers[str(e)] = checked
        else:
            assert hw['status']=='timing_failed' and min(hw['WNS_ns'],hw['WHS_ns'])<0
            assert not (P/'results'/f'power_e{e}_a0').exists()
    supplydir = P/'results/supply2_models_0_a0'
    supply = run.read(supplydir/'frontier_checks.json')
    assert supply['status']=='pass' and all(r['service_clocks']==354816 and r['requests']==317952 for r in supply['rows'])
    assert all(r['saved_states_spikes_counts_classes_match'] for r in supply['rows'])
    assert supply['rows'][0]['numeric_retirement_sha256']==models['rows'][0]['numeric_retirement_sha256']
    add(supply['source_sha256']); add(supply['candidate_file_sha256']); add(run.read(supplydir/'provenance.json'))
    conditions = [x for x in powers.values()]
    if conditions:
        ref = conditions[0]
        for value in conditions:
            assert value['device_settings']==ref['device_settings']
            assert value['fixture_FF']==290 and value['native_interval_audit']['scalar_updates']==635904
            assert [(v['name'],v['voltage']) for v in value['voltage_sources']]==[(v['name'],v['voltage']) for v in ref['voltage_sources']]
            assert {k:v for k,v in value['thermal_settings'].items() if k!='AMBIENT'} == {k:v for k,v in ref['thermal_settings'].items() if k!='AMBIENT'}
    def comparison(e):
        result = dict(baseline_engine=e,
            model_service_change_percent=(models['rows'][5]['service_clocks']/models['rows'][e]['service_clocks']-1)*100,
            model_issue_change_percent=(models['rows'][5]['requests']/models['rows'][e]['requests']-1)*100,
            stress_service_change_percent=(stress['rows'][5]['service_clocks']/stress['rows'][e]['service_clocks']-1)*100,
            LUT_change=hardware[5]['core']['LUT']-hardware[e]['core']['LUT'],
            FF_change=hardware[5]['core']['FF']-hardware[e]['core']['FF'],
            DSP_change=hardware[5]['core']['DSP']-hardware[e]['core']['DSP'])
        if '5' in powers and str(e) in powers:
            result['estimated_dynamic_energy_change_percent']=(powers['5']['dynamic_energy_J']/powers[str(e)]['dynamic_energy_J']-1)*100
        return result
    comparisons = [comparison(e) for e in range(5)]
    invalid_replays=[]
    for check in (P/'results').glob('replay*/replay_checks.json'):
        d=run.read(check)
        if d['status']=='invalid':
            assert d['timing_diagnostics']
            assert all('at time 3 ns' in x['line'] for x in d['timing_diagnostics'])
            invalid_replays.append(dict(file=str(check),diagnostics=d['timing_diagnostics'],energy_used=False))
    rejected_method_replays=[]
    for e in range(6):
        wd=P/'results'/f'replay_e{e}_a1'
        log=(wd/'tool_3.log').read_text(errors='replace')
        options=run.read(wd/'tool_2.job.json')['argv']
        assert '-transport_int_delays' not in options
        if e in (0,1):
            assert f'FRONTIER_ROUTE_REPLAY PASS E{e}' in log
        else:
            assert f'REPLAY data mismatch V{e}' in log and 'FRONTIER_ROUTE_REPLAY PASS' not in log
        rejected_method_replays.append(dict(directory=str(wd),engine=e,
            valid_output_mismatch=e not in (0,1),energy_used=False,
            reason='Missing AMD-required timing simulation transport/pulse settings; repeated uniformly in a3.'))
        partial=P/'results'/f'replay_e{e}_a2'
        partial_log=(partial/'tool_3.log').read_text(errors='replace')
        assert 'REPLAY' in partial_log and 'mismatch' in partial_log and 'FRONTIER_ROUTE_REPLAY PASS' not in partial_log
        partial_options=run.read(partial/'tool_2.job.json')['argv']
        assert '-transport_int_delays' in partial_options and '-pulse_e' not in partial_options
        rejected_method_replays.append(dict(directory=str(partial),engine=e,
            valid_output_mismatch=True,energy_used=False,
            reason='Zero rejection but default pulse error limits produced unknowns; complete four-zero method repeated in a3.'))
    summary = dict(status='complete',experiment='Exact six-versus-eight residue capacity frontier',
        engine_names=NAMES,native_suites=native,hardware=hardware,power_audits=powers,
        supply2_control=supply,adaptive_comparisons=comparisons,failed_or_recovered_jobs=failures,
        job_memory_and_time=jobs,source_sha256=allpins,invalid_startup_replays=invalid_replays,
        rejected_timing_method_replays=rejected_method_replays,
        adaptive_policy='First six full U11/I8 lanes; admit seventh/eighth in order only when their actual U fits signed8. Fixed radix32 DSP layout and exact high recovery.',
        model_scope='Three seeds,144 saved images,32 timesteps,635904 updates; U operand is ceil(231*stored_membrane/256) computed in Python before addition; declared beta231 integer reference, no original-trained accuracy claim.',
        hardware_scope='Same Artix7,6ns,290FF registered OOC fixture; core counts exclude fixture; raw external port timing separate.',
        energy_scope='Whole-fixture vendor dynamic estimate from exact routed slow/max-SDF full native trace with AMD-required transport and zero pulse rejection; typical nominal rails,userTj25C; not core-only,board or full-neuron-update energy.',
        paper_readiness='This bounded trial measures a primitive tradeoff. Strong ISCAS contribution additionally requires a material matched-baseline benefit, closest-prior-art distinction and representative workload/range evidence.',
        audit_authorship='Independent agent reviewed RTL/native/fixture/supply control; root completed generic physical-activity/power audits after two agents reached usage limits.')
    run.write(targets[1],summary)
    lines = ['# Exact adaptive residue-capacity trial','',
        'All six engines preserve the same signed11 membrane plus signed8 current addition with exact signed12 output. In the saved model stream, the membrane operand is the post-leak value ceil(231*stored_membrane/256), computed in Python; this trial implements its subsequent current integration in RTL. The adaptive engine changes consumed capacity between six, seven and eight; it does not change numeric precision or discard bits.','',
        '## Matched routed results','',
        'Vivado2025.2; xc7a100tcsg324-1; 6ns; same183launch+107capture=290fixtureFF. Core resources exclude these FFs. Occupied slice counts are placement results and are not additive area weights.','']
    for e,hw in enumerate(hardware):
        r=hw['core']; m=models['rows'][e]
        p=powers.get(str(e))
        energy = f"; estimated dynamic {p['estimated_dynamic_energy_pJ_per_scalar_update']:.5f}pJ/update ({p['dynamic_power_W']*1000:.3f}mW over {p['native_interval_audit']['duration_ps']/1e6:.3f}us)" if p else '; energy unavailable because registered timing failed'
        lines.append(f"- E{e} {NAMES[e]}: **{r['LUT']}LUT / {r['FF']}FF / {r['DSP']}DSP**, registered WNS/WHS {hw['WNS_ns']:+.3f}/{hw['WHS_ns']:+.3f}ns; saved service {m['service_clocks']:,}clocks for {m['requests']:,}requests{energy}.")
    lines += ['', '## What the adaptation buys','']
    for c in comparisons:
        energy = f"; dynamic energy change {c['estimated_dynamic_energy_change_percent']:+.3f}%" if 'estimated_dynamic_energy_change_percent' in c else ''
        lines.append(f"- E5 versus E{c['baseline_engine']}: LUT/FF/DSP changes {c['LUT_change']:+d}/{c['FF_change']:+d}/{c['DSP_change']:+d}; saved service change {c['model_service_change_percent']:+.5f}%; stress service change {c['stress_service_change_percent']:+.3f}%{energy}.")
    lines += ['',
        'Comparing only with fixed6 would hide the stronger fixed8 alternatives. Accuracy is preserved by every baseline, so accuracy is not an adaptive advantage here. The fixed8 hybrid and LUT-only engines must also remain visible; DSP and LUT counts cannot be converted into one area number without a justified target-device resource constraint.','',
        '## Exactness and unfavorable work','',
        'Both ordinary and backpressured simulations cover all524288U11/I8 scalar pairs, structured mixed packed boundaries, arbitrary unused tails, reset cancellation and output/source holds. Python checks plain integer sums, ordering, zero tails and four advancing pipeline clocks. Saved635904 updates replay threshold/subtractive reset and match all saved states, spikes, output counts and classes. This is equivalence to the modified beta231 reference, not original trained-model accuracy.','',
        'For radix32, write U=32hU+rU and I=32hI+rI, with residues0..31. Each six-bit DSP field returns s=rU+rI<=62, preventing cross-lane carry. Reconstruct32(hU+hI+s[5])+s[4:0]. Full-range high results lie in[-36,35] and fit signed7; admitted narrow U8/I8 high results lie in[-8,7] and fit signed4. This identity supplies the general arithmetic argument beyond finite packed-vector coverage.','',
        'The saved models use three seeds and144 images, not several independent trained architectures. The full-domain stress workload is arithmetic coverage and an unfavorable range case, not a measured application spike burst. Issue and group-drained service counts are not complete-network or arrival-burst latency.','',
        '## Input delivery control','',
        'The eight-value raw-window fixture is a generous supply condition. With the same ordered model work and available capped at two values per cycle, all six actual RTL cores complete317952 requests in354816 clocks, with identical sums and saved states/spikes/classes. This validates the throughput dependence on input delivery; it does not implement or price a window buffer, SRAM porting or an external memory controller. Group drains add4 clocks for each of9216 groups in both controls. They preserve dependencies but also conservatively drain between independent images.','',
        '## Energy and timing evidence','',
        'Every timing-pass engine receives slow/max-SDF replay at6ns, with all native rows checked and no timing waivers. All accepted elaborations use AMD-required interconnect transport and zero pulse rejection settings, checked directly from job arguments. SAIF covers all useful service plus the same two fixture-settling clocks. Name-only normalization retains every numeric activity value and raw file. The audit verifies complete physical-net annotation, each simulated probability/rate, constrained clock aliases, primitive-proved constants, DSP enables and zero unknown time on physical activity. Simulator-only unknown aliases are retained and separately counted. Device static power is recorded separately. Energy is dynamic watts times actual interval divided by635904 updates; no fixture power is subtracted.','',
        'These are vendor estimates for the whole290FF fixture. Decimal export precision is not physical confidence. All designs use typical process, nominal rails and user junction25C; derived ambient can differ. The measured routes establish registered setup/hold, while raw-port budgets are separately archived and do not establish a board interface or board Fmax.','',
        '## Contribution boundary and paper decision','',
        'The specific mechanism is actual-membrane admission of two inexpensive narrow tail lanes beside six full-range lanes in one invariant DSP residue layout. It avoids layout switching and shared fallback correction. It remains adaptive DSP packing even though LUTs/registers recover high bits and control admission; their full costs belong in the comparison.','',
        'Exact guarded SNN additions are established by [DSP-Packing,SectionVII](https://arxiv.org/html/2203.11028#S7). External exact spill/high-part recovery is established in [Arithmetic Packing](https://arxiv.org/html/2606.11065) and related earlier work. The particular prefix rule has not been identified in our review; that is a qualified search result, not proof of first-ever novelty. Configuration uniqueness alone does not establish a strong paper.','',
        'A strong adaptive claim must be tied to the measured comparisons above and its unfavorable ranges/bandwidth conditions. This bounded primitive experiment does not establish general adaptive superiority, full SNN latency, memory efficiency or original-trained accuracy. Do not present it as a reproduced FireFly implementation: every measured baseline here was constructed for the same primitive and FPGA.','',
        '## Reproducibility','',
        'One initial workload-preparation assertion failed before simulation because the saved groups follow seed/timestep/layer/image order. Executed sources and logs were preserved; the corrected preparation copies the saved stream byte-for-byte. The bandwidth-control checker initially applied its two-value work cap to a nonvalid idle prelude window. Its failure is preserved; a separate repaired checker validates actual combinational take on idle rows and enforces the cap on every accepted useful row, reusing the unchanged simulation/trace. Any Synth20-411 checkpoint-export tool failure is retained together with recovery from the same verified synthesized checkpoint, without changing arithmetic or flow. No failed check is silently omitted.','',
        'The first E0 timing replay reports a startup setup violation at3ns, before GSR release/useful work, and is rejected for energy. A separately pinned testbench holds the clock low for6ns, moving its first edge from3ns to9ns while preserving the3mod6ns phase, every subsequent period and the entire useful trace/ROI. All accepted energy replays use this same initialization and must have no timing violations anywhere; timing checks are never disabled. The original failed replay and its activity remain preserved. An initial audit also failed because it selected all archived design.dcp names; its separate v2 replacement selects the exact exported top/hardware/DCP and rechecks unchanged evidence. The failed audit log/source are retained; no physical-activity acceptance rule is relaxed.','',
        'The first phase-corrected timing runs omitted standalone timing settings required by AMD UG900. Four fabric arithmetic engines reported valid-output mismatches; the other two completed. Every one of those activities and the preliminary E0 power estimate is excluded. A first transport correction left the pulse error limits at their default100 and failed all comparisons with unknowns; these attempts are also excluded. All six engines were replayed anew with interconnect transport, all four pulse error/rejection limits set to zero as in AMD support\'s standalone example, and explicit slow/max delays. No RTL, checkpoint, full trace, comparison, clock or activity interval changed. The v4 audit checks the complete option configuration. Sequential setup/hold checks and SDF delays stay enabled. This also makes previously archived energy comparisons using the omitted options preliminary; their values are not imported into this frontier result. '+link(P/'TIMING_SIMULATION_CORRECTION.md','Full correction record')+'.','',
        'Vivado export/implementation/power jobs run serially under RAM gates. Following the user request for speed and a measured approximately0.26GiB simulator process tree, two independent timing replays may overlap; the scheduling addendum and each separate job record document this. User applications are not closed. Tool-tree working-set sums can double-count shared pages and are sampled, not unique physical peaks. Two delegated agents reached usage limits; root completed their unfinished checks and does not claim a completed independent energy review.','',
        link(P/'CONTRACT.md','Contract')+'; '+link(P/'novelty_audit.md','Prior-art boundary')+'; '+link(targets[1],'Numeric summary')+'; '+link(targets[2],'SHA256 manifest')+'.','']
    targets[0].write_text('\n'.join(lines),encoding='utf-8')
    files = {Path(name) for name in allpins}
    files.update(x for x in P.iterdir() if x.is_file())
    for wd in (P/'results').iterdir():
        if wd.is_dir():
            files.update(x for x in wd.iterdir() if x.is_file())
            if (wd/'synth').is_dir(): files.update(x for x in (wd/'synth').iterdir() if x.is_file())
    files.update(targets[:2])
    add(run.pins(files))
    run.verify(run.frozen())
    run.write(targets[2],dict(status='pass',file_count=len(allpins),
        bytes=sum(Path(name).stat().st_size for name in allpins),files=allpins,
        scope='All scheduled successful frontier native/routes/replays/power/control evidence, preserved failed/recovered job logs and executed sources, referenced frozen evidence and publication; compiled vendor snapshots excluded.'))
    print(json.dumps(dict(status='published',report=str(targets[0]),files=len(allpins),comparisons=comparisons),indent=2),flush=True)


if __name__=='__main__':main()
