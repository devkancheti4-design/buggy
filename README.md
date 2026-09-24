# buggy

Your test suite went red. **buggy** tells you the line to open, the commit that broke it, and where the
failing run first parted from a passing one. No model, no tokens, no network. It runs your suite once
under per-test coverage, reads the evidence, and lets two integer laws rule.

```
RED — 1 failing: tests/integration_tests/user_tests/test_user_login.py::test_user_lockout_after_bad_attemps
root cause, by lanes of evidence agreeing:
  1. mealie/core/security/providers/credentials_provider.py:48   if user.login_attemps > settings.SECURITY_MAX_LOGIN_ATTEMPTS
       cause  7/15  [executed, spectrum 0.71 (ef 1, ep 1), recent, when-commit 92ef083]
  2. mealie/core/security/providers/credentials_provider.py:41   if user.login_attemps > settings.SECURITY_MAX_LOGIN_ATTEMPTS
       cause  7/15  [executed, spectrum 0.08 (ef 1, ep 160), recent, when-commit 92ef083]
when: 92ef0835 "credentials: tidy the lockout comparisons" introduced the failure (bisect, 6 test runs)
```

That is a real 41,000-line FastAPI project (Mealie), one red test whose traceback said only
`assert 200 == 423`, 294 seconds for the three lanes above, nine minutes with the mutation lane on, and the two
lines it names are exactly the two the guilty commit changed. The mutation lane names the repair as well: `>`
back to `>=` on both.

## Install

```bash
pip install buggy-cli
```

(The name `buggy` on PyPI is an unrelated 2019 placeholder; the package installs the `buggy` module and
the `buggy` command.)

Your project needs `pytest-cov` in **its own** virtualenv (buggy finds a `.venv` or `venv` beside the code
by itself; anything else, pass `--python`). Check before the first run:

```bash
buggy doctor .
```

## Use

```bash
buggy .                      # locate: WHERE, WHEN, WHY, on the failing test — one run of the suite
buggy locate . -j 6          # the hive: six worker buggys on the mutation lane (default: half the cores)
buggy locate . --no-bisect   # faster: skip the commit search
buggy locate . --open        # jump your editor to the top line
buggy icon .                 # the pixel bug: twitches while red; click it and it crawls to the line
buggy scan ~/projects        # every project folder under a workspace, watched live in the browser
buggy vscode-init .          # a "buggy: locate the bug" task; results land in the Problems pane
```

In VS Code, Cursor or Windsurf, install `vscode/buggy-0.1.0.vsix` (Extensions → ⋯ → Install from VSIX) for
the status-bar bug, the crawl through your executed lines, and the gutter mark on the ranked line.

## What it reads

- **WHERE.** Every line the failing test executed, with eight measured bits: run by every failing test,
  run by no passing test, import-time only, last touched by the commit bisect blamed, first divergence
  from a passing run, named in a traceback frame, containing a literal from the assertion, changed
  recently. The **cause law** turns the bits into a priority 0..15; 0 is a veto.
- **Where missing code belongs.** When the fix is a line that does not exist yet, no executed line is
  wrong. The **omission law** ranks where the path stopped looking: the last executed line, the frontier
  it stepped past, the function the assertion targets, lines only passing tests reach.
- **WHEN.** Bisect in a throwaway worktree, with the failing test carried into every revision. When no
  revision is green it says so: *at least as old as \<commit\> (\<date\>)*.
- **WHY.** The failing test traced through pytest against its nearest passing neighbour, to the first
  line where the paths part or a local differs.
- **What happens when the line is changed.** Coverage says which lines were there; it cannot say which
  line matters. The **mutation law** ranks lines by an experiment: each candidate is altered one operator
  at a time — relational, arithmetic, off-by-one, boolean, constant, return, deletion — in a copy of the
  project, against the failing tests and a sample of the passing tests that execute the line. Eight facts
  about what happened (did the failing test turn green, did every failing test, did any passing test turn
  red, was it an edit or a deletion, did the failure change, is this the only line that flips) become the
  rank. A mutant that turns the whole set green is reported as a one-token repair. On by default with a
  budget (`--mutants 300 --mutate-seconds 240`, `--no-mutate` to skip); off in the editor extension unless
  `buggy.mutate` is set, because it costs minutes on a large suite.
- **The hive.** The mutation lane is a swarm: one queen, `-j N` workers (default half the cores, at most
  8), each worker a buggy process with its own copy of the project. The queen hands out lines in the
  presented order and counts the budget on assignment, so *which* lines get measured never depends on
  which worker was faster, and every worker measures with the same function the single lane uses, so the
  bits cannot differ. Checked, not assumed: `examples/hive_fairness.py` runs each case both ways and
  diffs every bit and every rank. On Mealie the hive did twice the mutants in a third of the time with the
  same verdict. `--suite-jobs N` also runs the suite under pytest-xdist workers, opt-in and off by default:
  on Mealie it halved the suite and produced failures that do not exist serially, so the wrong test was
  judged. Use it only on a suite you already run under xdist.

All three laws are generated integer kernels, `src/buggy/laws/*.c`, each with an independent oracle and a
self-check; the prompts that produced them are in `docs/laws/`. No number in them is a weight: lanes are
counted, one strong lane beats any number of weak ones, and the ranking is the dense lexicographic rank
of (strong, weak). The body measures; the law rules.

## What it is worth, measured

`docs/MEASURED.md` has the tables. The short version, read straight:

- **Planted bug in a real project** (Mealie, above): the cause law puts the two changed lines at ranks 1
  and 2 and bisect names the commit; the mutation law puts the same two lines first and names the repair,
  `>` back to `>=`, on both. Easy for an engineer too; the point is that it costs nothing and runs
  unattended.
- **Eleven adversarial cases** (`examples/adversarial.py`): under the cause law 6.5/11; under the mutation
  law **9.5/11**, the guilty line first in nine. The exception is honest: an additive pipeline with a
  sum-only test, where about 80 lines each have a one-token edit that greens the suite, and the law says
  so instead of picking one.
- **35 real fixes from rich, held out** (cause law): guilty file first in 21, guilty line in the top 10 in
  12, never a candidate in 7 (omissions the failing test never ran).
- **The longest-lived real bugs found**, 8 to 12 years old, 900 to 5,000-line files, blind. Cause law:
  rank 28, 11, 20, and a miss. Mutation law on the same four: **1**, 42, **3**, and a different one-token
  repair than the maintainer's, at 400 mutants each. Where a single edit can flip the test the experiment
  finds it in a 3,600-line file; where the real fix is eight lines, no mutant flips and the cause law's
  verdict stands beside it.

So: the cause law is a free shortlist from circumstance; the mutation law is a paid experiment that turns
the shortlist into a line when a one-token repair exists. Neither replaces whoever reads next, and both
say what they measured.

## What you will get wrong setting it up

| symptom | cause | do |
|---|---|---|
| import errors on a project that is green in your shell | the suite ran under the wrong interpreter | keep a `.venv` beside the code, or pass `--python` |
| *the law could not rule — EF_ALL is unmeasured* | `pytest-cov` is not in the project's interpreter | install it there; `buggy doctor .` checks |
| *spectrum lane: no per-test coverage* on Python 3.12+ | coverage's default core credits a line to the first test only | buggy sets `COVERAGE_CORE=ctrace`; keep coverage ≥ 7.6 |
| two runs on one project, both wrong | the suite shares state (a SQLite file, a temp dir) | never run two locates on one checkout at once |
| bisect blames the commit on top | stale bytecode when file sizes match across revisions | buggy purges it; never trust `.pyc` across checkouts |
| *at least as old as …* far back in history | the test is red there because the feature did not exist yet | read the bound as a bound |
| *cannot judge: the tests could not be collected / collected no tests / internal error / exit N* | the suite did not run to a verdict | fix the suite first; buggy never reports green unless pytest exited 0 |

## What `buggy scan` exposes

The scan page listens on `127.0.0.1` only. Its source endpoint serves `.py` files inside the listed
projects and nothing else: the path is resolved, so an absolute path, `..`, or a symlink that leaves the
project is refused. Every request must carry a local `Host` header (a page rebound to your address by
DNS is refused), and a scan can only be started with a header a browser cannot attach cross-origin.
`tests/test_scan_is_confined.py` pins all four. Before 2026-09-24 an absolute `file=` read outside the
project; that is fixed.

## Layout

```
src/buggy/locate.py     the three lanes, the pool, the two regimes, the bisect step
src/buggy/cause.py      the CAUSE law (port of laws/cause.c)
src/buggy/omission.py   the OMISSION law (port of laws/omission.c)
src/buggy/mutation.py   the MUTATION law (port of laws/mutation.c)
src/buggy/mutate.py     the mutation lane's body: mutants, the project copy, the runs
src/buggy/hive.py       the queen and the workers: the same body, N copies, budget counted on assignment
src/buggy/float_icon.py the pixel bug (Tk, standard library only)
src/buggy/scan.py       the workspace scan page
vscode/                 the editor extension
examples/               the adversarial battery, the real-fix harness, the bug-age survey
```

AGPL-3.0-or-later.
