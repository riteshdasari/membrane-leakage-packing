from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'release_manifest.json').read_text());errors=[]
for name,info in d['files'].items():
    p=ROOT/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=info['sha256']:errors.append(name)
if errors:raise SystemExit('Changed/missing release files: '+repr(errors))
print(f"PASS {len(d['files'])} published file hashes; historical receipts retain their original scope")
