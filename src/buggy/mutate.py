# SPDX-License-Identifier: AGPL-3.0-or-later
"""The MUTATION lane's body: mutants of a candidate line, run against the tests that matter, eight bits.

The law (mutation.py, laws/mutation.c) reads one byte per line; this is where the byte comes from. The
project is copied once — no .git, no virtualenvs, no node_modules — every mutant is written into the copy
and the file restored byte-exact after each run, and the user's tree is never touched. Which tests run
against a mutant is known from the per-test coverage the locator already has: the failing tests, and a
bounded sample of the passing tests that execute the line. Never the whole suite.

Mutants are made mechanically, one per applicable operator, none by judgement. A line whose mutants the
budget cut is unmeasured: all bits 0, vetoed by the law. Silence is not innocence."""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .mutation import BITS

_REL = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
_ADJ = {ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
_ARITH = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%"}
_SIMPLE = (ast.Expr, ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Return, ast.Raise, ast.Delete, ast.Assert,
           ast.Global, ast.Nonlocal, ast.Import, ast.ImportFrom, ast.Continue, ast.Break)
_SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".buggy", ".fluidfix", "dist",
         "build", ".mypy_cache", ".ruff_cache", ".tox", ".nox", ".idea", ".coverage"}
_FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+?)(?: - .*)?$", re.M)


@dataclass
class Mutant:
    kind: str          # relational | arithmetic | boundary | boolean | constant | return | deletion
    edit: bool         # everything but a deletion
    line: str          # the whole new source line
    describe: str      # "> → >="


def _splice(line: str, node, new_text: str) -> str:
    b = line.encode("utf-8")
    return (b[:node.col_offset] + new_text.encode("utf-8") + b[node.end_col_offset:]).decode("utf-8")


def mutants_of(src: str, lineno: int, per_line: int = 6) -> list[Mutant]:
    """Every mutant of one line, in a fixed order, at most `per_line` — the deletion always among them."""
    lines = src.split("\n")
    if lineno < 1 or lineno > len(lines):
        return []
    line = lines[lineno - 1]
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    nodes = [n for n in ast.walk(tree)
             if getattr(n, "lineno", None) == lineno and getattr(n, "end_lineno", None) == lineno
             and getattr(n, "end_col_offset", None) is not None]
    nodes.sort(key=lambda n: (n.col_offset, -(n.end_col_offset - n.col_offset)))
    out, seen = [], {line}

    def add(kind, edit, new_line, desc):
        if new_line not in seen:
            seen.add(new_line); out.append(Mutant(kind, edit, new_line, desc))

    for n in nodes:                                                  # relational: the adjacent op first
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and type(n.ops[0]) in _REL:
            cur = type(n.ops[0]); order = [_ADJ[cur]] + [o for o in _REL if o not in (cur, _ADJ[cur])]
            for op in order[:3]:
                m = ast.Compare(left=n.left, ops=[op()], comparators=n.comparators)
                add("relational", True, _splice(line, n, ast.unparse(m)), f"{_REL[cur]} → {_REL[op]}")
    for n in nodes:                                                  # arithmetic
        if isinstance(n, ast.BinOp) and type(n.op) in _ARITH:
            cur = type(n.op)
            for op in [o for o in _ARITH if o is not cur][:3]:
                m = ast.BinOp(left=n.left, op=op(), right=n.right)
                add("arithmetic", True, _splice(line, n, ast.unparse(m)), f"{_ARITH[cur]} → {_ARITH[op]}")
    for n in nodes:                                                  # boundary on integer literals
        if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
            v = n.value
            add("boundary", True, _splice(line, n, repr(v + 1)), f"{v} → {v + 1}")
            add("boundary", True, _splice(line, n, repr(v - 1)), f"{v} → {v - 1}")
    for n in nodes:                                                  # boolean
        if isinstance(n, ast.BoolOp):
            m = ast.BoolOp(op=ast.Or() if isinstance(n.op, ast.And) else ast.And(), values=n.values)
            add("boolean", True, _splice(line, n, ast.unparse(m)), "and ↔ or")
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            add("boolean", True, _splice(line, n, ast.unparse(n.operand)), "not x → x")
        elif isinstance(n, ast.Constant) and isinstance(n.value, bool):
            add("boolean", True, _splice(line, n, repr(not n.value)), f"{n.value} → {not n.value}")
    for n in nodes:                                                  # constant
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value:
            add("constant", True, _splice(line, n, '""'), 'str → ""')
        elif isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool) and n.value not in (0, 1):
            add("constant", True, _splice(line, n, "0"), f"{n.value} → 0")
    stmts = [n for n in nodes if isinstance(n, ast.stmt)]
    for n in stmts:                                                  # return
        if isinstance(n, ast.Return) and n.value is not None and not (isinstance(n.value, ast.Constant) and n.value.value is None):
            add("return", True, _splice(line, n, "return None"), "return expr → return None")
    deletion = None
    simple = [n for n in stmts if isinstance(n, _SIMPLE)]
    if len(simple) == 1:                                             # deletion: a simple statement alone on its line
        deletion = Mutant("deletion", False, _splice(line, simple[0], "pass"), "statement → pass")
    if deletion is not None and deletion.line not in seen:
        out = out[:per_line - 1] + [deletion]
    return out[:per_line]


def _section(out: str, tid: str) -> str:
    name = tid.split("::")[-1].split("[")[0]
    heads = [m for m in re.finditer(r"^_{3,} .+ _{3,}$", out, re.M)]
    mine = [m for m in heads if name in m.group(0)]
    if not mine:
        return ""
    start = mine[0].start(); later = [m.start() for m in heads if m.start() > start]
    return out[start:later[0] if later else len(out)]


def signature(out: str, tid: str) -> str:
    """What the judged test's failure looks like: the E-lines and the last location. Addresses normalised."""
    sec = _section(out, tid)
    e = [l.strip() for l in sec.splitlines() if l.startswith("E ")][:6]
    loc = re.findall(r"^(\S+\.py):(\d+): (\w+)", sec, re.M)
    sig = "\n".join(e) + ("\n" + ":".join(loc[-1]) if loc else "")
    return re.sub(r"0x[0-9a-fA-F]+", "0x", sig)


def _run_to_file(cmd: list, cwd, env: dict, timeout: int) -> tuple:
    """Run a test process with its output in a FILE, not a pipe, in its own process group.

    A test can spawn something that outlives pytest and inherits the pipe; `subprocess.run(capture_output)`
    then waits on the pipe forever — a Mealie run sat 26 minutes in select() with no child alive
    (2026-09-24). A file has no such wait, and on timeout the whole group is killed."""
    import signal
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as fh:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True)
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                p.kill()
            p.wait()
            return None, "TIMEOUT"
        fh.seek(0)
        return rc, fh.read()


class Lab:
    """A copy of the project where mutants are tried. The copy's own code comes first on PYTHONPATH."""

    def __init__(self, root: str, python: str, extra_args=None, timeout: int = 180):
        self.root = str(Path(root).resolve()); self.python = python
        self.extra = list(extra_args or []); self.timeout = timeout; self.runs = 0
        self.dir = Path(tempfile.mkdtemp(prefix="buggy-lab-")); self.copy = self.dir / "r"
        shutil.copytree(self.root, self.copy, symlinks=True,
                        ignore=lambda d, names: [n for n in names if n in _SKIP or n.endswith(".egg-info")])

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run(self, ids: list) -> tuple[dict, str]:
        """{id: pass|fail|error} and the output. A run that cannot collect marks every id error."""
        pp = ([str(self.copy / "src")] if (self.copy / "src").is_dir() else []) + [str(self.copy)]
        if os.environ.get("PYTHONPATH"):
            pp.append(os.environ["PYTHONPATH"])
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": os.pathsep.join(pp)}
        cmd = [self.python, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-header", "-W", "default",
               "--tb=short", "-rfE", *self.extra, *ids]
        rc, out = _run_to_file(cmd, self.copy, env, self.timeout)
        self.runs += 1
        if rc is None:
            return {i: "error" for i in ids}, "TIMEOUT"
        if rc not in (0, 1):
            return {i: "error" for i in ids}, out
        failed = set(_FAILED.findall(out))
        return {i: ("fail" if any(f == i or f.startswith(i + "[") for f in failed) else "pass") for i in ids}, out


def line_bits(lab: "Lab", rel: str, ln: int, ms: list, ids: list, failing_all: list, judged: str,
              base_sig: str) -> tuple[dict, list, int]:
    """The eight bits of ONE line from its mutants, run in `lab`. The same function serves the single lane
    and every hive worker, so the bits cannot differ by who measured them. Returns (bits, repairs, ran)."""
    path = lab.copy / rel
    src = path.read_text(encoding="utf-8"); lines = src.split("\n")
    fails = set(failing_all); passing = [t for t in ids if t not in fails]
    b = {k: 0 for k in BITS}; ran = 0; broke_every = True; any_change = False; repairs = []
    for m in ms:
        two = list(lines); two[ln - 1] = m.line
        path.write_text("\n".join(two), encoding="utf-8")
        try:
            res, mout = lab.run(ids)
        finally:
            path.write_text(src, encoding="utf-8")
        ran += 1
        if all(v == "error" for v in res.values()):
            b["MOVES"] = 1; any_change = True              # raised where the original did not: a changed outcome
            continue                                        # and nothing passed, so it broke
        jg = res.get(judged) == "pass"
        allg = all(res.get(t) == "pass" for t in failing_all)
        broke = any(res.get(t) != "pass" for t in passing)
        if jg:
            b["FLIP"] = 1; any_change = True
            if m.edit:
                b["EDIT"] = 1
        if allg:
            b["ALL"] = 1
        if allg and not broke:
            b["CLEAN"] = 1
            repairs.append({"file": rel, "line": ln, "was": lines[ln - 1], "now": m.line, "edit": m.describe})
        if not jg and signature(mout, judged) != base_sig:
            b["MOVES"] = 1; any_change = True
        if broke:
            any_change = True
        else:
            broke_every = False
    if ran:
        b["BREAKS"] = int(broke_every and bool(passing))
        b["SILENT"] = int(not any_change)
    return b, repairs, ran


def plan(root: str, order: list, covering: dict, failing_all: list, per_line: int, sample: int) -> list:
    """The jobs, in the presented order: (rel, line, mutants, ids). Lines with no applicable operator are
    left out — unmeasured, not silent."""
    fails = set(failing_all); jobs = []; cache = {}
    for rel, ln in order:
        if rel not in cache:
            try:
                cache[rel] = Path(root, rel).read_text(encoding="utf-8")
            except OSError:
                cache[rel] = None
        if cache[rel] is None:
            continue
        ms = mutants_of(cache[rel], ln, per_line)
        if not ms:
            continue
        passing = [t for t in covering.get((rel, ln), []) if t not in fails][:sample]
        jobs.append((rel, ln, ms, list(failing_all) + passing))
    return jobs


def _finish(results: dict, repairs: list, mutants_run: int, runs: int, t0: float, cut: int, note=None) -> dict:
    flips = [k for k, b in results.items() if b.get("FLIP")]
    if len(flips) == 1:
        results[flips[0]]["UNIQUE"] = 1
    return {"lines": results, "measured": len(results), "mutants": mutants_run, "runs": runs,
            "seconds": round(time.time() - t0, 1), "cut": cut, "repairs": repairs, "note": note}


def measure(root: str, python: str, failing_all: list, judged: str, order: list, covering: dict,
            extra_args=None, budget_mutants: int = 300, budget_s: int = 240, per_line: int = 6,
            sample: int = 3, progress=None, jobs: int = 1) -> dict:
    """The eight bits for the lines in `order`, first to last, until the budget ends.

    covering: {(rel, line): [test ids that execute it]} from the spectrum. Returns lines (bits per measured
    line), the cost (lines measured, mutants, test runs, seconds, lines cut by the budget), the repairs
    (CLEAN mutants, as source lines), and a note when nothing could be measured. With jobs > 1 the work is
    done by a hive of worker processes, each a buggy with its own copy (see hive.py); the bits are the same
    by construction and the budget is counted on assignment, so the verdict does not depend on scheduling."""
    if jobs and jobs > 1:
        from .hive import hive_measure
        return hive_measure(root, python, failing_all, judged, order, covering, extra_args, budget_mutants,
                            budget_s, per_line, sample, progress, jobs)
    tell = progress or (lambda *a: None)
    t0 = time.time()
    lab = Lab(root, python, extra_args)
    try:
        base, out = lab.run(list(failing_all))
        if base.get(judged) != "fail":
            return _finish({}, [], 0, lab.runs, t0, len(order),
                           "the project copy does not reproduce the failure, so no mutant was judged")
        base_sig = signature(out, judged)
        results, repairs, mutants_run, cut = {}, [], 0, 0
        todo = plan(root, order, covering, failing_all, per_line, sample)
        for idx, (rel, ln, ms, ids) in enumerate(todo):
            if mutants_run + len(ms) > budget_mutants or time.time() - t0 > budget_s:
                cut = len(todo) - idx; break
            tell("mutation", f"{rel}:{ln} — {len(ms)} mutants")
            b, reps, ran = line_bits(lab, rel, ln, ms, ids, failing_all, judged, base_sig)
            mutants_run += ran
            if ran:
                results[(rel, ln)] = b; repairs += reps
        return _finish(results, repairs, mutants_run, lab.runs, t0, cut)
    finally:
        lab.close()
