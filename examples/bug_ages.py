import json, re, subprocess
from datetime import datetime
S="/private/tmp/claude-501/-Users-kanchetidevieswar-neo/107a7e63-6bc9-4d5b-b4a5-b0d23111954f/scratchpad/repos_full"
rows=json.load(open("research/real-history-2026-09-19/tested_fixes.json"))
def sh(*a, cwd=None, t=120):
    try: return subprocess.run(a, cwd=cwd, capture_output=True, text=True, timeout=t).stdout
    except subprocess.TimeoutExpired: return ""
out=[]
for r in rows:
    repo, sha, rel = r["repo"], r["sha"], r["file"]; cwd=f"{S}/{repo}"
    d=sh("git","diff","-U0",sha+"^",sha,"--",rel, cwd=cwd)
    old=[(int(m.group(1)), int(m.group(1))+int(m.group(2) if m.group(2) is not None else 1)-1)
         for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+", d, re.M) if (m.group(2) is None or int(m.group(2))>0)]
    if not old: continue
    births=[]
    for a,b in old[:4]:
        bl=sh("git","blame","--porcelain","-L",f"{a},{b}",sha+"^","--",rel, cwd=cwd)
        for m in re.finditer(r"^([0-9a-f]{40}) \d+ \d+(?: \d+)?\n(?:(?!\n[0-9a-f]{40} ).*\n)*?committer-time (\d+)", bl, re.M):
            births.append((int(m.group(2)), m.group(1)))
    if not births: continue
    t, bsha = min(births)
    fix_t=datetime.fromisoformat(r["date"].replace("Z","+00:00")).timestamp() if "T" in r["date"] else datetime.strptime(r["date"][:10],"%Y-%m-%d").timestamp()
    size=len(sh("git","show",f"{sha}^:{rel}", cwd=cwd).split("\n"))
    out.append({"repo":repo,"sha":sha,"file":rel,"born":bsha,"born_at":datetime.fromtimestamp(t).date().isoformat(),
                "fixed_at":r["date"][:10],"years":round((fix_t-t)/86400/365.25,1),"lines":size,"subject":r["subject"],"tests":r["tests"]})
out.sort(key=lambda o:-o["years"])
json.dump(out, open(S.replace("/repos_full","")+"/bug_ages.json","w"), indent=1)
print(f"{'years':>5} {'lines':>6} {'repo':6} {'fix':8} {'born':8} file / subject")
for o in out[:16]:
    print(f"{o['years']:>5} {o['lines']:>6} {o['repo'][:6]:6} {o['sha'][:8]} {o['born'][:8]} {o['file'][-28:]}  —  {o['subject'][:46]}")
print("SURVEY_DONE", len(out))
