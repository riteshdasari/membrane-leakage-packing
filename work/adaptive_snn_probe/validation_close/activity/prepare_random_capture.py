"""Retain midpoint experiment and declare an anti-alias randomized stratified follow-up."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
original=HERE/'capture_activity.py'
out=HERE/'capture_activity_random_v2.py'
assert not out.exists()
s=original.read_text()
s=s.replace("HERE = Path(__file__).resolve().parent\nTRIAL = HERE.parent.parent / 'sequential_paper_trial'", "HERE = Path(__file__).resolve().parent / 'random_stratified_v2'\nTRIAL = HERE.parent.parent.parent / 'sequential_paper_trial'")
s=s.replace("eight contiguous windows per nonzero batch/layer/time frame, centered at the midpoints of eight equal-length nonzero-index strata", "eight contiguous windows per nonzero batch/layer/time frame, each uniformly positioned within its equal-length nonzero-index stratum by a fixed deterministic PCG64 seed from SHA256 of seed417839/layer/time/batch; no measured outcome enters placement")
s=s.replace("        for j in range(8):\n            left=((2*j+1)*N)//16-L//2;right=left+L", "        seed_text=f'417839/{name}/{step}/{batch_start}'.encode('utf-8')\n        rng=np.random.default_rng(int.from_bytes(hashlib.sha256(seed_text).digest()[:8],'little'))\n        for j in range(8):\n            bin_start=j*N//8;bin_end=(j+1)*N//8\n            left=int(rng.integers(bin_start,bin_end-L+1));right=left+L")
s=s.replace("    save('plan.json',plan)", "    plan['sampling_method_change_reason']='Fixed midpoint windows can systematically alias power-of-two feature planes and channelwise coefficients. Random positions were selected as the follow-up method before inspecting either outcome; both experiments retained, no best-result selection.'\n    plan['retained_midpoint_capture_directory']=str(HERE.parent)\n    plan['placement_seed']=417839\n    save('plan.json',plan)")
assert 'seed_text' in s and "random_stratified_v2" in s
out.write_text(s,encoding='utf-8')
v=(HERE/'verify_activity.py').read_text()
v=v.replace("HERE=Path(__file__).resolve().parent\nTRIAL=HERE.parent.parent/'sequential_paper_trial'", "HERE=Path(__file__).resolve().parent/'random_stratified_v2'\nTRIAL=HERE.parent.parent.parent/'sequential_paper_trial'")
vout=HERE/'verify_activity_random_v2.py';assert not vout.exists();vout.write_text(v,encoding='utf-8')
record=dict(status='prepared_before_follow_up_inference',reason='prevent coefficient/channel layout aliasing, not favor selected hardware results',
            original_capture=hashlib.sha256(original.read_bytes()).hexdigest(),new_capture=hashlib.sha256(out.read_bytes()).hexdigest(),
            new_verifier=hashlib.sha256(vout.read_bytes()).hexdigest(),seed=417839)
(HERE/'random_v2_preparation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
