"""Final authored-doc polish, release hashes and mentor archive. Run after final edits."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'outputs/mentor_handoff/repository';OUT=D.parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
 return h.hexdigest()
for p in [D/'README.md',*list((D/'docs').glob('*.md'))]:
 text=p.read_text(encoding='utf-8')
 for a,b in [('fullsigned16','full signed16'),('zeroDSP','zero DSP'),('oneDSP','one DSP'),('all33','all 33'),('GLIF64','GLIF 64'),('codebeta','code beta')]:text=text.replace(a,b)
 text=re.sub(r'\b(all|full|at|versus|with|below|above|of|on|uses|unit|beta|and|is|the|common|matched|for|count|covers|supports)(?=\d)',r'\1 ',text)
 text=re.sub(r'(\d)(LUT|FF|DSP|pJ|ns|images|updates|image|bits)',r'\1 \2',text)
 text=text.replace('10000','10,000').replace('25C','25 C').replace('10,000-image','10,000-image')
 p.write_text(text,encoding='utf-8')
src=ROOT/'work/mentor_handoff_build';archive=D/'scripts/authoring_archive';archive.mkdir(parents=True,exist_ok=True)
for p in src.glob('*.py'):shutil.copyfile(p,archive/p.name)
shutil.copyfile(src/'slides/build_slides.mjs',archive/'build_slides.mjs')
historical=ROOT/'work/adaptive_snn_probe/validation_close/manuscript_snapshots/draft_e3bc0a6a_before_iscas.source_snapshot'
shutil.copyfile(historical,D/'research_reports/historical_manuscript_e3bc.source_snapshot')
(D/'scripts/authoring_archive/README.md').write_text('''# Handoff authoring sources

These scripts preserve how the repository, paper update and slides were authored. They are historical authoring tools with machine-specific Codex/runtime paths. Do not run them blindly: some require a completed local vendor pipeline and assert the old manuscript text before editing. Use the portable examples and `scripts/verify_release.py` for a fresh clone.

The slide builder uses the Codex-bundled `@oai/artifact-tool` runtime. This library is not redistributed. The delivered PPTX retains editable native objects for ordinary PowerPoint editing. New export revisions use fresh final filenames and validation receipts.
''')
slide=OUT/'mentor_briefing_v4.pptx'
if not slide.exists():slide=OUT/'mentor_briefing_v3.pptx'
if not slide.exists():slide=OUT/'mentor_briefing_v2.pptx'
assert slide.exists()
(D/'slides').mkdir(exist_ok=True)
shutil.copyfile(slide,D/'slides/mentor_briefing.pptx');shutil.copyfile(OUT/'slide-notes.md',D/'slides/slide-notes.md')
assert sha(slide)==sha(D/'slides/mentor_briefing.pptx')
original=json.loads((D/'release_manifest.json').read_text(encoding='utf-8')).get('preserved_original_files',{})
bindings={}
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 relative=p.relative_to(D)
 if any(x in {'.git','.build','__pycache__','node_modules'} for x in relative.parts) or relative.as_posix()=='release_manifest.json':continue
 bindings[relative.as_posix()]=dict(sha256=sha(p),bytes=p.stat().st_size)
manifest=dict(status='mentor_review_release',paper_source='paper/membrane_leakage_paper_draft.tex',slides='slides/mentor_briefing.pptx',files=bindings,preserved_original_files=original,
 historical_absolute_paths_are_provenance=True,large_external_assets_included=False,software_license_selected=False,
 scope='All research-authored sources and lightweight receipts, plus portable examples, current paper, editable slides and user-facing root conversation. No vendor binaries, weights, datasets or raw complete activity/checkpoints.')
(D/'release_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
zip_path=OUT/'mentor_handoff_release.zip';assert not zip_path.exists()
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
 for name in [*bindings,'release_manifest.json']:z.write(D/name,'membrane-leakage-packing/'+name)
print(json.dumps(dict(status='release_frozen',files=len(bindings),source_archive_files=len(original),paper_sha256=sha(D/'paper/membrane_leakage_paper_draft.tex'),slides_sha256=sha(slide),zip_bytes=zip_path.stat().st_size),indent=2))
