from leakage_reference import execute,packed_pair,reference
for u0,u1,beta in [(-3,5,128),(-256,1,1),(-16,15,231)]:
    results,detail=packed_pair(u0,u1,beta)
    print(f'PAIR u=({u0},{u1}), beta={beta}: {results}, borrow={detail["borrow"]}, upper correction={detail["upper_quotient_correction"]}')
    assert results==(reference(u0,beta),reference(u1,beta))
operands=[(-3,128),(5,128),(381,78),(-2,128),(7,128)]
values,trace=execute(operands)
print('\nOrdered workload, no zero filter:')
for row in trace:print(f'issue {row["first_operand"]}: {row["mode"]}, consume {row["count"]}, {row["inputs"]} gives {row["outputs"]}')
assert values==[reference(u,b) for u,b in operands]
print(f'{len(operands)} scalar operands, {len(trace)} DSP issues, exact output {values}')
print(f'Unsafe signed9 wrap of 381 would give {reference(381-512,78)} rather than {reference(381,78)}')
