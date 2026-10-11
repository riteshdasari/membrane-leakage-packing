"""Admission only: do not rebrand filtered SRM reset state as membrane U."""
import hashlib,json
from pathlib import Path
import torch
P=Path(__file__).resolve().parent
pin='cb1e7faaabfe91de27c109c121da0e52077be944'
repo=P/'iir_archive'/('snn-iir-'+pin)
checkpoint=repo/'examples/checkpoint/pretrained_snn_mlp_2'
state=torch.load(checkpoint,map_location='cpu',weights_only=True)['snn_state_dict']
coeffs={k:{'shape':list(v.shape),'min':float(v.min()),'max':float(v.max()),
          'unique_values':int(torch.unique(v).numel())}
        for k,v in state.items() if any(w in k for w in ('alpha','decay','reset_v'))}
paths=[repo/'examples/snn_mlp_2.py',repo/'examples/snn_mlp_2.yaml',
       repo/'snn_lib/snn_layers.py',checkpoint,P/'iir_source.zip',Path(__file__)]
result={'status':'excluded_from_actual_membrane_leakage_benchmark',
        'paper':'Exploiting Neuron and Synapse Filter Dynamics in Spatial Temporal Learning of Deep Spiking Neural Network, IJCAI2020',
        'repository':'https://github.com/Snow-Crash/snn-iir','commit':pin,
        'available_trained_checkpoint':str(checkpoint),'model':'MNIST MLP784-500-500-10,T25',
        'configuration_membrane_filter':False,
        'actual_voltage':'weighted filtered input minus previous reset trace; no previous voltage multiplication when membrane_filter=False',
        'decayed_state':'Reset trace, plus separately learned first-order synaptic/axon filter states',
        'coefficient_audit':coeffs,
        'reason':'Changing membrane_filter to True or calling resettrace U would change the trained model or the stated packing target. This model is not evidence of actual-U leakage packing.',
        'original_source_config_discrepancy':'YAML membrane_filer key is misspelled whereas script reads membrane_filter; retained unchanged',
        'inference_performed':False,
        'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(P/'iir_admission_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
