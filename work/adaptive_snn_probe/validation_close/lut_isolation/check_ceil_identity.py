"""Exhaustively verify the exact alternative LUT rounding expression, B16."""
from pathlib import Path
import hashlib
import json
import time
import numpy as np

P=Path(__file__).resolve().parent
start=time.time()
u=np.arange(-32768,32768,dtype=np.int64)
cases=0
for beta in range(257):
    product=u*beta
    declared=(product+255)>>8
    alternative=(product>>8)+((product&255)!=0)
    assert np.array_equal(declared,alternative),(beta,u[declared!=alternative][0])
    # Match the actual multiplier construction, which bypasses beta=256.
    lut_product=u*(beta&255)
    rtl=u if beta==256 else (lut_product>>8)+((lut_product&255)!=0)
    assert np.array_equal(declared,rtl)
    assert declared.min()>=-32768 and declared.max()<=32767
    cases+=len(u)
result={'status':'pass','contract':'signed16 U; beta integer 0..256; ceil(beta*U/256)',
        'cases':cases,'coefficients':257,'failures':0,'seconds':time.time()-start,
        'identity':'ceil(p/256)=(p arithmetic-shift-right 8)+OR(p[7:0])',
        'negative_product_rule':'arithmetic shift implements floor; nonzero low byte adds one even for negative p',
        'RTL_sizing':'B+9-bit signed product; B+1-bit signed floor quotient plus explicitly signed zero-extended one-bit increment; truncate only after proven B-bit result bounds',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(P/'ceil_identity.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
