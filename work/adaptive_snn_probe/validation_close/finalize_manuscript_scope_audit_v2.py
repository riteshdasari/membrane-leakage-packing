"""Correct one first-pass finding after recognizing root's included paragraph.

Retain the first-pass records byte-for-byte. No evidence, manuscript or source
is changed; only the newly authored review's presentation of an already closed
scope clarification is corrected before delivery.
"""
from pathlib import Path
import hashlib
import json

P=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source=P/'manuscript_scope_audit_v2.json';md=P/'manuscript_scope_audit_v2.md'
    saved_json=P/'manuscript_scope_audit_v2_first_pass.json'
    saved_md=P/'manuscript_scope_audit_v2_first_pass.md'
    assert not saved_json.exists() and not saved_md.exists()
    record=json.loads(source.read_text())
    draft=Path(record['draft_file'])
    assert sha(draft)==record['audited_draft_sha256']
    text=draft.read_text()
    marker='The counted RTL computes both signed-range tests and coefficient equality'
    paragraph,=[line for line in text.splitlines() if line.startswith(marker)]
    assert 'source queues, operand memory and variable-consumption integration are not included' in paragraph
    saved_json.write_bytes(source.read_bytes());saved_md.write_bytes(md.read_bytes())
    finding,=[f for f in record['findings'] if f['id']=='source_queue_boundary']
    finding['severity']='material_boundary_already_disclosed'
    finding['lines']=[i for i,line in enumerate(text.splitlines(),1) if line==paragraph]
    finding['issue']='The measured primitive computes admission internally; the current paragraph explicitly states that upstream two-operand presentation, consume-count advancement, re-presentation, source queues and frame/window boundaries are external and excluded. The critical attribution boundary is correctly disclosed.'
    finding['action']='Preserve this paragraph in the final submission and retain all exclusions in area/energy claims.'
    finding.pop('suggested_text',None)
    record['conditional_paper_verdict']=record['conditional_paper_verdict'].replace(
       'explicitly preserve the constant-bank applicability gap and external source-queue boundary',
       'preserve the already disclosed constant-bank applicability gap and external source-queue boundary')
    record['first_pass_presentation_correction']=dict(
       reason='The initial finding requested a queue-boundary clarification, but the exact audited draft already includes root\'s explicit paragraph. Its classification is corrected to an already-disclosed material boundary; numerical evidence and manuscript bytes are unchanged.',
       first_pass_json_file=str(saved_json.resolve()),first_pass_json_sha256=sha(saved_json),
       first_pass_md_file=str(saved_md.resolve()),first_pass_md_sha256=sha(saved_md),
       finalizer_file=str(Path(__file__).resolve()),finalizer_sha256=sha(__file__))
    prose=saved_md.read_text(encoding='utf-8').replace(
       'State this boundary explicitly near the interface contract.',
       'The audited draft already states this boundary explicitly in its new paragraph at line37; preserve it.')
    source.write_text(json.dumps(record,indent=2)+'\n');md.write_text(prose,encoding='utf-8')
    print(json.dumps(dict(status=record['status'],audited_draft_sha256=record['audited_draft_sha256'],
       source_queue_boundary_correctly_disclosed=True,checked_evidence_hash_count=record['checked_evidence_hash_count'],
       first_pass_retained=True,manuscript_edited=False),indent=2))


if __name__=='__main__':main()
