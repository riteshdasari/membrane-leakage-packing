"""All legal scalar pairs plus ordered failures and unchanged LIF feedback."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent
sys.path.insert(0,str(ROOT/'residue_frontier_trial'))
from prepare_frontier_work import load_groups
MAP={0:'adaptive5full_3U8_DSP',1:'fixed8_precomputed_DSP',2:'native_FOUR12_DSP4_LUT4',3:'full_LUT8',4:'adaptive5full_3U8_LUT'}
def take_for(e,pairs,pos):
    av=min(8,len(pairs)-pos)
    if e in(1,2,3):return av
    n=min(av,5)
    while n<av and -128<=pairs[pos+n][0]<=127:n+=1
    return n
def groups_for(kind):
    if kind!='main':
        groups=load_groups(ROOT/f'trained_reference_admission_study/leak_shift{kind[-1]}/stream_stim.txt')
        assert all(-686<=u<=245 and -128<=i<=127 for _,pairs in groups for u,i in pairs)
        return groups
    groups=[(0,[(u,i)for i in range(-128,128)])for u in range(-686,246)]
    for bad in(5,6,7,8):
        for wide in(-686,-129,128,245):
            for narrow in(-128,-1,0,127):
                for current in(-128,-1,0,127):
                    pairs=[(-686 if j%2 else 245,current)for j in range(5)]
                    pairs.extend((wide if j==bad else narrow,current)for j in range(5,8))
                    groups.append((bad%3,pairs))
    # Partial groups, stalls, cross-field positive/negative carry boundaries.
    for n in range(1,33):
        groups.append((n%4,[((-686,-129,-128,-32,-1,0,31,127,128,245)[j%10],(-128,-1,0,31,127)[(j+n)%5])for j in range(n)]))
    return groups
def predictions(groups):
    rows=[]
    for e in range(5):
        requests=0;hist={str(n):0 for n in range(1,9)}
        for _,pairs in groups:
            pos=0
            while pos<len(pairs):
                n=take_for(e,pairs,pos);pos+=n;requests+=1;hist[str(n)]+=1
        rows.append(dict(engine=e,label=MAP[e],requests=requests,take_histogram=hist))
    return rows
