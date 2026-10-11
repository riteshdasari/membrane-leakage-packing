"""Create separate original-pixel runners; rejected preview results stay pinned."""
from pathlib import Path
P=Path(__file__).resolve().parent
text=(P/'run_pilot.py').read_text(encoding='utf-8')
for old,new in(('pilot_plan.json','original_pilot_plan_v2.json'),('pilot_test64.npz','original_test64.npz'),
                ('pilot_results.json','original_pilot_results_v2.json'),('pilot_logits.npz','original_pilot_logits_v2.npz'),
                ('pilot_data_acquisition.json','full_data_acceptance_v2.json')):text=text.replace(old,new)
text=text.replace('torch.set_num_threads(2)','torch.set_num_threads(8)')
text=text.replace("device='cpu',threads=2", "device='cpu',threads=8")
(P/'run_original_pilot_v2.py').write_text(text,encoding='utf-8')
text=(P/'run_full_v2.py').read_text(encoding='utf-8')
for old,new in(('full_test_plan_v2','full_test_plan_v3'),('full_data_acceptance.json','full_data_acceptance_v2.json'),
                ('pilot_logits.npz','original_pilot_logits_v2.npz'),('full_test_progress_v2','full_test_progress_v3'),
                ('full_test_logits_v2','full_test_logits_v3'),('full_test_results_v2','full_test_results_v3')):text=text.replace(old,new)
text=text.replace("original=np.load(P/'original_pilot_logits_v2.npz')['logits']", "original=np.load(P/'original_pilot_logits_v2.npz')['logits']")
text=text.replace("while not(P/'full_data_acceptance_v2.json').exists():time.sleep(3)",
    "while not(P/'full_data_acceptance_v2.json').exists()or not(P/'original_pilot_results_v2.json').exists():time.sleep(3)")
text=text.replace("P/'checkpoint_arrays.npz'", "P/'checkpoint_arrays_v3.npz'")
text=text.replace("P/'unmodified_control_acceptance.json',P/'thread_timing_v2.json'", "P/'original_pilot_results_v2.json',P/'thread_timing_v2.json',P/'preview_pilot_rejection.json'")
(P/'run_full_v3.py').write_text(text,encoding='utf-8')
print('Prepared original-pixel pilot and full-test runners, preserving all rejected preview artifacts.')
