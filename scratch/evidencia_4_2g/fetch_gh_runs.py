import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "LuisinTheLegend/ConciergeGraph"


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


def check_commit_runs(commit_sha_prefix: str, out_file: Path):
    lines = []
    gh_path = shutil.which("gh") or (
        r"C:\Program Files\GitHub CLI\gh.exe"
        if Path(r"C:\Program Files\GitHub CLI\gh.exe").exists()
        else None
    )
    lines.append(f"gh CLI path: {gh_path or 'NAO INSTALADO NO PATH'}")
    lines.append(f"Consultando GitHub REST API pública para {REPO} (commit prefix: {commit_sha_prefix})...")
    lines.append("")

    try:
        runs_data = fetch_json(f"https://api.github.com/repos/{REPO}/actions/runs?per_page=10")
        runs = runs_data.get("workflow_runs", [])
        matching = [
            r for r in runs
            if r.get("head_sha", "").startswith(commit_sha_prefix)
            and "Windows Stdin" in (r.get("name") or "")
        ]
        if not matching:
            matching = [r for r in runs if r.get("head_sha", "").startswith(commit_sha_prefix)]

        if not matching:
            lines.append(f"Nenhuma workflow_run encontrada para commit {commit_sha_prefix}.")
            for r in runs[:5]:
                lines.append(
                    f"  Run vista: id={r.get('id')} name={r.get('name')} "
                    f"branch={r.get('head_branch')} sha={r.get('head_sha')[:7]} "
                    f"status={r.get('status')} conclusion={r.get('conclusion')}"
                )
        else:
            for r in matching:
                run_id = r["id"]
                lines.append(f"Run ID: {run_id}")
                lines.append(f"Workflow: {r.get('name')}")
                lines.append(f"Branch: {r.get('head_branch')}")
                lines.append(f"Head SHA: {r.get('head_sha')}")
                lines.append(f"Status: {r.get('status')} | Conclusion: {r.get('conclusion')}")
                lines.append(f"URL: {r.get('html_url')}")
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
    except Exception as exc:
        lines.append(f"NÃO VERIFICADO: sem acesso ao Actions ({type(exc).__name__}: {exc})")

    text = "\n".join(lines) + "\n"
    out_file.write_text(text, encoding="utf-8")
    print(text, flush=True)


if __name__ == "__main__":
    sha = sys.argv[1] if len(sys.argv) > 1 else "30d65c1"
    out_name = sys.argv[2] if len(sys.argv) > 2 else "item4_gh_run_main.txt"
    check_commit_runs(sha, HERE / out_name)

