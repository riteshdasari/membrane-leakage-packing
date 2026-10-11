"""Prepare an additive scope audit from the preserved v3 auditor; no job reruns."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
source = (P / 'audit_manuscript_scope_v3.py').read_text(encoding='utf-8')
target = P / 'audit_manuscript_scope_v4.py'
assert not target.exists()

def replace(old, new, count=1):
    global source
    assert source.count(old) == count, (old, source.count(old))
    source = source.replace(old, new)

replace("out=P/'manuscript_scope_audit_v3.json';md=P/'manuscript_scope_audit_v3.md'", "out=P/'manuscript_scope_audit_v4.json';md=P/'manuscript_scope_audit_v4.md'")
replace("    assert len(access['papers'])==4 and all(not x['full_method_retrieved'] for x in access['papers'])", """    # Earlier access receipt remains immutable historical evidence.
    assert len(access['papers'])==4 and all(not x['full_method_retrieved'] for x in access['papers'])
    A=P/'prior_art/pending_closure_20261011'
    D=P/'lut_isolation/pending_closure_20261011'
    udp=evidence.read(A/'udp_full_reader_inspection_v1.json',{'completed_full_rendered_primary_method_inspection'})
    normal=evidence.read(A/'normal_publisher_access_receipt_v1.json',{'normal_browser_publisher_access_checked_three_methods_still_unread'})
    ou_cui=evidence.read(A/'ou_cui_access_equivalence_report_v1.json',{'completed_fresh_primary_route_check_two_full_method_gaps_unresolved'})
    mc=evidence.read(A/'udp_mckeown_closure_v1.json',{'bounded_new_primary_routes_complete_original_full_method_still_unresolved'})
    diag=evidence.read(D/'pending_closure_independent_audit_v2.json',{'audited_pending_LUT_closure_signed16_cell_output_inconsistency'})
    diag12=evidence.read(D/'signed12_controls_independent_audit_v1.json')
    probe=evidence.read(D/'run_signed16_probe/a0/diagnostic.json',{'completed_observation_only_signed16_probe'})
    assert udp['full_method_retrieved'] and not udp['original_pdf_file_acquired']
    assert len(udp['rendered_page_characters'])==12 and all(n>2000 for n in udp['rendered_page_characters'])
    assert udp['configured_widths_distinct_from_runtime_correction'] and not udp['equivalent_actual_membrane_admission_described']
    assert not udp['first_ever_established'] and not udp['Cui_original_method_closed_by_secondary_description']
    remaining=[r['id'] for r in normal['papers']]
    assert set(remaining)=={'Ou2024','Cui2024','McKeown2008'} and all(not r['full_method_retrieved'] for r in normal['papers'])
    assert not normal['login_attempted'] and not normal['access_controls_bypassed']
    assert len(ou_cui['papers'])==2 and all(not r['full_method_retrieved'] for r in ou_cui['papers'])
    assert not mc['original_full_method_retrieved']
    assert all(probe['gates'].values()) and probe['original_failure_reproduced']
    assert not probe['cause_established'] and not probe['full_trace_energy_acceptance']
    settled=[]
    for line in probe['snapshots']:
        m=re.search(r'AGE([0-9.]+) S0 DI0 CI0 CY0 SI0 DII0 CII0 CYI0 CO0 FB0 O2 PARENT_O2 UPSTREAM_CI0 EXPECT_O0 EXPECT_CO0',line)
        if m:settled.append(float(m.group(1)))
    assert settled and max(settled)>19
    assert diag['error_limit_control']['first_failure_row']==5 and not diag['error_limit_control']['accepted_as_remedy']
    assert diag['signed16']['original_first_failure_reproduced'] and diag['signed16']['all_observation_gates_pass']
    for needle in ['Disabling simulator optimization also retains row 914', 'replay fails later at row 2836',
        'forcing can affect connected nets', 'more than 19 ns of stable inputs',
        'Full methods for three relevant originals remain unread', 'runtime sign and most-negative-value corrections']:
        where(needle)
    assert 'Full methods for four relevant papers remain access-limited' not in text
    evidence.bind(A/'udp_full_reader_inspection_v1.md')
    evidence.bind(A/'ou_cui_access_equivalence_report_v1.md')
    evidence.bind(A/'udp_mckeown_closure_v1.md')
    evidence.bind(D/'pending_closure_independent_audit_v2.md')
    evidence.bind(D/'signed12_controls_independent_audit_v1.md')
    evidence.bind(P/'prepare_manuscript_scope_v4.py')""")
replace('four unavailable full methods', 'three unavailable full methods')
replace("full_method_access_gaps=[r['id'] for r in access['papers']]", "full_method_access_gaps=remaining,UDP_complete_method_inspected=True,UDP_original_PDF_acquired=False")
replace("        required_caveats=", "        fresh_closure=dict(UDP_method_inspected=True,remaining_originals=remaining,signed16_settled_wrong_max_age_ns=max(settled),original_LUT_precise_cause_resolved=False,original_LUT_energy_accepted=False),\n        required_caveats=")
replace('Four full methods remain inaccessible;', 'Three original full methods remain unread; UDP complete rendered methods were inspected;')
target.write_text(source, encoding='utf-8', newline='\n')
print(target)
