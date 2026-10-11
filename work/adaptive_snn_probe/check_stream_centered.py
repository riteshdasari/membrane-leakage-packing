"""Use the same independent stimuli and oracle for the centered repair."""
from pathlib import Path
import sys
from check_stream_offset import simulate
P=Path(__file__).resolve().parent;R=P/'results'
small='--small'in sys.argv;dataset='smoke'if small else'main'
tokens=iter((R/f'stream_offset_{dataset}_25_0/stream_stim.txt').read_text().split());n=int(next(tokens));frames=[]
for j in range(n):
 length,d,gap=[int(next(tokens))for _ in range(3)];vals=[int(next(tokens),16)for _ in range(length)]
 frames.append(([v-2048 if v>=1024 else v for v in vals],d,gap))
for dc,stall in [(25,0),(-1,1)]:simulate(f'stream_centered_{dataset}_{dc}_{stall}',frames,dc,stall,variant='centered')
