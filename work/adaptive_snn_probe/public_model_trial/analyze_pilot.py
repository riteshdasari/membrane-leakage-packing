"""Interpret fixed predeclared screens without claiming a new integer model."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;r=json.loads((P/'pilot_results.json').read_text())
rows=[]
for scale in json.loads((P/'pilot_plan.json').read_text())['units']:
    counts={k:sum(layer['units'][str(scale)][k]for layer in r['rows'])for k in
        ('updates','U_fits_i8','I_fits_i8','both_fit_i8','current_outside_i8')}
    widths=[dict(layer=layer['layer'],U_bits=layer['units'][str(scale)]['U_observed_signed_bits'],
        I_bits=layer['units'][str(scale)]['I_observed_signed_bits'],S_bits=layer['units'][str(scale)]['S_observed_signed_bits'],
        membrane_only_full_vs_tail_high_FF_saving=layer['units'][str(scale)]['five_full_three_U8_metadata_FF_saving_vs_fixed8_if_contract_legal'])for layer in r['rows']]
    assert counts['updates']==r['neuron_updates']
    rows.append(dict(scale=scale,**counts,U8_fraction=counts['U_fits_i8']/counts['updates'],
        I8_fraction=counts['I_fits_i8']/counts['updates'],both8_fraction=counts['both_fit_i8']/counts['updates'],
        current_incompatible_layers=[layer['layer']for layer in r['rows']if layer['units'][str(scale)]['current_outside_i8']>0],
        membrane_only_metadata_saving_layers=sum(x['membrane_only_full_vs_tail_high_FF_saving']>0 for x in widths),observed_widths=widths))
result=dict(status='pass_bounded_observed_operand_interpretation',rows=rows,
    conclusion='No predeclared unit establishes a hardware advantage. At coarse unit16 all observed membranes and currents fit int8; at finer units current exceptions invalidate existing I8-only RTL. In all68 layer/unit observed-width pairs, membrane-only narrowing with a global current width saves no high-base metadata. Joint U/I or sum admission is a different implementation that would need fair fixed controls and its own proof/RTL.',
    all_layer_unit_cases=68,membrane_only_metadata_saving_layer_unit_cases=sum(x['membrane_only_metadata_saving_layers']for x in rows),
    limits=['Observed maxima are not legal width certificates.','Rounded float operands do not constitute integer SNN inference or preserved float outputs.',
        'Pilot accuracy81.25percent over64 examples is not a reproduction of full published94.19percent accuracy.',
        'No prospective workload can reduce the request count below a legal eight-output fixed baseline for this addition interface.'],
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in(Path(__file__),P/'pilot_plan.json',P/'pilot_results.json')})
assert result['membrane_only_metadata_saving_layer_unit_cases']==0
(P/'pilot_interpretation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items()if k not in('rows','pins')},indent=2))
