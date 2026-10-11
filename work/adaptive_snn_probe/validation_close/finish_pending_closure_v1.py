"""Freeze this continuation's bounded conclusion without replacing earlier evidence."""
from pathlib import Path
import datetime, hashlib, json, sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
OUT=ROOT/'outputs'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def write_new(path,data):
    with Path(path).open('xb') as stream:stream.write(data)

def main():
    audit_file=P/'manuscript_scope_audit_v4.json'
    audit=json.loads(audit_file.read_text(encoding='utf-8'))
    assert audit['status']=='pass_final_manuscript_scope_audit_with_explicit_failed_controls_and_limits'
    assert not audit['material_factual_or_numerical_errors_found']
    draft=ROOT/'outputs/membrane_leakage_paper_draft.tex'
    assert sha(draft)==audit['audited_draft_sha256']
    assert audit['primary_comparison_gate']['accepted']==12
    assert not audit['primary_comparison_gate']['all14_energy_accepted']
    assert audit['fresh_closure']['UDP_method_inspected']
    assert not audit['fresh_closure']['original_LUT_precise_cause_resolved']
    names=['membrane_leakage_pending_closure_20261011.md','membrane_leakage_pending_closure_20261011.json']
    assert all(not (OUT/name).exists() for name in names)
    pins={str(audit_file.resolve()):sha(audit_file),str(draft.resolve()):sha(draft),
        str(Path(__file__).resolve()):sha(__file__)}
    result=dict(status='bounded_checks_completed_three_original_methods_and_precise_simulator_cause_unresolved',
        generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        draft=str(draft.resolve()),draft_sha256=sha(draft),
        built_in_latex_compilation='success observed after the last source edit; source unchanged since compilation',
        independent_prior_work_wording_review='pass; configuration/runtime correction distinction, citations and three original gaps checked; not a second reading of browser full text',
        fresh_closure=audit['fresh_closure'],
        original_E2_full_replay_and_energy_accepted=False,
        accepted_comparison_count=12,attempted_original_comparison_count=14,
        model_reexecution_this_continuation=False,
        accepted_model_evidence_preserved=['GLIF ResNet18 CIFAR10 full10000 scalar integer plus64-image packed feedback',
            'OTTT VGG11 CIFAR10 full10000 actual packed feedback',
            'BNTT VGG11 TinyImageNet thirty-step held-out64-image packed feedback'],
        paper_position='Exact adaptive membrane-leakage primitive and measured resource/rate/estimated-energy trade-offs at fixed signed16 precision.',
        first_ever_established=False,strong_ISCAS_readiness_established=False,
        unresolved_inputs=['Legitimate original Ou2024, Cui2024 and McKeown2008 full methods.',
            'Simulator pending-event/cancellation provenance or equivalent authoritative resolution for the retained timed CARRY4 discrepancy.'],
        further_strong_baseline_limit='GLIF two-constant-per-channel CSD/bank hardware is unmeasured; this limits model-specific superiority.',
        evidence_sha256=dict(sorted(pins.items())))
    prose='''# Continuation conclusion: exact adaptive membrane leakage

The existing paper draft was updated in place and compiled successfully. This continuation preserves all accepted routes, model results and energy evidence. The new scope audit passes without material numerical or factual errors.

**LUT discrepancy: localized, not fully repaired.** The signed16 OTTT observation-only replay reproduces its +16384 error. A timed CARRY4 output remains inconsistent with its settled Boolean inputs; that wrong bit reaches D14 and is captured into Q14. The signed12 connected-carry-input suppression removes row914 but later fails at2836; disabling optimization does not fix914. Changing only pulse error limits produces early unknowns. These diagnostics identify the failing simulation location and path, but do not expose exact pending-event/cancellation behavior or establish a physical FPGA defect. No original E2 energy is accepted. The independent exact E7 fabric control remains accepted.

**Prior work: one of four full-method gaps closed.** UDP's complete twelve-page rendered paper was inspected. Its configured widths/template parallelism and runtime sign/most-negative corrections are distinct from our actual-membrane admission policy; exact signed packing and high/low fusion remain substantial ancestry. No matching leakage/admission conjunction was described in that inspected method. No original PDF checksum is claimed. Ou, Cui and McKeown remain unread originals: normal publisher pages explicitly deny PDF access, and legal author/institution routes did not supply manuscripts. The Macau thesis candidate is intranet-only. Abstracts and UDP's description of Cui cannot close these gaps.

**Paper position.** The contribution remains exact signed16 membrane leakage with actual signed9 pair admission and full-width singleton fallback, implemented in62LUT/44FF/oneDSP. Accepted GLIF results give46.0091% fewer issues and12.3695% lower estimated representative fixture dynamic energy than one-DSP scalar execution, at49 extra LUTs and15 extra FFs; against fixed full-domain split packing, energy falls60.9472% with1.0821% more captured issues. The two-DSP scalar pair remains a near-energy-parity competing point. Vanilla-LIF half-leakage shifting beats adaptation by a wide margin. These are measured primitive trade-offs, not universal model/accelerator benefits, board energy or packing accuracy improvements.

The public GLIF, OTTT and thirty-step BNTT validations remain accepted with their original full-test/subset scopes. They were not unnecessarily rerun in this continuation. A model-specialized GLIF two-constant/CSD bank remains unmeasured.

**Decision:** continue writing a focused exact adaptive leakage primitive paper using the accepted comparisons and explicit negative cases. First-ever novelty and strong ISCAS readiness are still unproved. Closing the three original-method gaps requires authorized original PDFs or legitimate author manuscripts; further public abstract searches cannot answer their mechanism questions. The precise simulator cause remains a separate retained diagnostic limit, with failed E2 energy excluded.
'''
    prose+=f'\nCurrent manuscript SHA256: `{sha(draft)}`. Additive audit: `manuscript_scope_audit_v4.json`, binding {audit["checked_evidence_hash_count"]} evidence hashes. Earlier reports and audits remain immutable historical snapshots.\n'
    write_new(OUT/names[0],prose.encode('utf-8'))
    write_new(OUT/names[1],(json.dumps(result,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(status=result['status'],report=str((OUT/names[0]).resolve()),draft_sha256=sha(draft))))

if __name__=='__main__':main()
