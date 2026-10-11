"""Additive bounded primary-route access review; never treats access failure as non-equivalence."""
import datetime, hashlib, json, pathlib

P=pathlib.Path(__file__).resolve().parent
PA=P.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(name):
    r=json.loads((P/(name+'.access.json')).read_text(encoding='utf-8'))
    if 'response_path' in r:
        assert pathlib.Path(r['response_path']).resolve()==(P/(name+'.response')).resolve()
        assert sha(P/(name+'.response'))==r['sha256']
    return r
def text(name):return (P/(name+'.extracted.txt')).read_text(encoding='utf-8')

assert 'Full-text (Intranet only)' in text('ou_um_thesis_detail')
assert 'Study and design of the FPGA-based neural network CoDesign' in text('ou_um_thesis_detail')
assert 'Ou, Yao Zhong,' in text('ou_um_thesis_detail') and 'Zhu Yan' in text('ou_um_thesis_detail')
assert 'Efficient DSP Packing Method for Neural Network Accelerator.' in text('cui_fpt_program')
assert '崔泽楠' in text('cui_seu_team') and '张经纬' in text('cui_seu_team')
assert '前16页' in text('cui_seu_thesis_policy') and '统一身份认证' in text('cui_seu_thesis_policy')
assert 'ir.seu.edu.cn' in rec('cui_seu_ir_notice')['links'][0] or any('ir.seu.edu.cn' in u for u in rec('cui_seu_ir_notice')['links'])
orcid_ou=json.loads((P/'ou_orcid_target_work.response').read_text(encoding='utf-8'))
assert orcid_ou['url']['value']=='https://doi.org/10.1109/TCSII.2024.3377356'
orcid_meng=json.loads((P/'cui_meng_orcid_person.response').read_text(encoding='utf-8'))
assert 'Contaminated sites' in [x['content'] for x in orcid_meng['keywords']['keyword']]

access=[rec(p.name.removesuffix('.access.json')) for p in sorted(P.glob('*.access.json')) if p.name.startswith(('ou_','cui_'))]
pins={str(p.resolve()):sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name.startswith(('ou_','cui_')) and p.suffix not in ('.md',) and 'access_equivalence_report_v1.json' not in p.name}
old_inputs=['final_contribution_boundary.md','targeted_followup/targeted_equivalence_followup.md','targeted_followup/access_checks.json','bounded_final_access_20261011/access_closure.json','bounded_final_access_20261011/access_closure.md','openalex_10.1109_TCSII.2024.3377356.json','openalex_10.1109_ICFPT64416.2024.11113473.json']
old_pins={str((PA/s).resolve()):sha(PA/s) for s in old_inputs}
questions=[
    {'question':'Does current operand value determine pair/lane admission at issue, rather than only configured quantization or layer precision?','status':'unresolved; full method unread'},
    {'question':'Is out-of-range work routed to an exact full-width operation under the same stored integer representation?','status':'unresolved; full method unread'},
    {'question':'Does its signed unpacking reproduce shared-beta ceil(beta*U/256) with equivalent overlap-borrow and narrow quotient correction?','status':'unresolved; full method unread'},
]
papers=[
    {
      'key':'Ou2024','doi':'10.1109/TCSII.2024.3377356','publisher_url':'https://ieeexplore.ieee.org/document/10472602',
      'title':'A 119.64 GOPs/W FPGA-Based ResNet50 Mixed-Precision Accelerator Using the Dynamic DSP Packing',
      'full_method_retrieved':False,'method_equivalence_status':'unresolved_due_to_full_method_access','method_section_equation_evidence':[],
      'new_primary_routes':['ou_um_author','ou_um_group_report','ou_orcid_works','ou_orcid_target_work','ou_um_theses','ou_um_theses_author','ou_um_theses_microelectronics','ou_um_theses_author_o','ou_um_theses_author_o_p2','ou_um_theses_author_o_p3','ou_um_theses_author_chinese','ou_um_theses_author_chinese_p2','ou_um_thesis_author_target','ou_um_thesis_detail'],
      'fresh_evidence':'The official catalogue identifies a 2024 thesis by Ou, Yao Zhong, supervised by Zhu Yan. The detail explicitly labels its full text Intranet only. This is a candidate source, not a verified copy of the target journal method.',
      'thesis_record_url':rec('ou_um_thesis_detail')['url'],'thesis_title':'Study and design of the FPGA-based neural network CoDesign','thesis_access':'Intranet only; restricted download not followed',
      'orcid_work_result':'Target work detail links only the journal DOI; no author manuscript or repository URL.',
      'remaining_questions':questions,
      'legitimate_next_access':'Obtain the complete 2554–2558 journal pages using the user/lab IEEE licence or a legitimately supplied author manuscript. Alternatively obtain the identified 2024 thesis through authorised UM access and verify whether it contains this paper.',
      'needed_method_passages':'DDP packing-selector control, numerical contract and precision-selection timing, FPC signed unpacking/calibration equations, supported operand bounds, and any exceptional/full-width path. Section/equation numbers cannot be named without the full method.',
    },
    {
      'key':'Cui2024','doi':'10.1109/ICFPT64416.2024.11113473','publisher_url':'https://ieeexplore.ieee.org/document/11113473',
      'title':'Efficient DSP Packing Method for Neural Network Accelerator',
      'full_method_retrieved':False,'method_equivalence_status':'unresolved_due_to_full_method_access','method_section_equation_evidence':[],
      'new_primary_routes':['cui_seu_team','cui_fpt_program','cui_fpt_home','cui_seu_meng_profile','cui_seu_library_ir','cui_seu_library_theses_notice','cui_seu_thesis_policy','cui_seu_ir_notice','cui_seu_ir_portal'],
      'fresh_evidence':'The official FPT program lists the exact short-paper title and authors but contains no target paper/slides/supplement link. Official SEU news identifies Cui Zenan and Zhang Jingwei in its FPGA team. The linked SEU repository hostname failed DNS; the thesis policy offers only the first16 pages to guests, full browsing after institutional authentication, and library-mediated full downloads. No candidate Cui thesis record or full target method was retrieved.',
      'institutional_access_policy_url':rec('cui_seu_thesis_policy')['url'],'institutional_repository_url':'https://ir.seu.edu.cn/',
      'identity_quality_note':'The retained OpenAlex Meng Zhang ORCID0000-0001-5630-321X returned an environment/soil-remediation profile and no DSP packing work. That inferred author-ID match is not admitted as verified identity or method evidence. Likewise secondary inferred Cui ORCID was not accepted as proof of identity.',
      'remaining_questions':questions,
      'legitimate_next_access':'Obtain the complete four-page ICFPT paper through the user/lab IEEE licence or a legitimately supplied author manuscript. SEU thesis access is only an alternative candidate search and is not evidence that a thesis contains this paper.',
      'needed_method_passages':'Packing operand widths and mappings, signed correction/overlap equations, exactness conditions, any runtime lane-count selector and overflow/full-width fallback. Section/equation numbers cannot be named without the full method.',
    },
]
report={
 'status':'completed_fresh_primary_route_check_two_full_method_gaps_unresolved',
 'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'ONLY Ou2024 TCASII and Cui2024 ICFPT; source/access check, no hardware, model or manuscript changes',
 'full_methods_newly_retrieved':0,'closed_paper_equivalence_gaps':0,'remaining_assigned_gaps':['Ou2024','Cui2024'],
 'candidate_contract':{'stored_membrane':'signed16, unchanged unit1/256','coefficient':'unsigned Q8 beta0..256','result':'ceil(beta*U/256)','pair_admission':'two available consecutive signed9 membranes[-256,255] and equalbeta','fallback':'exact signed16 singleton; no quantization/rescaling','decoder':'stride16 shared-beta overlap; one exact borrow bit and rounded quotient correction'},
 'papers':papers,'access_receipts':access,'new_source_pins':pins,'retained_input_pins':old_pins,
 'scientific_interpretation':'These fresh primary routes improve source identification and legitimate access instructions. They supply no unread selector, fallback or decoder facts and do not establish either equivalence or non-equivalence. Application/name differences cannot establish arithmetic novelty; no first-ever or absence claim is permitted.',
 'scope_limits':'This report does not review UDP or McKeown. Parent owns their closure. Previous publisher access failures remain historical; they were not repeated as new progress.',
 'access_safety':'Public GETs and primary web searches only. No author messages, login attempts, CAPTCHA bypass, restricted download, vendor launches, inference, process control or draft edits.',
}
j=P/'ou_cui_access_equivalence_report_v1.json';m=P/'ou_cui_access_equivalence_report_v1.md'
assert not j.exists() and not m.exists(),'Additive record must not overwrite an existing report'
j.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
md='''# Ou/Cui fresh primary-route closure attempt

Prepared 11 October 2026. **Neither assigned full-method gap is closed.** Fresh author, institutional thesis and conference routes were followed; previous publisher failures were not repeated as progress. Every saved response has an explicit URL, retrieval outcome and SHA256 in the JSON record. No hardware/model/draft changes were made.

Ou now has a precise alternative source: the [official 2024 thesis record](https://libdigital.um.edu.mo/um-theses/show/991010450375306306?from=author), *Study and design of the FPGA-based neural network CoDesign*, by Ou, Yao Zhong, supervised by Zhu Yan. The public catalogue marks Full Text, but its detail explicitly says **Full-text (Intranet only)**. That restricted download was not followed. The matching name, year and supervisor make this a candidate source; its contents have not been verified against the target journal paper. The [public ORCID work detail](https://pub.orcid.org/v3.0/0009-0001-8228-622X/work/159546236) links only the DOI.

For Cui, the [official FPT2024 program](https://fpt2024.org/draft-program/) confirms the exact short paper and author list, but its saved links contain no target manuscript, slides or supplement. [Official SEU team news](https://news.seu.edu.cn/2023/0718/c5495a455422/page.htm) establishes the institutional route and Chinese author names. The [official thesis policy](https://lib.seu.edu.cn/bencandy.php?fid=250&id=1464) permits guest browsing of the first16 pages, full browsing after institution authentication, and library-mediated full downloads. The [official IR notice](https://lib.seu.edu.cn/list.php?fid=44) links ir.seu.edu.cn; that hostname failed DNS in this attempt. No candidate Cui thesis or full paper was retrieved. The inferred Meng Zhang ORCID in the retained aggregate metadata instead shows soil-remediation keywords, so that identity was not treated as verified.

The necessary legitimate next inputs are the complete [Ou journal paper](https://ieeexplore.ieee.org/document/10472602), pages2554–2558, and [Cui ICFPT paper](https://ieeexplore.ieee.org/document/11113473), all four pages, obtained through the user/lab IEEE licence or a legitimately supplied author manuscript. Author messages were not sent. The identified Macau thesis could alternatively be checked through authorised UM access.

The method questions remain: does an actual current operand select lane count at issue; is there an exact full-width fallback under unchanged stored integer units; and do the signed overlap/rounding equations reproduce shared-beta ceil(beta*U/256) with E5-equivalent borrow and narrow quotient correction? For Ou, the specific missing passages are DDP selection and FPC calibration/unpacking. For Cui, they are packing mappings, correction algebra, exactness bounds and any runtime/full-width control. Section/equation numbers are deliberately absent because the full methods were unread.

**Conclusion:** this effort produced better access routes and provenance, not evidence of novelty or non-equivalence. Keep the focused leakage claim conditional on the unresolved original methods; do not use first-ever, no-equivalent-work or fully-closed-equivalence wording. UDP and McKeown are outside this two-paper report and remain parent-owned.
'''
m.write_text(md,encoding='utf-8')
print(json.dumps({'status':report['status'],'new_source_pins':len(pins),'access_receipts':len(access),'json':str(j),'markdown':str(m)}))
