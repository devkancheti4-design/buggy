# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE MUTATION LAW — which candidate line to examine first, ranked by what happens when it is changed.

A verbatim port of laws/mutation.c (generated; every lane authored by search). The body makes mutants of a
line — one operator altered — and runs the failing tests and the passing tests that execute the line;
eight facts about what happened are the byte the law reads. No number here is a weight: four lanes are
counted STRONG or WEAK and the priority is the dense lexicographic rank of (strong, weak). BREAKS is not
a lane but the regime, a shift: a line whose every alteration breaks correct behaviour is halved, never
vetoed. SILENT is in no lane: "measured and nothing" and "not measured" are both R0.

    bit 0 FLIP    bit 1 ALL     bit 2 CLEAN   bit 3 EDIT
    bit 4 MOVES   bit 5 UNIQUE  bit 6 BREAKS  bit 7 SILENT

    REPAIR  strong CLEAN            weak ALL without CLEAN
    FLIP    strong FLIP and UNIQUE  weak FLIP
    KIND    strong EDIT             —
    FLOW    —                       weak MOVES

tests/test_mutation_law.py holds the independent branchy oracle and checks all 45 reachable words, R0–R4,
the deletion-never-outranks-an-edit property, the range on 0..255, and the seven anchors."""

BITS = ("FLIP", "ALL", "CLEAN", "EDIT", "MOVES", "UNIQUE", "BREAKS", "SILENT")


def _flip(x):   return x & 1
def _all(x):    return 1 & (x >> 1)
def _clean(x):  return 1 & (x >> 2)
def _edit(x):   return 1 & (x >> 3)
def _moves(x):  return 1 & (x >> 4)
def _unique(x): return 1 & (x >> 5)
def _breaks(x): return 1 & (x >> 6)
def _silent(x): return x >> 7
def _f(x):      return (x - (x >> 1)) + (x | (x + x))


def keep(x: int) -> int:
    """R0: a mutant touched the failure."""
    return _flip(x) | _moves(x)


def strong(x: int) -> int:
    """CLEAN ⇒ ALL ⇒ FLIP and UNIQUE ⇒ FLIP, so the strong terms need no AND."""
    return _clean(x) + _unique(x) + _edit(x)


def nonsil(x: int) -> int:
    return _all(x) + _flip(x) + _edit(x) + _moves(x)


def mutation(x: int) -> int:
    """0..15; higher = examine first; 0 = no mutant of this line touched the failure."""
    return ((0 - keep(x)) & ((1 + nonsil(x) + _f(strong(x))) >> _breaks(x))) & 15


def word(bits: dict) -> int:
    return sum((1 << i) for i, k in enumerate(BITS) if bits.get(k))


def lanes(bits: dict) -> tuple[list, list]:
    """(strong, weak) lane names, for the reader."""
    s, w = [], []
    (s if bits.get("CLEAN") else w if bits.get("ALL") else []).append("REPAIR")
    (s if bits.get("FLIP") and bits.get("UNIQUE") else w if bits.get("FLIP") else []).append("FLIP")
    if bits.get("EDIT"): s.append("KIND")
    if bits.get("MOVES"): w.append("FLOW")
    return s, w
