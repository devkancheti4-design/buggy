"""The C file's own main(), in Python, against the port. The oracle is branchy and shares nothing with a lane."""
import shutil, subprocess, sys
from pathlib import Path
from buggy.mutation import mutation, word, lanes, BITS

BASE = [0, 5, 9, 12, 14]


def bits(x):
    return [(x >> i) & 1 for i in range(8)]


def oracle(x):
    fl, al, cl, ed, mv, uq, br, si = bits(x)
    if not fl and not mv: return 0                                      # R0
    rep = 2 if cl else (1 if al else 0)
    flp = 2 if (fl and uq) else (1 if fl else 0)
    knd = 2 if ed else 0
    flw = 1 if mv else 0
    s = sum(1 for g in (rep, flp, knd, flw) if g == 2); w = sum(1 for g in (rep, flp, knd, flw) if g == 1)
    r = 1 + BASE[s] + w
    return r >> 1 if br else r


def reach(x):
    fl, al, cl, ed, mv, uq, br, si = bits(x)
    if cl and not al: return False
    if al and not fl: return False
    if ed and not fl: return False
    if uq and not fl: return False
    if si and (fl or mv or br): return False
    if cl and br: return False
    return True


def s_of(x):
    fl, al, cl, ed, mv, uq, br, si = bits(x); return cl + int(fl and uq) + ed


def w_of(x):
    fl, al, cl, ed, mv, uq, br, si = bits(x); return int(al and not cl) + int(fl and not uq) + mv


R = [x for x in range(256) if reach(x)]


def test_reachable_words():
    assert len(R) == 45


def test_against_the_table_all_reachable():
    assert all(mutation(x) == oracle(x) for x in R)


def test_r0_neither_flip_nor_moves_is_zero():
    assert all(mutation(x) == 0 for x in R if not (x & 1) and not ((x >> 4) & 1))


def test_r1_r3_within_a_regime():
    for x in R:
        for y in R:
            if mutation(x) and mutation(y) and ((x >> 6) & 1) == ((y >> 6) & 1):
                sx, wx, sy, wy = s_of(x), w_of(x), s_of(y), w_of(y)
                if sx > sy: assert mutation(x) >= mutation(y)
                if sx == sy and wx > wy: assert mutation(x) >= mutation(y)
                if (sx, wx) == (sy, wy): assert mutation(x) == mutation(y)


def test_r2_monotone_breaks_excepted():
    for x in R:
        for i in range(8):
            if i == 6: continue
            if not (x & (1 << i)) and reach(x | (1 << i)):
                assert mutation(x | (1 << i)) >= mutation(x)


def test_r4_rank_15_unreachable_and_max_strong_3():
    assert max(s_of(x) for x in R) == 3
    assert all(mutation(x) != 15 for x in R)
    assert sorted({mutation(x) for x in R}) == list(range(15))


def test_a_deletion_never_outranks_the_same_edit():
    for x in R:
        if not ((x >> 3) & 1) and reach(x | 8):
            assert mutation(x) <= mutation(x | 8)


def test_silent_rules_zero_through_the_veto():
    assert all(mutation(x) == 0 for x in R if x >> 7)


def test_lands_in_range_on_all_256():
    assert all(0 <= mutation(x) <= 15 for x in range(256))


def test_the_anchors():
    want = {15: 11, 63: 14, 41: 10, 16: 2, 65: 1, 64: 0, 128: 0}
    assert {x: mutation(x) for x in want} == want


def test_word_and_lanes():
    x = word({"FLIP": 1, "ALL": 1, "CLEAN": 1, "EDIT": 1})
    assert x == 15 and lanes({"FLIP": 1, "ALL": 1, "CLEAN": 1, "EDIT": 1}) == (["REPAIR", "KIND"], ["FLIP"])
    assert len(BITS) == 8


def test_the_c_kernel_agrees_when_a_compiler_is_here(tmp_path):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        return
    src = Path(__file__).resolve().parents[1] / "src/buggy/laws/mutation.c"
    exe = tmp_path / "mutation"
    assert subprocess.run([cc, "-O2", "-o", str(exe), str(src)], capture_output=True).returncode == 0
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    assert r.returncode == 0 and "TOTAL  0 violations" in r.stdout, r.stdout
