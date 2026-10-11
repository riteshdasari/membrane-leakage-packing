"""Four isolated low-memory F5 RTL cohorts; route jobs remain root-serialized."""
import sys
sys.dont_write_bytecode=True
import run_frontier_f5 as run
assert '--run' in sys.argv
for kind,stall in [('models',0),('models',1),('main',0),('main',1)]:
    print('F5 NATIVE QUEUE',kind,stall,flush=True)
    run.native(kind,stall,0)
run.functional()
print('F5 ALL FOUR NATIVE COHORTS PASS',flush=True)
