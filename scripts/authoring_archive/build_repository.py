"""Create a reviewed public handoff, preserving local evidence unchanged."""
from pathlib import Path
import collections,datetime,hashlib,html,json,os,re,shutil
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'outputs/mentor_handoff/repository'
DEST.mkdir(parents=True,exist_ok=True)
W=ROOT/'work/adaptive_snn_probe/validation_close/width16'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,text):
 p=DEST/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
manifest={};omitted=[]
def copy(p,relative):
 target=DEST/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 assert sha(p)==sha(target);manifest[str(relative).replace('\\','/')]=dict(bytes=p.stat().st_size,sha256=sha(target),original=str(p.relative_to(ROOT)).replace('\\','/'))

# Research-authored sources: preserve directory relationships, not vendor/generated netlists.
exclude={'hardware','.Xil','.git','__pycache__','deps','assets','sources','ottt_source','bntt_visual_source','iir_source','iir_archive','mnist_public','xsim.dir','tmp','node_modules'}
codeext={'.py','.sv','.tcl','.ps1','.mjs','.sh','.md'}
for folder,dirs,files in os.walk(ROOT/'work/adaptive_snn_probe'):
 dirs[:]=[d for d in dirs if d not in exclude]
 for name in files:
  p=Path(folder)/name
  if p.suffix.lower() in codeext:
   copy(p,p.relative_to(ROOT))
# Human-readable result receipts. Large DCP/SAIF/model/image assets stay out of Git.
for folder,dirs,files in os.walk(ROOT/'work/adaptive_snn_probe'):
 dirs[:]=[d for d in dirs if d not in exclude-{'hardware'}]
 for name in files:
  p=Path(folder)/name
  if p.suffix=='.json' and p.stat().st_size<8*2**20:
   copy(p,p.relative_to(ROOT))
for name in ('leak_core16.sv','leak_dsp.sv','timing16.sv'):
 copy(W/name,Path('rtl')/name)
for p in (W/'lutceil_e7').glob('*.sv'):copy(p,Path('rtl/lut_control')/p.name)
for p in (W/'constant_glif_readiness').glob('*.sv'):copy(p,Path('rtl/glif_constant_control')/p.name)
for p in (ROOT/'outputs').glob('*.md'):copy(p,Path('research_reports')/p.name)
for p in (ROOT/'outputs').glob('*.json'):
 if p.stat().st_size<8*2**20:copy(p,Path('research_reports')/p.name)
copy(ROOT/'outputs/membrane_leakage_paper_draft.tex',Path('paper/membrane_leakage_paper_draft.tex'))
# Representative integer operands are compact research-generated assets, not images or weights.
for name in ('actual_glif_expected.npz','actual_glif_input.txt'):
 p=W/name
 if p.exists() and p.stat().st_size<25*2**20:copy(p,Path('captures')/name)

share='https://chatgpt.com/s/cx_6acb1c46e7688191b3cd0aa437cddd1c'
thread='01a11a12-e81a-7153-962a-08ee9cb1c78b'
sessions=[p for p in Path('C:/Users/Ritesh/.codex/sessions').rglob('*.jsonl') if thread in p.name]
messages=[];seen=set();session_pins={}
for p in sorted(sessions):
 session_pins[p.name]=sha(p)
 for line in p.open(encoding='utf-8'):
  d=json.loads(line);x=d.get('payload',{})
  if d.get('type')!='response_item' or x.get('type')!='message':continue
  role=x.get('role');phase=x.get('phase',x.get('channel'))
  if role not in ('user','assistant') or (role=='assistant' and phase not in ('commentary','final')):continue
  text='\n'.join(c.get('text','') for c in x.get('content',[]) if c.get('type') in ('input_text','output_text'))
  if not text.strip():continue
  if role=='user' and text.lstrip().startswith(('<environment_context>','<external_codex_apps_open_page>')):continue
  key=x.get('id') or (d.get('timestamp'),role,text)
  if key in seen:continue
  seen.add(key);messages.append(dict(timestamp=d.get('timestamp',''),role=role,phase=phase,text=text))
messages.sort(key=lambda v:v['timestamp'])
header=f'''# Conversation export

This exports the user-facing text of the local root conversation through {datetime.datetime.now(datetime.timezone.utc).isoformat()}.
It contains user messages and assistant commentary/final replies. Tool logs, hidden reasoning, system/developer instructions and subagent internals are excluded. Earlier statements describe intermediate experiments and may be superseded. The current paper and results index govern final claims.

Public immutable chat snapshot: {share}

'''
markdown=header+'\n\n'.join(f"## {i+1}. {m['role'].title()} · {m['timestamp']}\n\n{m['text']}" for i,m in enumerate(messages))
write('chat/conversation.md',markdown)
write('chat/conversation.html','<!doctype html><meta charset="utf-8"><title>Membrane leakage research conversation</title><style>body{max-width:1000px;margin:40px auto;padding:0 24px;font:17px/1.55 system-ui;color:#172638}pre{white-space:pre-wrap;overflow-wrap:anywhere}h2{border-top:1px solid #ddd;padding-top:24px}</style><h1>Research conversation</h1><p>Historical intermediate claims can be superseded. Read the current paper and results index first.</p>'+''.join(f'<h2>{i+1}. {m["role"].title()} · {html.escape(m["timestamp"])}</h2><pre>{html.escape(m["text"])}</pre>' for i,m in enumerate(messages)))
write('chat/export_receipt.json',json.dumps(dict(status='exported_user_facing_conversation',messages=len(messages),by_role=dict(collections.Counter(m['role'] for m in messages)),source_sessions=session_pins,excluded=['tool outputs','reasoning','system/developer text','subagent messages','automatically injected environment/page-only user records'],share_snapshot=share),indent=2))
write('.gitignore','__pycache__/\n*.pyc\n.build/\n.venv/\nnode_modules/\n*.dcp\n*.saif\n*.pth\n*.pth.tar\n*.pt\n*.zip\n.Xil/\nxsim.dir/\n')
write('NOTICE.md','''# Source and release notice

This repository publishes the research code and manuscript for mentor review. No software license grant has yet been selected by the authors. Public availability does not change third-party licenses. The authors should choose a release license before inviting reuse beyond the normal GitHub viewing/forking permissions.

Downloaded model repositories, weights, datasets, vendor libraries, raw third-party papers and the GitHub CLI executable are not redistributed. The source records identify their original repositories, commits and asset hashes. Fetch them from their owners and retain their licenses.

OpenAI Codex assisted with prototyping, validation tooling, evidence analysis and document/slides preparation. X is the requested temporary author placeholder. This is a research draft, not an accepted publication.
''')
write('docs/START_HERE.md','''# Mentor reading guide

1. Read the README for the operation, adaptation rule and measured trade-offs.
2. Open the slide deck in `slides/`. Its speaker notes include explanations and evidence pointers.
3. Run `python examples/run_examples.py` to see the integer arithmetic, including a negative borrow and exact wide fallback.
4. Read `docs/MECHANISM.md` for the decoder derivation and interface obligations.
5. Review `paper/membrane_leakage_paper_draft.tex`, `docs/RESULTS.md` and the explicit limitations.
6. Use `docs/REPRODUCIBILITY.md` for portable checks and the preserved research archive.
7. Read `chat/conversation.html` locally, or use the shared chat link. It records the exploration, including failed candidates, rather than only the final conclusion.

The contribution concerns membrane **leakage multiplication**. Synaptic accumulation, complete neuron scheduling and a complete accelerator are outside measured core scope.
''')
write('docs/MECHANISM.md','''# Exact arithmetic and runtime admission

The primitive computes `L(U,beta) = ceil(beta*U/256)` for signed16 U and integer beta from 0 through 256. Quantizing a floating neuron into this contract is a separate conversion step. Exact packing preserves this integer contract.

The stored membrane always remains signed16. The core inspects two available consecutive operands. It pairs them only when both actual values fit signed9 `[-256,255]` and beta values match. Otherwise it consumes only the first operand and computes it with full signed16 precision. The source must advance by `take` after an accepted request and present the unconsumed operand again. Pairing cannot cross a declared frame boundary. Valid/ready stalls preserve order and hold outputs.

## Packed calculation

For admitted `(u0,u1,beta)`:

```
A = (u0 + 256) + (u1 << 16)
C = 255 - 256*beta + (255 << 16)
P = A*beta + C = x + (y << 16)
x = beta*u0 + 255
y = beta*u1 + 255
```

A fits the DSP48E1 signed25 multiplicand port. `-65536 < x < 65536`, so the lower field can cause at most one negative borrow. Let `n = 1 if x < 0 else 0`. The upper portion equals `T = floor(P/65536) = y-n`. The known parity of y gives an inexpensive reference bit:

```
r = ((beta & 1) & (u1 & 1)) XOR 1
n = bit16(P) XOR r
L0 = unsigned(P[15:8]) - 256*n
L1 = signed9(P[32:24]) + (n AND P[23:16] == 255)
```

The upper quotient needs correction only when adding back the borrow crosses a byte boundary. Both outputs sign extend to signed16. No mantissa, exponent, rescaling, saturation or discarded spill appears in this mechanism.

## Worked negative-borrow example

For `u0=-3`, `u1=5`, `beta=128`, the independent results are `ceil(-384/256)=-1` and `ceil(640/256)=3`. Here `x=-129`, `y=895`, so n=1. The unsigned lower quotient byte is 255. Restoring the borrow gives `255-256=-1`. The upper truncated field is 894, which still gives quotient 3, so its byte correction is zero.

For `u0=-256`, `u1=1`, `beta=1`, x=-1 and y=256. The upper field becomes 255. Adding back its borrow changes quotient 0 into 1. This exercises the rare correction boundary exactly.

For `U=381`, `beta=78`, the result is 117. Signed9 wrapping would turn 381 into -131 and produce -39. The core instead selects a wide singleton and returns 117.

## Architecture and measured boundary

```mermaid
flowchart LR
  S[External ordered operand source and common zero filter] --> R[Actual signed9 range tests and coefficient equality]
  R --> M[Packed pair or signed16 singleton layout]
  M --> D[One registered DSP48E1]
  D --> Q[Borrow recovery and exact quotient correction]
  Q --> O[Ordered signed16 outputs and count]
  R -. Accepted consume count 1 or 2 .-> S
```

The measured E5 core includes range/equality tests, layout selection, exact correction and the elastic interface. Operand memory, the source queue, variable-consumption source integration and common zero-filter hardware remain external. Unstalled core latency is two advancing edges. A leakage issue is not a full neuron-update cycle.
''')
write('docs/PRIOR_WORK.md','''# Specific contribution and prior-work boundary

A new integrated mechanism can contribute without inventing every building block. This work combines an overlapping rounded-leakage decoder, actual-membrane admission and exact signed16 singleton fallback in a measured one-DSP primitive.

Value-based narrowness detection and operation packing have prior work: Brooks and Martonosi, DOI 10.1145/350853.350856. DSP-Packing (arXiv:2203.11028) establishes packed arithmetic and signed correction. Arithmetic Packing (arXiv:2606.11065) covers exact spill reconstruction. XtraMAC (arXiv:2605.06052) covers runtime datatype packing. These building blocks are explicitly credited.

FireFly uses fixed12-bit SIMD spike accumulation and shift leakage. Our constructed controls execute the same leakage operation as E5. Their numbers are not FireFly accelerator reproductions. UDP (DOI 10.1145/3748173.3779194) supplies relevant configuration and correction ancestry, but its inspected full methods do not describe this actual-U pair/singleton policy.

Original full methods remain unavailable for Ou (10.1109/TCSII.2024.3377356), Cui (10.1109/ICFPT64416.2024.11113473) and McKeown (10.1109/SIPS.2008.4671768). This review supports a specific implemented contribution. It does not prove worldwide first-ever status. No publication acceptance or network-accuracy gain is claimed.
''')
write('docs/REPRODUCIBILITY.md','''# Reproduction levels

## Portable arithmetic example

Python 3.10 or later, with no external packages:

```
python examples/run_examples.py
python examples/check_arithmetic.py
python scripts/verify_release.py
```

These commands are portable and leave the preserved evidence unchanged. They demonstrate the algebra and audit the release. They do not rerun full model inference or certify a new routed FPGA implementation.

## Portable RTL smoke simulation

With Icarus Verilog on PATH:

```
python scripts/run_rtl_smoke.py
```

The portable smoke test substitutes an explicitly labeled behavioral multiply-add for the vendor DSP primitive. It exercises the unmodified E5 control/decoder and stalls. Accepted Vivado RTL evidence uses the real AMD DSP48E1 library and remains indexed in the research archive. The behavioral test is not new FPGA timing or energy evidence.

## Paper and slides

The paper is a standalone IEEEtran conference `.tex` file. Compile it with an IEEEtran-capable LaTeX installation. Its source enforces at most four technical pages and five total pages. The main workspace copy was checked with the Codex built-in compiler. Exported submission PDF font embedding, file size and final visual inspection still need the authors' upload check.

`slides/mentor_briefing.pptx` contains editable diagrams/charts/tables and detailed notes. `slides/slide-notes.md` provides a text reading route.

## Preserved full research workflow

`work/adaptive_snn_probe/` preserves all research-authored Python, SystemVerilog and Tcl sources, including discarded trials. Their original directory relationships remain intact. Historical manifests contain original absolute paths and source hashes. They are provenance receipts, not portable launch instructions. Some historical scripts write accepted filenames or require missing raw assets. Read their source and use a separate working copy with fresh attempt labels before running them.

`release_manifest.json` binds shipped file bytes by relative path. It provides portability without rewriting historical evidence hashes. `scripts/verify_release.py` checks every published file. Generated DCPs, complete SAIFs, large logs, raw inference tensors, trained weights and datasets are excluded from Git. They are not required for the portable examples but are required for independently rerunning some complete research stages.

The repository's `.gitattributes` preserves original file bytes across operating systems, including line endings. GitHub Actions runs the portable arithmetic checks, release manifest check and behavioral RTL smoke test; it does not reproduce licensed Vivado routes or complete model inference.

The detailed existing guide is `research_reports/membrane_leakage_reproduce_20261011.md`. Read its absolute links as historical local locations. Relevant selected route/power/model receipts reside under `work/adaptive_snn_probe/validation_close/`. Reports preserve failed attempts and distinguish accepted data from unmeasured controls.

## Original model assets

GLIF: https://github.com/CAS-CLab/Gated-LIF at commit `60638b28ff8b688b51867e7dd44f1e065d4892b0`, ResNet18/CIFAR10/T2 checkpoint `trained models/resCifar18stand-CIFAR10-step2-CW.pth.tar`.

OTTT: https://github.com/pkuxmq/OTTT-SNN at commit `c15d5da05eea0c48e1fa837a4f8073297006d93f`, official VGG11/CIFAR10/T6 checkpoint. `ottt_source_manifest.json` records the official Drive folder and selected asset hash.

TinyImageNet: https://github.com/Intelligent-Computing-Lab-Panda/Visual-Explanations-from-Spiking-Neural-Networks-using-Interspike-Intervals at commit `178789c74fef72b9c25bd31d65ac598c987e1de9`, `pretrained_tiny_t30.pth.tar`. This is the evaluated BNTT-style model released with the Scientific Reports paper, not an evaluated checkpoint from the separate BNTT training repository.

Download source/weights/data from their original owners, retain licenses and verify the recorded hashes. Evaluation adapters preserve reset ordering, thresholds and Poisson inputs. They require NumPy, PyTorch and the model-specific dependencies described by the original repositories. Exact package metadata remains in the historical environment/source records. The local validation used `rn_dps/.venv`; that machine path is not a portable environment specification.

## Hardware and estimated energy

Accepted runs use Vivado 2025.2, Artix7 `xc7a100tcsg324-1`, 12ns, the same 94FF fixture, complete slow/max known-pin SDF replay and complete physical-net SAIF annotation. Timing checks remain enabled. Energy means estimated fixture dynamic pJ per scalar operand at 25C, not board/static/memory/full-neuron energy. Do not suppress timing errors or substitute a different activity interval to obtain a passing energy result.
''')
write('README.md','''# Exact adaptive DSP packing for SNN membrane leakage

This public research handoff explains and implements a compact FPGA leakage primitive. Actual membrane values select **two narrow operations or one exact full-width operation** per DSP issue. The stored membrane remains signed16 throughout.

**The contribution is the integrated exact leakage decoder and membrane admission mechanism, with measured trade-offs.** It is a focused circuit study for a potential ISCAS submission. It is not an accepted paper or a complete SNN accelerator.

## Start here

- [Mentor reading guide](docs/START_HERE.md)
- [Editable explanatory slides](slides/mentor_briefing.pptx) and [slide notes](slides/slide-notes.md)
- [IEEE paper source](paper/membrane_leakage_paper_draft.tex)
- [Current verified results](docs/RESULTS.md)
- [Submission recommendation and remaining author checks](docs/READINESS.md)
- [Complete user-facing conversation export](chat/conversation.md), [offline HTML](chat/conversation.html), and [shared chat snapshot](https://chatgpt.com/s/cx_6acb1c46e7688191b3cd0aa437cddd1c)

## What operation does it pack?

```
L(U, beta) = ceil(beta * U / 256)
U: signed16, -32768 through 32767
beta: unsigned Q8 coefficient code, 0 through 256
```

This is the membrane **leakage multiplication** within a neuron update. Synaptic accumulation is a different operation. Converting a floating neuron into this integer contract can change predictions. Packing then preserves the declared integer results exactly.

## What makes it adaptive?

The core examines two consecutive available operands at runtime. When both membranes lie in `[-256,255]` and their beta values match, it consumes two. Otherwise it consumes one and computes the full signed16 result. The output count tells the external source how many operands to advance. No voltage rescaling or exponent changes occur.

```
(-3, 5), beta=128: narrow pair gives (-1, 3) in one DSP issue
381, beta=78: wide singleton gives 117 exactly
```

An overlapping product layout saves DSP input bits. A parity bit recovers the lower field's signed borrow, and a compact correction recovers the exact rounded upper result. [Derivation, boundary example and architecture](docs/MECHANISM.md).

## Quick examples

```
python examples/run_examples.py
python examples/check_arithmetic.py
python scripts/verify_release.py
```

These use Python's standard library. The optional `python scripts/run_rtl_smoke.py` requires Icarus Verilog and exercises the unmodified core with a labeled behavioral DSP model. [Reproduction scope and original model assets](docs/REPRODUCIBILITY.md).

## Verified evidence

The adaptive E5 core uses **62 LUTs, 44 FFs and one DSP** at the selected matched12ns route. The fixed full-domain split E1 uses202 LUTs,79 FFs and one DSP. Both implement the same declared general coefficient arithmetic.

On the evaluated GLIF64-image stream, E5 needs **46.01% fewer leakage issues than a one-DSP scalar**, and1.0836% more than fixed split packing. Representative fixture dynamic energy is21.599pJ/scalar, compared with24.648 for the one-DSP scalar and55.308 for fixed split. The two-DSP scalar pair uses21.371pJ/scalar, so this is approximately energy parity with half the DSP count, not universal superiority.

Public-model validation covers GLIF ResNet18/CIFAR10/T2, OTTT VGG11/CIFAR10/T6 and an independent BNTT-style VGG11/TinyImageNet/T30 model. Every tested packed integer state/spike/logit matches its scalar integer reference. Full-test and64-image scopes differ and are stated in [results](docs/RESULTS.md).

## Operating limits

Exact half-leakage shifting outperforms E5 for OTTT's beta128. Wider membrane streams reduce pairing opportunities. E5's issues exceed fixed split on OTTT and TinyImageNet. Operand memory and variable-consumption source integration remain outside reported core area/energy. There is no demonstrated end-to-end burst-latency improvement or packing accuracy gain.

Original LUT E2 failed delayed replay and contributes no accepted energy. The independent exact E7 LUT control passes the stricter replay/activity audit. Failed evidence is retained. Three relevant original full methods remain unavailable, so this repository does not claim proven first-ever status. [Prior-work distinctions](docs/PRIOR_WORK.md).

## Repository organization

`rtl/` provides convenient exact copies of the current core and controls. `examples/` explains the arithmetic with executable integers. `scripts/` contains portable release and RTL-smoke commands. `paper/`, `slides/`, `docs/` and `chat/` provide the mentor handoff. `work/adaptive_snn_probe/` preserves the complete research-authored source archive and lightweight result receipts, including earlier discarded approaches. `research_reports/` preserves experiment summaries.

The release manifest checks shipped bytes. Historical receipts retain their original paths and hashes rather than pretending a Git clone contains every large raw artifact. Vendor libraries, datasets, weights, routed checkpoints and complete SAIF files remain external. See [source/release notice](NOTICE.md).
''')
current=DEST/'docs/readiness_receipt.json'
if current.exists():
 e9=json.loads(current.read_text())['numbers']['E9']
 if e9['accepted_energy']:
  value=e9['estimated_energy_pJ']
  detail=f"The added checkpoint-specific GLIF control supports all 33 trained coefficient codes using a shared exact add/sub pair: **375 LUTs, 82 FFs, zero DSPs and {value:.3f} pJ/scalar** on the same representative capture. Its full timed replay and independent physical audit pass. This is one measured construction, not an optimality bound for every constant implementation.\n\n"
  f=DEST/'README.md';text=f.read_text();text=text.replace('## Operating limits\n\n',detail+'## Operating limits\n\n');f.write_text(text)
write('release_manifest.json',json.dumps(dict(status='staging_additional_handoff_files_pending',preserved_original_files=manifest,omitted_asset_classes=['vendor generated netlists/checkpoints/activity','downloaded third-party source/model/data','caches'],conversation_messages=len(messages)),indent=2))
print(json.dumps(dict(files_copied=len(manifest),bytes=sum(x['bytes'] for x in manifest.values()),conversation_messages=len(messages),destination=str(DEST)),indent=2))
