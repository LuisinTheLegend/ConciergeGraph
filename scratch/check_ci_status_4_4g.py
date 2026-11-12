"""
scratch/check_ci_status_4_4g.py — Consulta status dos runs e jobs do GitHub Actions
para os commits da Rodada 4.4g (além de 26a43e2 e do job com falha em 3dccf68).
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "LuisinTheLegend/ConciergeGraph"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4g")
os.makedirs(OUT_DIR, exist_ok=True)


def fetch_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "GrafoConcierge-Audit-Script"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_text(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "GrafoConcierge-Audit-Script"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, str(exc)


def git_commits_since(base_sha: str) -> list[str]:
    p = subprocess.run(
        ["git", "log", "--reverse", "--format=%H", f"{base_sha}..HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if p.returncode != 0:
        return []
    return [line.strip() for line in p.stdout.splitlines() if line.strip()]


def main() -> None:
    target_shas = sys.argv[1:] if len(sys.argv) > 1 else git_commits_since("26a43e2")
    runs_data = fetch_json(f"https://api.github.com/repos/{REPO}/actions/runs?per_page=25")
    by_sha: dict[str, list[dict]] = {}
    for run in runs_data.get("workflow_runs", []):
        by_sha.setdefault(run["head_sha"], []).append(run)

    lines = ["=== GITHUB ACTIONS CI STATUS (RODADA 4.4g) ==="]

    # Metadados públicos do job com falha do 3dccf68 (run 43075938190)
    try:
        j3 = fetch_json(f"https://api.github.com/repos/{REPO}/actions/jobs/130715647420")
        lines.append("\nReferência de falha histórica no 3dccf68 (run 43075938190):")
        lines.append(
            f"  Job {j3['id']} ({j3['name']}) | status={j3['status']} | conclusion={j3['conclusion']} | completed_at={j3['completed_at']}"
        )
        for st in j3.get("steps", []):
            if st.get("conclusion") != "success":
                lines.append(
                    f"    - Step {st['number']}: {st['name']} | conclusion={st['conclusion']} | completed_at={st['completed_at']}"
                )
        code, body = fetch_text(f"https://api.github.com/repos/{REPO}/actions/jobs/130715647420/logs")
        lines.append(f"  Endpoint logs públicos: HTTP {code} ({body.splitlines()[0] if body else ''})")
    except Exception as exc:
        lines.append(f"\nErro ao consultar job 130715647420: {exc}")

    # Commits alvo (rodada atual + 26a43e2 se listado)
    shas_to_report = list(dict.fromkeys(target_shas + ["26a43e2723488f5206c12f639c0a94a7ba3c483d"]))
    all_completed = True
    any_failed = False

    for full_sha in shas_to_report:
        short = full_sha[:7]
        runs = by_sha.get(full_sha, [])
        lines.append(f"\nCommit {short} ({full_sha}):")
        if not runs:
            lines.append("  Nenhum workflow run encontrado ainda na API pública.")
            if full_sha != "26a43e2723488f5206c12f639c0a94a7ba3c483d":
                all_completed = False
            continue
        total_jobs = 0
        green_jobs = 0
        for r in runs:
            jobs_data = fetch_json(r["jobs_url"])
            jobs = jobs_data.get("jobs", [])
            lines.append(
                f"  Workflow: {r['name']} (run_id={r['id']}, status={r['status']}, conclusion={r['conclusion']})"
            )
            if r["status"] != "completed":
                all_completed = False
            for j in jobs:
                total_jobs += 1
                concl = j.get("conclusion")
                if j.get("status") != "completed":
                    all_completed = False
                if concl == "success":
                    green_jobs += 1
                elif concl is not None:
                    any_failed = True
                lines.append(
                    f"    - Job: {j['name']} (id={j['id']}) | status={j['status']} | conclusion={concl}"
                )
                if concl and concl != "success":
                    for st in j.get("steps", []):
                        if st.get("conclusion") not in ("success", "skipped", None):
                            lines.append(
                                f"        * Step falho: {st['name']} | conclusion={st['conclusion']}"
                            )
                    try:
                        anns = fetch_json(f"https://api.github.com/repos/{REPO}/check-runs/{j['id']}/annotations")
                        for ann in anns[:5]:
                            lines.append(
                                f"        * Annotation ({ann.get('path')}:{ann.get('start_line')}): {ann.get('message')}"
                            )
                    except Exception:
                        pass
                    lcode, lbody = fetch_text(f"https://api.github.com/repos/{REPO}/actions/jobs/{j['id']}/logs")
                    if lcode == 200:
                        tail = "\n".join(lbody.splitlines()[-30:])
                        lines.append(f"        * Tail do log:\n{tail}")
                    else:
                        lines.append(f"        * Log API HTTP {lcode}")
        lines.append(f"  => Resumo {short}: {green_jobs}/{total_jobs} jobs verdes (success)")

    lines.append(f"\nall_completed={all_completed}, any_failed={any_failed}")
    report = "\n".join(lines) + "\n"
    out_path = os.path.join(OUT_DIR, "ci_status.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()

