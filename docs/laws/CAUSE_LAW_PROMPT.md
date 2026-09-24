# Superoptimizer task — the CAUSE law

A root-cause locator is ranking lines by evidence, and the body is deciding how much each piece of evidence
is worth with an `if` and a number. Find the law.

---

## The defect

`fluidnet locate` (neo/fluidnet, 2026-09-23) gathers evidence about each candidate line from several
independent sources, then ranks lines by a score the body adds up by hand:

```python
if n in frames:    lanes.append("frame");   score += 3
if literal:        lanes.append("literal"); score += 2
if n in recent:    lanes.append("recent");  score += 1
if executed:       lanes.append("executed"); score += 1
# later: first bad commit touched it  +2,   first divergence from a passing run  +2
```

Every number there is a guess. Why is a traceback frame worth 3 and the commit that introduced the failure
worth 2? Nothing says. And the sum lets several weak signals outvote one decisive one: a recently edited line
on the failing path with a literal on it (1+1+2 = 4) outranks the line the introducing commit changed (2).

The rule of this repository: **the law decides and the body only measures.** The same rule produced the
engine, ranking, SIGHT, lanes, router, PAIR and placement laws. The body's job is to measure eight facts
about a line into an integer. The law's job is to turn that integer into a priority.

## What must not be done

Do not tune weights. Do not add `if frame and bisect: score += 5`. The table below is derived from four stated
principles; the kernel must reproduce it exactly, and nothing else.

---

## The measurement the body will supply

For one candidate line, eight bits. All are measured mechanically; none is a judgement.

| bit | name | set when |
|---|---|---|
| 0 | `EF_ALL` | every failing test executes this line (per-test coverage, `ef == F`) |
| 1 | `EP_NONE` | at least one failing test and **no passing test** executes it (`ef >= 1`, `ep == 0`) |
| 2 | `IMPORT` | the line runs only at import time — it has coverage but no test context, so the spectrum cannot see it |
| 3 | `BISECT` | automated bisect converged, and `git blame` says the first bad commit last touched this line |
| 4 | `DIVERGE` | tracing the failing test beside a passing one, this is the first line where control or a value differs |
| 5 | `FRAME` | a non-test frame of the failing traceback names this line |
| 6 | `LITERAL` | a literal from the failing assertion's comparison occurs on this line |
| 7 | `RECENT` | the line changed within the last N commits of its file |

**Situation word:** `x = EF_ALL | EP_NONE<<1 | IMPORT<<2 | BISECT<<3 | DIVERGE<<4 | FRAME<<5 | LITERAL<<6 | RECENT<<7`

**Unreachable, so the law may return anything for them:** `IMPORT=1` together with any of `EF_ALL`,
`EP_NONE`, `DIVERGE`. A line with no test context has no failing or passing executions, and the tracer only
sees lines a test executes. That leaves **144 reachable values of 256.**

---

## The law to find

```
cause(x) -> priority 0..15      higher = examine first      0 = cannot be the root cause
```

The body sorts candidate lines by `cause(x)` descending, and breaks ties with the Ochiai score — a measured
number, not a decision.

### The principles that fix the table

Evidence comes from **four independent lanes**. Each lane grades a line 0, 1 (weak — consistent with the
cause) or 2 (strong — points at the cause):

| lane | strong (2) | weak (1) |
|---|---|---|
| TIME | `BISECT` — the commit that introduced the failure touched it | `RECENT` |
| SPECTRUM | `EF_ALL` and `EP_NONE` — every failing test runs it and no passing test does | `EF_ALL` alone, **or** `IMPORT` (the spectrum is blind there; unknown is scored as weak, never as strong or absent) |
| WHY | `DIVERGE` — where the failing run first departs from a passing one | — |
| SYMPTOM | `FRAME` and `LITERAL` both — two independent symptoms coincide on it | `FRAME` or `LITERAL` |

- **R0 — reachability veto.** If `EF_ALL = 0` and `IMPORT = 0`, the priority is **0** whatever else is set. A line
  that not every failing test executes cannot be the single cause of every failure. (Where failing tests fail
  for different causes, the body runs the law once per failing test; that is its job, not the law's.)
- **R1 — one strong beats any number of weak.** Otherwise, with `s` = lanes at strong and `w` = lanes at weak,
  the priority is the **dense lexicographic rank of `(s, w)`**: a line with more strong lanes always outranks one
  with fewer, however many weak lanes the other has; among equal `s`, more weak lanes rank higher.
- **R2 — monotone.** Turning on any evidence bit other than `IMPORT` never lowers the priority.
- **R3 — no lane is privileged.** Only the counts `(s, w)` matter, not which lanes supplied them.

The pairs `(s, w)` with `s + w <= 4` are fifteen, which with the veto's 0 fill exactly 0..15:

```
(s,w)  (0,0) (0,1) (0,2) (0,3) (0,4) (1,0) (1,1) (1,2) (1,3) (2,0) (2,1) (2,2) (3,0) (3,1) (4,0)
cause    1     2     3     4     5     6     7     8     9    10    11    12    13    14    15
```

(Any line R0 lets through has `SPECTRUM >= 1`, so values 1 and 5 are never produced; they are still correct.)

### Truth table — all 256 values

Row `r`, column `c` is `x = 16r + c`. `.` is unreachable — the law may return anything there.

```
x=  0..15   0  2  0  6  2  .  .  .  0  7  0 10  7  .  .  .
x= 16..31   0  7  0 10  .  .  .  .  0 11  0 13  .  .  .  .
x= 32..47   0  3  0  7  3  .  .  .  0  8  0 11  8  .  .  .
x= 48..63   0  8  0 11  .  .  .  .  0 12  0 14  .  .  .  .
x= 64..79   0  3  0  7  3  .  .  .  0  8  0 11  8  .  .  .
x= 80..95   0  8  0 11  .  .  .  .  0 12  0 14  .  .  .  .
x= 96..111  0  7  0 10  7  .  .  .  0 11  0 13 11  .  .  .
x=112..127  0 11  0 13  .  .  .  .  0 14  0 15  .  .  .  .
x=128..143  0  3  0  7  3  .  .  .  0  7  0 10  7  .  .  .
x=144..159  0  8  0 11  .  .  .  .  0 11  0 13  .  .  .  .
x=160..175  0  4  0  8  4  .  .  .  0  8  0 11  8  .  .  .
x=176..191  0  9  0 12  .  .  .  .  0 12  0 14  .  .  .  .
x=192..207  0  4  0  8  4  .  .  .  0  8  0 11  8  .  .  .
x=208..223  0  9  0 12  .  .  .  .  0 12  0 14  .  .  .  .
x=224..239  0  8  0 11  8  .  .  .  0 11  0 13 11  .  .  .
x=240..255  0 12  0 14  .  .  .  .  0 14  0 15  .  .  .  .
```

Anchors, so the table can be read against reality:

| line | x | cause |
|---|---|---|
| the `rich` segment.py bug: every failing test runs it, no passing test does, the first bad commit touched it | 11 | **10** |
| a module constant the first bad commit changed (import time) | 12 | 7 |
| a shared helper every test runs | 1 | 2 |
| a traceback frame on a line only one of two failing tests runs | 34 | 0 |

---

## Constraints

- **Branchless integer arithmetic over `x`.** No conditionals, no lookup table, same character as the existing laws —
  e.g. the engine's `act = (4 & ntzb(x-7)) + ntzb(x + (x&128))`, SIGHT's lanes of shifts and masks.
- Shifts, masks, adds, subtracts, popcount if you have it, and `ntzb` are available. Fewer operations is better.
- **Total** on 0..255 and **exact** on all 144 reachable values. Return the priority, or a value whose low 4 bits are it.

## How it will be judged

1. **Exhaustively against the table**, all 144 reachable `x`.
2. **R0–R3 re-checked by enumeration** on the kernel itself, not only on the table.
3. `fluidfix selfcheck` must still re-derive every existing law unchanged.

**What the superoptimizer does not decide:** whether this table ranks real bugs well. That is measured
separately, on 198 real single-file fixes that ship their own regression test (click, arrow, rich,
python-sortedcontainers), with the cases split into a half used for the design and a held-out half. If the
held-out half says the table is wrong, the table changes by a stated principle — never by fitting — and a
new kernel is asked for. The kernel's job is to make the ruling exact, branchless and verifiable; the real
bugs' job is to say whether the ruling is right.
