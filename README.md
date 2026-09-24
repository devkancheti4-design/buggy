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
`assert 200 == 423`, 294 seconds, and the two lines it names are exactly the two the guilty commit changed.

## Install

```bash
pip install git+https://github.com/devkancheti4-design/buggy
```

Your project needs `pytest-cov` in **its own** virtualenv (buggy finds a `.venv` or `venv` beside the code
by itself; anything else, pass `--python`). Check before the first run:

```bash
buggy doctor .
```

## Use

```bash
buggy .                      # locate: WHERE, WHEN, WHY, on the failing test — one run of the suite
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

Both laws are generated integer kernels, `src/buggy/laws/*.c`, each with an independent oracle and a
self-check; the prompts that produced them are in `docs/laws/`. No number in them is a weight: lanes are
counted, one strong lane beats any number of weak ones, and the ranking is the dense lexicographic rank
of (strong, weak). The body measures; the law rules.

## What it is worth, measured

`docs/MEASURED.md` has the tables. The short version, read straight:

- **Planted bug in a real project** (Mealie, above): the two changed lines at ranks 1 and 2, the commit
  named. Easy for an engineer too; the point is that it costs nothing and runs unattended.
- **Ten adversarial cases** (`examples/adversarial.py`): exact on 4, top 5 on 5, one genuine weakness — a
  2,000-line file of coverage-identical lines, where nothing distinguishes them and the guilty line sits
  around rank 220. Score 6.5/10.
- **35 real fixes from rich, held out**: guilty file first in 21, guilty line in the top 10 in 12, never a
  candidate in 7 (omissions the failing test never ran).
- **The five longest-lived real bugs found**, 8 to 12 years old, 900 to 5,000-line files, blind: the
  guilty line at rank 28, 11, 20 and 32 of the executed lines, the pure omission missed. On bugs like
  these only one bit fires and the spectrum does the ordering: a reading list, not the line.

So: when several lanes agree it is exact; when they do not it hands you a short list. It is a pre-filter
you run first because it is free, not a replacement for whoever reads next.

## What you will get wrong setting it up

| symptom | cause | do |
|---|---|---|
| import errors on a project that is green in your shell | the suite ran under the wrong interpreter | keep a `.venv` beside the code, or pass `--python` |
| *the law could not rule — EF_ALL is unmeasured* | `pytest-cov` is not in the project's interpreter | install it there; `buggy doctor .` checks |
| *spectrum lane: no per-test coverage* on Python 3.12+ | coverage's default core credits a line to the first test only | buggy sets `COVERAGE_CORE=ctrace`; keep coverage ≥ 7.6 |
| two runs on one project, both wrong | the suite shares state (a SQLite file, a temp dir) | never run two locates on one checkout at once |
| bisect blames the commit on top | stale bytecode when file sizes match across revisions | buggy purges it; never trust `.pyc` across checkouts |
| *at least as old as …* far back in history | the test is red there because the feature did not exist yet | read the bound as a bound |

## Layout

```
src/buggy/locate.py     the three lanes, the pool, the two regimes, the bisect step
src/buggy/cause.py      the CAUSE law (port of laws/cause.c)
src/buggy/omission.py   the OMISSION law (port of laws/omission.c)
src/buggy/float_icon.py the pixel bug (Tk, standard library only)
src/buggy/scan.py       the workspace scan page
vscode/                 the editor extension
examples/               the adversarial battery, the real-fix harness, the bug-age survey
```

AGPL-3.0-or-later.
