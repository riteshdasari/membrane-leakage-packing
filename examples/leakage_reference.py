"""Executable explanation of the E5 integer contract, using unbounded Python ints."""
def reference(u,beta):
    if not -32768<=u<=32767 or not 0<=beta<=256:raise ValueError('Outside signed16/Q8 domain')
    return -((-u*beta)//256)

def signed(value,bits):
    value &= (1<<bits)-1
    return value-(1<<bits) if value&(1<<(bits-1)) else value

def packed_pair(u0,u1,beta):
    if not (-256<=u0<=255 and -256<=u1<=255 and 0<=beta<=256):
        raise ValueError('Pair requires signed9 membranes and beta0..256')
    a=(u0+256)+(u1<<16)
    c=255-256*beta+(255<<16)
    p=a*beta+c
    r=((beta&1)&(u1&1))^1
    n=((p>>16)&1)^r
    low=((p>>8)&255)-256*n
    carry=int(bool(n) and ((p>>16)&255)==255)
    high=signed((p>>24)&511,9)+carry
    return (low,high),dict(A=a,C=c,P=p,x=beta*u0+255,y=beta*u1+255,reference_bit=r,borrow=n,upper_quotient_correction=carry)

def issue(operands):
    """One accepted request. The caller retains operands after the returned count."""
    if not operands:raise ValueError('No available operand')
    u0,b0=operands[0];reference(u0,b0)
    if len(operands)>1:
        u1,b1=operands[1];reference(u1,b1)
        if -256<=u0<=255 and -256<=u1<=255 and b0==b1:
            values,detail=packed_pair(u0,u1,b0)
            return 2,values,'pair',detail
    return 1,(reference(u0,b0),),'singleton',{}

def execute(operands):
    output=[];trace=[];position=0
    while position<len(operands):
        count,values,mode,detail=issue(operands[position:position+2])
        trace.append(dict(first_operand=position,count=count,mode=mode,inputs=operands[position:position+count],outputs=values,details=detail))
        output.extend(values);position+=count
    return output,trace
