"""The hive measures the same bits as the single lane, by construction; only the clock differs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from test_root_cause import make
from buggy.locate import locate


def _bits(L):
    return {(f.file, f.line): dict(f.bits) for f in L.mutation}


def test_hive_and_single_lane_agree(tmp_path):
    root = make(tmp_path)
    one = locate(root, bisect=False, trace=False, jobs=1, mutants=60, mutate_s=300)
    hive = locate(root, bisect=False, trace=False, jobs=3, mutants=60, mutate_s=300)
    assert one.mutation_cost["measured"] == hive.mutation_cost["measured"] >= 3, (one.mutation_cost, hive.mutation_cost)
    assert one.mutation_cost["mutants"] == hive.mutation_cost["mutants"]
    assert _bits(one) == _bits(hive), (_bits(one), _bits(hive))
    assert [(f.file, f.line, f.rank) for f in one.mutation] == [(f.file, f.line, f.rank) for f in hive.mutation]
    assert hive.mutation_cost["workers"] == 3 and hive.repairs and hive.repairs[0]["edit"] == "+ → *"


def test_budget_is_counted_on_assignment(tmp_path):
    root = make(tmp_path)
    L = locate(root, bisect=False, trace=False, jobs=3, mutants=7, mutate_s=300)
    assert L.mutation_cost["mutants"] <= 7 and L.mutation_cost["cut"] >= 1, L.mutation_cost
