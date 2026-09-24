# buggy for VS Code, Cursor and Windsurf

A pixel bug in the status bar. It twitches when your suite is red. Click it and the bug crawls your file —
down the lines the failing test actually executed — and stops on the line the CAUSE law ranked first, with
the verdict on hover: cause N/15, which lanes were strong and which weak, the commit that introduced it,
where the failing run parts from a passing one. The line also lands in the Problems pane. No model.

Commands: **buggy: locate the bug** · **buggy: crawl to the bug** · **buggy: scan every workspace
folder**. Saving a `.py` file locates again (`buggy.onSave`).

Needs `buggy` installed (`pip install buggy` from the repository); set `buggy.path` to a venv's
`bin/buggy` if it is not on PATH. The target must have a `pytest` suite and `pytest-cov`.

Install from a .vsix: `code --install-extension buggy-0.2.0.vsix` (also `cursor`, `windsurf`).
