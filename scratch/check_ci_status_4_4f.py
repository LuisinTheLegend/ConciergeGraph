"""
scratch/check_ci_status_4_4f.py — Consulta status dos runs e jobs do GitHub Actions para 3dccf68 e commits recentes (Rodada 4.4f).
"""
import json
import os
import urllib.request

REPO = "LuisinTheLegend/ConciergeGraph"
OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "evidencia_4_4f"))
os.makedirs(OUT_DIR, exist_ok=True)


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "GrafoConcierge-Audit-Script"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    runs_data = fetch_json(f"https://api.github.com/repos/{REPO}/actions/runs?per_page=15")
    lines = ["=== GITHUB ACTIONS CI STATUS (RODADA 4.4f) ==="]
    by_sha: dict[str, list[dict]] = {}
    for run in runs_data.get("workflow_runs", []):
        sha = run["head_sha"][:7]
        by_sha.setdefault(sha, []).append(run)

    for sha, runs in by_sha.items():
        lines.append(f"\nCommit {sha} ({runs[0]['head_sha']}):")
        total_jobs = 0
        green_jobs = 0
        for r in runs:
            jobs_data = fetch_json(r["jobs_url"])
            jobs = jobs_data.get("jobs", [])
            lines.append(
                f"  Workflow: {r['name']} (run_id={r['id']}, status={r['status']}, conclusion={r['conclusion']})"
            )
            for j in jobs:
                total_jobs += 1
                if j.get("conclusion") == "success":
                    green_jobs += 1
                lines.append(f"    - Job: {j['name']} | status={j['status']} | conclusion={j['conclusion']}")
        lines.append(f"  => Resumo {sha}: {green_jobs}/{total_jobs} jobs verdes (success)")

    report = "\n".join(lines) + "\n"
    out_path = os.path.join(OUT_DIR, "ci_status.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()

