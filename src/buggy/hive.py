# SPDX-License-Identifier: AGPL-3.0-or-later
"""The hive: one queen, N workers, each worker a buggy with its own copy of the project.

The queen plans the jobs — one job is one line and all its mutants — in the presented order, hands them to
whichever worker is free, and counts the budget on ASSIGNMENT, so which lines get measured does not depend
on which worker was faster. Every worker measures a line with the same `line_bits` the single lane uses,
so the bits cannot differ by who measured them. UNIQUE is settled by the queen after the last result.

    python -m buggy.hive <root> <python> <extra_args json>      # a worker: jobs in on stdin, results out

A worker that dies takes only the job it held; the queen reports it and the line stays unmeasured."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict

from .mutate import Lab, Mutant, line_bits, plan, signature, _finish


def worker_main(root: str, python: str, extra_args: list) -> int:
    lab = Lab(root, python, extra_args)
    try:
        for raw in sys.stdin:
            raw = raw.strip()
            if not raw:
                continue
            job = json.loads(raw)
            ms = [Mutant(**m) for m in job["mutants"]]
            try:
                b, reps, ran = line_bits(lab, job["rel"], job["line"], ms, job["ids"], job["failing_all"],
                                         job["judged"], job["base_sig"])
                out = {"rel": job["rel"], "line": job["line"], "bits": b, "repairs": reps, "ran": ran, "runs": lab.runs}
            except Exception as e:
                out = {"rel": job["rel"], "line": job["line"], "error": f"{type(e).__name__}: {str(e)[:120]}", "runs": lab.runs}
            lab.runs = 0
            sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()
    finally:
        lab.close()
    return 0


def hive_measure(root: str, python: str, failing_all: list, judged: str, order: list, covering: dict,
                 extra_args=None, budget_mutants: int = 300, budget_s: int = 240, per_line: int = 6,
                 sample: int = 3, progress=None, jobs: int = 4) -> dict:
    tell = progress or (lambda *a: None)
    t0 = time.time()
    # the queen's own lab: the baseline, and the proof that the copy reproduces the failure
    queen = Lab(root, python, extra_args)
    try:
        base, out = queen.run(list(failing_all))
        base_runs = queen.runs
        if base.get(judged) != "fail":
            return _finish({}, [], 0, base_runs, t0, len(order),
                           "the project copy does not reproduce the failure, so no mutant was judged")
        base_sig = signature(out, judged)
    finally:
        queen.close()
    todo = plan(root, order, covering, failing_all, per_line, sample)
    jobs = max(1, min(jobs, len(todo) or 1))
    tell("hive", f"{jobs} workers, {len(todo)} lines planned, budget {budget_mutants} mutants / {budget_s} s")
    cmd = [sys.executable, "-B", "-m", "buggy.hive", root, python, json.dumps(list(extra_args or []))]
    workers = [subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, bufsize=1, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
               for _ in range(jobs)]
    lock = threading.Lock()
    state = {"next": 0, "assigned": 0, "cut": 0, "stopped": False}
    results, repairs, notes = {}, [], []
    runs = [base_runs]

    def take():
        """The next job, or None: the budget is counted here, on assignment, under the lock."""
        with lock:
            if state["stopped"] or state["next"] >= len(todo):
                return None
            rel, ln, ms, ids = todo[state["next"]]
            if state["assigned"] + len(ms) > budget_mutants or time.time() - t0 > budget_s:
                state["stopped"] = True; state["cut"] = len(todo) - state["next"]; return None
            state["next"] += 1; state["assigned"] += len(ms)
            return rel, ln, ms, ids

    def serve(w: subprocess.Popen, k: int):
        while True:
            job = take()
            if job is None:
                break
            rel, ln, ms, ids = job
            tell("mutation", f"worker {k}: {rel}:{ln} — {len(ms)} mutants")
            try:
                w.stdin.write(json.dumps({"rel": rel, "line": ln, "mutants": [asdict(m) for m in ms], "ids": ids,
                                          "failing_all": list(failing_all), "judged": judged, "base_sig": base_sig}) + "\n")
                w.stdin.flush()
                raw = w.stdout.readline()
            except (BrokenPipeError, OSError):
                raw = ""
            if not raw:
                with lock:
                    notes.append(f"worker {k} died on {rel}:{ln}; the line is unmeasured")
                break
            r = json.loads(raw)
            with lock:
                runs.append(r.get("runs", 0))
                if "error" in r:
                    notes.append(f"worker {k}: {rel}:{ln} — {r['error']}"); continue
                if r["ran"]:
                    results[(rel, ln)] = r["bits"]; repairs.extend(r["repairs"])
                state.setdefault("mutants", 0); state["mutants"] += r["ran"]

    threads = [threading.Thread(target=serve, args=(w, k), daemon=True) for k, w in enumerate(workers)]
    for t in threads: t.start()
    for t in threads: t.join()
    for w in workers:
        try:
            w.stdin.close(); w.wait(timeout=30)
        except Exception:
            w.kill()
    res = _finish(results, repairs, state.get("mutants", 0), sum(runs), t0, state["cut"],
                  "; ".join(notes) if notes else None)
    res["workers"] = jobs
    return res


if __name__ == "__main__":
    sys.exit(worker_main(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else []))
