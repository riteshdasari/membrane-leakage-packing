"""Verify the same oracle with a declared maximum two supplied values per issue."""
import sys
from pathlib import Path
import verify_frontier as checker
checker.take_for=lambda engine,pairs,pos:min(2,len(pairs)-pos)
if __name__=='__main__':checker.main()
