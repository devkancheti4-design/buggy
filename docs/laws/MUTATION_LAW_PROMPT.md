# Superoptimizer task — the MUTATION law

The CAUSE law ranks the lines a failing test executed by eight bits of circumstantial evidence. On real
bugs that is usually one bit, `EF_ALL`, and the spectrum tie-break does the ordering: on the five
longest-lived real bugs the guilty line sat at rank 28, 11, 20, 32; in a 2,000-line file of
coverage-identical lines it sat at 218 in a band of 84 the law could not tell apart. Coverage says which
lines were *there*. It cannot say which line *matters*. Find the law that ranks lines by what happens
when each one is changed.

---

## The measurement, and why it is different in kind

For every candidate line the body will make **mutants** — the same line with one thing altered — and run
tests against each. This is not more circumstantial evidence; it is an experiment on the line. A mutant
that turns the failing test green is a line whose content the outcome depends on. A mutant that turns the
whole suite green is a repair.

Mutants are made mechanically, one per applicable operator, none by judgement:

| operator | what changes |
|---|---|
| relational | `<` `<=` `>` `>=` `==` `!=`, each to each of the others |
| arithmetic | `+` `-` `*` `/` `//` `%`, each to each of the others |
| boundary | an integer literal `n` to `n-1` and `n+1` |
| boolean | `and`↔`or`, `not x`↔`x`, `True`↔`False` |
| constant | a literal to `0`, `1`, `None`, `""`, `[]` |
| return | `return expr` to `return None` |
| deletion | the statement to `pass` |

Which tests run against a mutant is known from the per-test coverage the locator already has: the failing
tests, and only the **passing tests that execute the line** (`ep` of the spectrum), never the whole
suite. A mutant that raises where the original did not is a changed outcome, not a crash of the body.
Every run is bounded; a line whose mutants the budget cut is **unmeasured**, all bits 0, and the law
vetoes it — silence is not innocence.

---

## What must not be done

Do not add `if flip: score += 10`. The body measures; the law rules — the same rule that produced the
CAUSE and OMISSION laws. No number in the body is a weight.

Do not fold this into the CAUSE law. "Which line did the failing test run" and "which line's content does
the outcome depend on" are different questions with different regimes. Three laws, side by side; the body
shows each verdict and never picks between them by a constant.

Do not let a deletion outrank an edit. Deleting a guard can make a failing assertion pass by skipping the
check that was asserting; an operator flip that makes the same test pass is a repair. The grades below say
so; the kernel must not.

---

## The measurement the body will supply

For one candidate line, one byte:

| bit | name | set when |
|---|---|---|
| 0 | `FLIP` | some mutant of this line turns the **judged** failing test green |
| 1 | `ALL` | some single mutant turns **every** failing test green |
| 2 | `CLEAN` | some single mutant turns every failing test green and turns **no** covering passing test red — a repair candidate, handed to the certification gates as such |
| 3 | `EDIT` | a flipping mutant is an **edit** (relational, arithmetic, boundary, boolean, constant, return), not a deletion |
| 4 | `MOVES` | some mutant **changes** the judged failing test's failure — a different value in the assertion, a different exception, a different line — without turning it green: the line's content reaches the failure |
| 5 | `UNIQUE` | this is the **only** line in the pool with `FLIP` — measured once per run over the whole pool |
| 6 | `BREAKS` | **every** mutant of this line that ran turned some covering passing test red — the line is load-bearing for correct behaviour and no edit of it helped (the counter-evidence of Moon et al., MUSE) |
| 7 | `SILENT` | every mutant that ran changed nothing anywhere — equivalent mutants, or a line the failing path never reaches with these inputs |

**Situation word** `x = bit0 | bit1<<1 | … | bit7<<7`, 256 values.

Reachability: `CLEAN` ⇒ `ALL` ⇒ `FLIP`. `EDIT` ⇒ `FLIP`. `UNIQUE` ⇒ `FLIP`. `SILENT` excludes `FLIP`,
`MOVES` and `BREAKS`. `CLEAN` excludes `BREAKS` (the clean mutant broke nothing). **45 words are
reachable**; the law may do anything on the rest, provided it still lands in 0..15.

---

## The law to find

```
mutation(x) -> 0..15    higher = examine first    0 = no mutant of this line touched the failure
```

**The principle**, in the same form as the CAUSE and OMISSION laws so the three are comparable: evidence
comes in lanes, each lane graded strong / weak / silent from its bits, and the priority is the dense
lexicographic rank of (strong count, weak count). One strong beats any number of weak because the rank
says so.

| lane | strong | weak |
|---|---|---|
| **REPAIR** — does a mutant fix it | `CLEAN` | `ALL` (without `CLEAN`) |
| **FLIP** — does the judged failure depend on this line | `FLIP` and `UNIQUE` | `FLIP` |
| **KIND** — is the flip an edit or an amputation | `EDIT` | — |
| **FLOW** — does the line's content reach the failure | — | `MOVES` |

`BREAKS` is not a lane. It is the regime bit, as `RAISED` is in the OMISSION law, and it is a **shift**:
with `BREAKS` = 1 the priority is halved (floor), because a line whose every alteration breaks correct
behaviour is more likely correct code the failing path merely runs through. A faulty line can also be
load-bearing, so `BREAKS` shifts and never vetoes.

`SILENT` is not a lane either. It exists so the body can tell "measured and nothing" from "not measured";
to the law both are R0.

**R0, the veto:** a line with neither `FLIP` nor `MOVES` is 0. No mutant of it touched the failure.
**R1** dense lexicographic rank of (strong, weak) among non-vetoed words, within a regime.
**R2** monotone in every evidence bit (adding evidence never lowers the rank), `BREAKS` excepted.
**R3** only the counts matter: no lane is privileged.
**R4** `KIND` has no weak grade and `FLOW` has no strong grade, so rank 15 is unreachable, as it is in the
other two laws and for the same structural reason; the top attainable rank is 14 at (3, 1). State it.

---

## Anchors — real cases, held out from the design

| word | case | want |
|---|---|---|
| `FLIP`+`ALL`+`CLEAN`+`EDIT` (x=15) | mealie `credentials_provider.py:48`: `>` back to `>=` turns the lockout test green and breaks nothing; line 41 does the same, so neither is `UNIQUE` | **11** — REPAIR strong, KIND strong, FLIP weak |
| the same plus `UNIQUE` (x=63) | the 2,000-line file: coverage cannot separate the lines, and exactly one of them flips | **14** — the top attainable; the case this law exists for |
| `FLIP`+`EDIT`+`UNIQUE`, no `ALL` (x=41) | two failing tests with different causes; an edit of this line turns the judged one green and not the other | **10** — two strong, no weak |
| `MOVES` alone (x=16) | a constant whose alteration changes the wrong value in the assertion but does not fix it | **2** — one weak; ranked, low |
| `FLIP`+`BREAKS`, deletion only (x=65) | deleting the line makes the assertion pass and breaks passing tests; every edit also breaks them | **1** — one weak, halved |
| `BREAKS` alone (x=64) | a shared helper every test runs; every mutant breaks something, none flips | **0** — R0 |
| `SILENT` (x=128) | a logging line | **0** — R0 |

---

## How it will be judged

1. **Exhaustively against the table**, every reachable word, plus R0–R4 by enumeration on the kernel,
   with an independent branchy oracle that shares no expression with a lane, as in `laws/cause.c` and
   `laws/omission.c`.
2. **On the cases the other laws could not separate.** The adversarial battery (`examples/adversarial.py`)
   and the five long-lived real bugs (`examples/longlived.py`): report the guilty line's rank under this
   law beside its rank under the CAUSE law, and the number of mutants run. The 2,000-line case must move
   from rank 218 to the top; if it does not, the table is wrong and this document changes by a stated
   principle before a new kernel is asked for.
3. **On real fixes, held out.** `examples/real_bugs.py` logs every candidate's bits; the rich and click
   sets are split in half, the table designed on one half and judged on the other. Report top-1, top-5,
   top-10 under this law, under the CAUSE law, and with the two shown side by side.
4. **Cost, stated.** Mutants per line, tests per mutant, seconds per case, beside the CAUSE law's cost on
   the same case. The body's budget is a measurement, not a weight, and it is reported with every verdict.
5. **The CAUSE and OMISSION laws' verdicts stand.** Showing three columns must not move either of the
   others; `tests/test_cause_law.py` and `tests/test_omission_law.py` pass unchanged.

---

## Why a law rather than a patch

Coverage is testimony: the line was present when the crime happened. Mutation is an experiment: change
the line and see whether the crime still happens. Every localizer that has beaten plain spectrum ranking
in the literature did it by adding the experiment. What none of them did was state, in a form that can be
checked exhaustively and read by a maintainer, how the experiment's outcomes rank against each other.
That is the law: eight measured facts about what happened when the line was changed, four lanes, one
regime, and a rank nobody chose by hand.
