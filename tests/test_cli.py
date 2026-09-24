import json, subprocess, sys


def run(*args, cwd=None):
    return subprocess.run([sys.executable, "-m", "buggy.cli", *args], capture_output=True, text=True, cwd=cwd)


def test_version():
    assert "buggy" in run("--version").stdout


def test_doctor_reports_this_interpreter(tmp_path):
    r = run("doctor", str(tmp_path))
    assert "project interpreter" in r.stdout and "pytest: present" in r.stdout, r.stdout + r.stderr


def test_a_path_alone_means_locate(repo_factory):
    root = repo_factory("def f():\n    return 2\n", "from pkg.mod import f\n\ndef test_f():\n    assert f() == 1\n")
    r = run(str(root), "--no-bisect", "--no-trace", "--format", "vscode")
    assert r.returncode == 3 and r.stdout.startswith("pkg/mod.py:"), r.stdout + r.stderr


def test_json_and_the_editor_task(repo_factory):
    root = repo_factory("def f():\n    return 2\n", "from pkg.mod import f\n\ndef test_f():\n    assert f() == 1\n")
    d = json.loads(run("locate", str(root), "--no-bisect", "--no-trace", "--json").stdout)
    assert d["status"] == "red" and d["where"][0]["file"] == "pkg/mod.py"
    assert run("vscode-init", str(root), "--buggy", "/x/bin/buggy").returncode == 0
    t = json.load(open(root / ".vscode/tasks.json"))
    assert t["tasks"][0]["command"].startswith("/x/bin/buggy locate .")
