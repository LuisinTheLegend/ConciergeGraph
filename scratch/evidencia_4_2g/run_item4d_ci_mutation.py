import json
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
MAIN_PATH = REPO_ROOT / "main.py"
REPO = "LuisinTheLegend/ConciergeGraph"
BRANCH = "ci-mutacao-4-2g"


def run_cmd(cmd):
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
    return res.returncode, out.strip()


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "GrafoConcierge-Audit-4.2g",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    orig_bytes = MAIN_PATH.read_bytes()
    mut_sha = None
    lines = []
    lines.append("=== ITEM 4d: MUTACAO NO CI WINDOWS (BRANCH DESCARTAVEL ci-mutacao-4-2g) ===")
    lines.append("Mutacao aplicada: remocao de `os.dup2(nul, 0)` em `decouple_stdin_from_fd0()` de `main.py`")
    lines.append("")

    try:
        # 1. Create branch ci-mutacao-4-2g
        rc, out = run_cmd(["git", "checkout", "-b", BRANCH])
        if rc != 0:
            raise RuntimeError(f"git checkout -b failed: {out}")

        # 2. Remove os.dup2(nul, 0) in main.py preserving CRLF
        text = orig_bytes.decode("utf-8")
        target = "        os.dup2(nul, 0)\r\n"
        assert target in text, "Target `os.dup2(nul, 0)` not found in main.py"
        mut_text = text.replace(target, "", 1)
        MAIN_PATH.write_bytes(mut_text.encode("utf-8"))

        _, diff_mut = run_cmd(["git", "diff", "--no-color", "--", "main.py"])
        lines.append("=== GIT DIFF DA MUTACAO NA BRANCH ci-mutacao-4-2g ===")
        lines.append(diff_mut)
        lines.append("")

        # 3. Commit and push ci-mutacao-4-2g
        run_cmd(["git", "add", "main.py"])
        rc, out = run_cmd(["git", "commit", "-m", "test(ci-mutacao): remove os.dup2(nul, 0) para testar D1 no runner Windows (4.2g Item 4d)"])
        if rc != 0:
            raise RuntimeError(f"git commit failed: {out}")

        _, mut_sha = run_cmd(["git", "rev-parse", "HEAD"])
        print(f"Mutation commit SHA on {BRANCH}: {mut_sha}", flush=True)

        rc, push_out = run_cmd(["git", "push", "-u", "origin", BRANCH])
        if rc != 0:
            raise RuntimeError(f"git push failed: {push_out}")
        print(f"Pushed {BRANCH} ({mut_sha[:7]}) to origin.", flush=True)

        # 4. Poll GitHub Actions for workflow run on mut_sha
        run_obj = None
        t0 = time.time()
        while time.time() - t0 < 900:  # up to 15 min
            time.sleep(15)
            try:
                runs_data = fetch_json(f"https://api.github.com/repos/{REPO}/actions/runs?per_page=10")
                runs = [
                    r for r in runs_data.get("workflow_runs", [])
                    if r.get("head_sha") == mut_sha
                    and "Windows Stdin" in (r.get("name") or "")
                ]
                if runs:
                    r = runs[0]
                    print(
                        f"[{int(time.time() - t0)}s] Run {r['id']} status={r.get('status')} conclusion={r.get('conclusion')}",
                        flush=True,
                    )
                    if r.get("status") == "completed":
                        run_obj = r
                        break
                else:
                    print(f"[{int(time.time() - t0)}s] Waiting for run on {mut_sha[:7]} to appear...", flush=True)
            except Exception as e:
                print(f"Poll warning: {e}", flush=True)

        lines.append("=== RESULTADO DO WORKFLOW NO GITHUB ACTIONS (MUTACAO SEM os.dup2(nul, 0)) ===")
        if run_obj is None:
            lines.append(f"Timeout aguardando workflow para commit {mut_sha}")
        else:
            run_id = run_obj["id"]
            lines.append(f"Run ID: {run_id}")
            lines.append(f"Workflow: {run_obj.get('name')}")
            lines.append(f"Branch: {run_obj.get('head_branch')}")
            lines.append(f"Head SHA: {run_obj.get('head_sha')}")
            lines.append(f"Status: {run_obj.get('status')} | Conclusion: {run_obj.get('conclusion')}")
            lines.append(f"URL: {run_obj.get('html_url')}")
            lines.append("")
            jobs_data = fetch_json(f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs")
            lines.append("Jobs da Matriz:")
            for j in jobs_data.get("jobs", []):
                lines.append(
                    f"  - Job: {j.get('name')} | status={j.get('status')} | "
                    f"conclusion={j.get('conclusion')} | started={j.get('started_at')} | "
                    f"completed={j.get('completed_at')}"
                )
                for st in j.get("steps", []):
                    lines.append(
                        f"      step [{st.get('number')}] {st.get('name')}: "
                        f"status={st.get('status')}, conclusion={st.get('conclusion')}"
                    )
            lines.append("")

    finally:
        # 5. Always return to main and delete branch ci-mutacao-4-2g (remote and local)
        print("Returning to main and deleting disposable branch...", flush=True)
        run_cmd(["git", "checkout", "main"])
        MAIN_PATH.write_bytes(orig_bytes)
        _, del_rem = run_cmd(["git", "push", "origin", "--delete", BRANCH])
        _, del_loc = run_cmd(["git", "branch", "-D", BRANCH])
        _, cur_branch = run_cmd(["git", "branch", "--show-current"])
        _, cur_head = run_cmd(["git", "rev-parse", "HEAD"])
        lines.append("=== LIMPEZA DA BRANCH DESCARTAVEL ===")
        lines.append(f"git push origin --delete {BRANCH}: {del_rem}")
        lines.append(f"git branch -D {BRANCH}: {del_loc}")
        lines.append(f"Branch ativa apos limpeza: {cur_branch} (HEAD={cur_head})")

    out_path = HERE / "item4_gh_run_mutacao.txt"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out_path.read_text(encoding="utf-8"), flush=True)


if __name__ == "__main__":
    main()

