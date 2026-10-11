"""Read existing checkpoints only; emit tied structural evidence.

Vivado checkpoints embed zstd-compressed EDIF. This uses Vivado's existing
libzstd.dll to decompress those members; it never opens Vivado or modifies a
checkpoint. Names identify register/adder groups, not formal logic equivalence.
"""
from pathlib import Path
import ctypes,hashlib,json,os,re,zipfile

P=Path(__file__).resolve().parent;R=P/'results'
LIB=Path('C:/AMDDesignTools/2025.2/Vivado/lib/win64.o/libzstd.dll')
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 os.add_dll_directory(str(LIB.parent))
 lib=ctypes.CDLL(str(LIB))
 lib.ZSTD_decompress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
 lib.ZSTD_decompress.restype=ctypes.c_size_t
 lib.ZSTD_isError.argtypes=[ctypes.c_size_t];lib.ZSTD_isError.restype=ctypes.c_uint
 cases=[('new_four_stage','top_stream_pipeline_adaptive_const','stream_pipeline_leak.sv','stream_pipeline_hardware.json'),
        ('old_three_stage','top_stream_fold_offset_const','stream_fold_leak.sv','stream_fold_hardware.json')]
 observations=[]
 primitive=re.compile(r'\(instance\s+(?:\(rename\s+\S+\s+"([^"]+)"\)|([^\s()]+))\s+\(viewref\s+netlist\s+\(cellref\s+(FDRE|FDSE|FDCE|FDPE|CARRY4)\b')
 for label,top,source,summary in cases:
  source_bytes=(P/source).read_bytes();source_sha=sha(source_bytes)
  rows=json.loads((R/summary).read_text());row=next(x for x in rows if x['top']==top)
  recorded=row['source_sha256'][source] if 'source_sha256' in row else row['rtl_sha256']
  assert source_sha==recorded,(label,'Current RTL differs from route pin')
  checkpoints=[]
  for phase in ['synth','route']:
   cp=R/f'{top}_{phase}'/'design.dcp';cp_bytes=cp.read_bytes()
   with zipfile.ZipFile(cp) as z:
    member=top+'.edf';packed=z.read(member)
   output=ctypes.create_string_buffer(4000000);input_buffer=ctypes.create_string_buffer(packed)
   size=lib.ZSTD_decompress(output,len(output),input_buffer,len(packed));assert not lib.ZSTD_isError(size)
   edif=output.raw[:size];text=edif.decode()
   instances=[dict(name=m[1]or m[2],primitive=m[3])for m in primitive.finditer(text)]
   ff=[x['name']for x in instances if x['primitive'].startswith('FD')]
   carry=[x['name']for x in instances if x['primitive']=='CARRY4']
   groups={}
   for stem in ['raw0','meta0','meta1','meta2','u_out']:
    names=[n for n in ff if re.search(r'(?:^|[./])'+stem+r'_reg\[\d+\]$',n)]
    indices=sorted(int(re.search(r'\[(\d+)\]$',n)[1])for n in names)
    groups[stem]=dict(count=len(names),indices=indices,instances=names)
   fixture_ff=[n for n in ff if n.startswith('src_')or n.startswith('sink_')]
   if label=='new_four_stage':pre=[n for n in carry if 'meta1_reg' in n]
   else:pre=[n for n in carry if 'wide_meta' in n or 'fold_pre2' in n]
   post=[n for n in carry if n not in pre]
   checkpoints.append(dict(phase=phase,path=str(cp.resolve()),checkpoint_sha256=sha(cp_bytes),
    edif_member=member,edif_sha256=sha(edif),all_primitive_ff_count=len(ff),fixture_ff_count=len(fixture_ff),
    inferred_core_ff_count=len(ff)-len(fixture_ff),ff_groups=groups,carry4_count=len(carry),
    carry4_groups=dict(name_derived_pre_correction=dict(count=len(pre),instances=pre),
                       remaining_decoder=dict(count=len(post),instances=post)),
    carry4_instances=carry))
  observations.append(dict(label=label,top=top,rtl_path=str((P/source).resolve()),rtl_sha256=source_sha,
   route_row_sha256=sha(json.dumps(row,sort_keys=True).encode()),route_row=row,checkpoints=checkpoints))
 audit=dict(method='Read-only checkpoint EDIF extraction using installed Vivado libzstd; no Vivado run',
  script_sha256=sha(Path(__file__).read_bytes()),decompression_library=str(LIB),
  scope='Same exact leakage candidate before/after input pipelining; different latency, fixture and constraints, so resource causes only, not a matched timing or throughput comparison',
  observations=observations,
  inference=dict(new_raw_capture_ff=33,extra_metadata_ff=22,extra_output_sign_ff=4,
   added_control_ff=6,total_ff_difference=65,
   explanation='33 raw capture +22 metadata +4 output copies +6 control =151−86. At positive constant coefficient, bypass implies zero raw input; explicitly exposing that invariant can remove unused metadata and sign copies. This is an optimization hypothesis, not a measured repaired-core saving.',
   carry_explanation='18 versus14 CARRY4; name-derived pre-correction chains12 versus8, consistent with two extra seven-bit narrow subtraction chains. Naming is structural evidence rather than a formal cell-to-expression proof.'),
  limitations=['No new synthesis or route.','Registers outside the core are excluded by preserved fixture register names.',
   'Constant bypass removal and subtraction sharing need separate exact RTL/routing verification.',
   'The four-stage worst routed path is an input bypass/enable path, so correction sharing alone does not imply a timing benefit.'])
 (R/'pipeline_register_cost_audit.json').write_text(json.dumps(audit,indent=2))
 for obs in observations:
  for cp in obs['checkpoints']:
   print(obs['label'],cp['phase'],'coreFF',cp['inferred_core_ff_count'],'metadata',[(s,cp['ff_groups'][s]['count'])for s in ['meta0','meta1','meta2']],'carry',cp['carry4_count'])
 print('Wrote',R/'pipeline_register_cost_audit.json')
if __name__=='__main__':main()
