# SPDX-License-Identifier: AGPL-3.0-or-later
"""buggy — locate the root cause of a red suite; the pixel bug; a workspace scan; an editor task."""
from __future__ import annotations

import argparse
import os
import json
import sys
from pathlib import Path

from . import __version__


def cmd_locate(a) -> int:
    from .locate import locate, project_python
    L = locate(a.root, python=a.python or project_python(a.root), good=a.good, bisect=not a.no_bisect,
               trace=not a.no_trace)
    if a.json:
        from dataclasses import asdict
        d = asdict(L); d.pop("_vetoed_list", None); print(json.dumps(d, indent=1))
    elif a.format == "vscode":
        # one line per finding, in the shape a problem matcher reads:  file:line: message
        for f in L.where[:5]:
            print(f"{f.file}:{f.line}: cause {f.rank}/15 — {', '.join(f.lanes)}")
        if L.status != "red":
            print(f"# {L.render()}")
    else:
        print(L.render())
    if a.open and L.status == "red" and L.where:
        import shutil, subprocess as sp
        ed = a.editor or os.environ.get("BUGGY_EDITOR") or next((e for e in ("code", "cursor", "windsurf") if shutil.which(e)), None)
        if ed:
            sp.Popen([ed, "-g", f"{Path(a.root, L.where[0].file)}:{L.where[0].line}"])
        else:
            print("(no editor command found to --open with; set BUGGY_EDITOR)")
    return {"green": 0, "red": 3}.get(L.status, 1)


def cmd_vscode_init(a) -> int:
    """Drop a task into a repo: run it and the guilty line lands in the Problems pane, no extension needed."""
    d = Path(a.root) / ".vscode"; d.mkdir(exist_ok=True); tf = d / "tasks.json"
    task = {"label": "buggy: locate the bug", "type": "shell",
            "command": f"{a.buggy} locate . --no-bisect --format vscode",
            "presentation": {"reveal": "always", "panel": "dedicated"},
            "problemMatcher": {"owner": "buggy", "fileLocation": ["relative", "${workspaceFolder}"],
                               "severity": "error",
                               "pattern": {"regexp": "^([^:#][^:]*):(\\d+): (.*)$", "file": 1, "line": 2, "message": 3}}}
    if tf.exists():
        try:
            cur = json.loads(tf.read_text())
        except json.JSONDecodeError:
            print(f"{tf} exists and is not valid JSON; add this task by hand:\n{json.dumps(task, indent=2)}"); return 1
        cur.setdefault("tasks", [])
        cur["tasks"] = [t for t in cur["tasks"] if t.get("label") != task["label"]] + [task]
    else:
        cur = {"version": "2.0.0", "tasks": [task]}
    tf.write_text(json.dumps(cur, indent=2) + "\n")
    print(f"wrote {tf}\n  Terminal → Run Task → \"buggy: locate the bug\"  — the root cause appears in Problems.")
    return 0


def _tk_python() -> str | None:
    import shutil, subprocess as sp
    cands = [sys.executable, "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
             "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3", "/usr/bin/python3",
             shutil.which("python3") or ""]
    for c in cands:
        if c and sp.run([c, "-c", "import tkinter"], capture_output=True).returncode == 0:
            return c
    return None


def cmd_icon(a) -> int:
    """Keep .buggy/locate.json fresh — on every source change, and every --interval seconds while red —
    and show it as the pixel bug under whichever Python here has Tk."""
    import subprocess as sp, time as _t
    from .locate import locate, project_python
    home = Path.home() / ".buggy"; home.mkdir(exist_ok=True)
    target_file, scan_now = home / "target", home / "scan-now"
    root = str(Path(a.root).resolve()); target_file.write_text(root)
    fx = Path(root, ".buggy"); fx.mkdir(exist_ok=True)
    badge = None
    if not a.headless:
        py = _tk_python()
        if py:
            badge = sp.Popen([py, str(Path(__file__).with_name("float_icon.py")), root])
            print(f"buggy is up (Tk via {py}) — bottom-right of your screen. click: crawl to the root cause · "
                  "drag onto a Finder window: scan that folder · double-click: pick a folder · Ctrl-C here: quit")
        else:
            print("no Python with Tk found here; running headless — read .buggy/locate.json")
    def snapshot():
        out = {}
        for p in Path(root).rglob("*.py"):
            if any(part in (".venv", "venv", ".git", "__pycache__", ".buggy") for part in p.relative_to(root).parts):
                continue
            try: out[str(p)] = p.stat().st_mtime_ns
            except OSError: pass
        return out
    last, red = snapshot(), False
    print(f"watching {root} — drop the icon on a Finder window to switch folders; Ctrl-C to stop")
    try:
        while True:
            want = target_file.read_text().strip() if target_file.exists() else root
            forced = scan_now.exists()
            if (want and want != root and Path(want).is_dir()) or forced:
                scan_now.unlink(missing_ok=True)
                if want != root:
                    root = want; fx = Path(root, ".buggy"); fx.mkdir(exist_ok=True)
                    print(f"[{_t.strftime('%H:%M:%S')}] now watching {root}")
                last = None                                # force a locate on the new target
            now = snapshot()
            if now != last or (red and a.interval):
                last = now
                (fx / "locating").touch()
                try:
                    L = locate(root, python=a.python or project_python(root), bisect=not a.no_bisect)
                    red = L.status == "red"
                    print(f"[{_t.strftime('%H:%M:%S')}] {L.status}" + (f": {L.where[0].file}:{L.where[0].line} ({len(L.where[0].lanes)} lanes)" if red and L.where else ""))
                finally:
                    (fx / "locating").unlink(missing_ok=True)
            if badge is not None and badge.poll() is not None:
                relaunch = getattr(a, "_relaunch", 0)
                if relaunch < 5:
                    a._relaunch = relaunch + 1
                    print(f"[{_t.strftime('%H:%M:%S')}] the icon closed (exit {badge.returncode}); bringing it back — "
                          f"see ~/.buggy/icon.log if it keeps happening")
                    badge = sp.Popen([py, str(Path(__file__).with_name("float_icon.py")), root]); _t.sleep(1.5)
                else:
                    print("the icon closed five times; stopping — ~/.buggy/icon.log has the reason"); break
            _t.sleep(a.interval if red else 1.0)
    except KeyboardInterrupt:
        print("\nbuggy stopped (Ctrl-C)")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"buggy stopped on an error: {type(e).__name__}: {e}")
    finally:
        if badge is not None and badge.poll() is None:
            badge.terminate()
    return 0


def cmd_scan(a) -> int:
    from .scan import serve
    return serve(a.workspace, port=a.port, python=a.python, bisect=not a.no_bisect)


def cmd_doctor(a) -> int:
    """Can this install locate here? The project's interpreter, pytest and pytest-cov in it, git, Tk."""
    import shutil, subprocess as sp
    from .locate import project_python
    ok = True
    py = a.python or project_python(a.root)
    print(f"project interpreter: {py}" + ("" if a.python or py != sys.executable else "  (no .venv here; buggy's own)"))
    for mod, why in (("pytest", "runs the suite"), ("pytest_cov", "per-test coverage — the spectrum lane; without it the law cannot rule")):
        r = sp.run([py, "-c", f"import {mod}"], capture_output=True)
        print(f"  {mod}: {'present' if r.returncode == 0 else 'MISSING — install it into that interpreter'}  ({why})")
        ok = ok and r.returncode == 0
    print(f"git: {'present' if shutil.which('git') else 'MISSING — the WHEN lane and the recency bit need it'}")
    print(f"Tk for the pixel bug: {_tk_python() or 'none found — `buggy icon` runs headless'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # `buggy .` and `buggy path/to/repo` mean locate
    if argv and argv[0] not in SUBS and not argv[0].startswith("-") and Path(argv[0]).is_dir():
        argv = ["locate", *argv]
    p = argparse.ArgumentParser(prog="buggy", description=__doc__)
    p.add_argument("--version", action="version", version=f"buggy {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("locate", help="root cause of a red suite: WHERE (file, line), WHEN (commit, by "
                                      "bisect), WHY (first divergence from a passing test)")
    l.add_argument("root", nargs="?", default="."); l.add_argument("--good", help="a revision known green (else searched)")
    l.add_argument("--no-bisect", action="store_true"); l.add_argument("--no-trace", action="store_true")
    l.add_argument("--python", help="the interpreter that runs the suite (default: the project's .venv)")
    l.add_argument("--json", action="store_true")
    l.add_argument("--format", choices=["text", "vscode"], default="text", help="vscode: file:line: message per finding")
    l.add_argument("--open", action="store_true", help="jump your editor to the top line (code/cursor/windsurf, or BUGGY_EDITOR)")
    l.add_argument("--editor"); l.set_defaults(fn=cmd_locate)

    for name in ("icon", "bug"):
        fl = sub.add_parser(name, help="the pixel bug: twitches while the suite is red; click it and it crawls "
                                       "your file to the root cause; drop it on a Finder window to scan that folder"
                                       + ("" if name == "icon" else " (alias of icon)"))
        fl.add_argument("root", nargs="?", default=".")
        fl.add_argument("--interval", type=float, default=15.0, help="re-locate this often while red (default 15s)")
        fl.add_argument("--no-bisect", action="store_true"); fl.add_argument("--headless", action="store_true")
        fl.add_argument("--python"); fl.set_defaults(fn=cmd_icon)

    sc = sub.add_parser("scan", help="a workspace of project folders, scanned one after another, watched live "
                                      "in the browser: the ladybug follows real scan events")
    sc.add_argument("workspace"); sc.add_argument("--port", type=int, default=7777)
    sc.add_argument("--no-bisect", action="store_true"); sc.add_argument("--python"); sc.set_defaults(fn=cmd_scan)

    vi = sub.add_parser("vscode-init", help="add a 'buggy: locate the bug' task with a problem matcher to a repo's .vscode/tasks.json")
    vi.add_argument("root", nargs="?", default="."); vi.add_argument("--buggy", default="buggy", help="how the task should invoke buggy")
    vi.set_defaults(fn=cmd_vscode_init)

    dr = sub.add_parser("doctor", help="can this install locate in this project?")
    dr.add_argument("root", nargs="?", default="."); dr.add_argument("--python"); dr.set_defaults(fn=cmd_doctor)
    a = p.parse_args(argv)
    return a.fn(a)


SUBS = {"locate", "icon", "bug", "scan", "vscode-init", "doctor"}


if __name__ == "__main__":
    sys.exit(main())
