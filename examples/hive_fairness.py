#!/usr/bin/env python3
"""Single lane against the hive, fairly: the same cases, the same mutant budget (time never cuts), on the
same machine one after another. Reports seconds, mutants, and whether every measured line's bits and the
final ranks are identical — they must be, by construction; this is the check."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src")); sys.path.insert(0, str(Path(__file__).resolve().parent))
import adversarial
from buggy import locate as L

PICK = {"shared helper, wrong file", "data, not code", "2,000-line file, one repair", "five failures, one cause"}
JOBS = int(sys.argv[1]) if len(sys.argv) > 1 else 6

def run_with(jobs):
    def wrapped(root, **kw):
        kw.pop("jobs", None); kw["mutate_s"] = 1800; kw.setdefault("mutants", 300)
        return L.locate(root, jobs=jobs, **kw)
    adversarial.locate = wrapped

def bits(Lc): return {(f.file, f.line): dict(f.bits) for f in Lc.mutation}
def ranks(Lc): return [(f.file, f.line, f.rank) for f in Lc.mutation]

print(f"{'case':30} {'lane s':>7} {'hive s':>7} {'speedup':>8} {'mutants':>8} {'same bits':>10} {'same ranks':>11}")
for name, hint, fn in adversarial.CASES:
    if name not in PICK: continue
    run_with(1); t0 = time.time(); one, truth = fn()[:2]; t1 = time.time() - t0
    run_with(JOBS); t0 = time.time(); hive, _ = fn()[:2]; t2 = time.time() - t0
    c1, c2 = one.mutation_cost, hive.mutation_cost
    print(f"{name:30} {c1['seconds']:>7} {c2['seconds']:>7} {c1['seconds'] / max(c2['seconds'], 0.1):>7.1f}x "
          f"{c1['mutants']:>3}/{c2['mutants']:<4} {str(bits(one) == bits(hive)):>10} {str(ranks(one) == ranks(hive)):>11}"
          + ("" if c1["measured"] == c2["measured"] else f"   MEASURED DIFFER {c1['measured']} vs {c2['measured']}"))
print("FAIRNESS_DONE")
