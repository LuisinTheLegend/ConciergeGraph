import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(r"C:\Nexus-Memory\GrafoConcierge")
OUT_DIR = ROOT / "scratch" / "evidencia_4_5c"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PY312 = Path(r"C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe")
PY314 = Path(r"C:\Python314\python.exe")


def parse_junit_ids(xml_path: Path, col_proc_stdout: str) -> list[str]:
    tree = ET.parse(xml_path)
    root_el = tree.getroot()
    cases = []
    for tc in root_el.iter("testcase"):
        status = "PASSED"
        if tc.find("skipped") is not None:
            sk = tc.find("skipped")
            sk_type = sk.attrib.get("type", "")
            status = "XFAIL" if "xfail" in sk_type.lower() else "SKIPPED"
        elif tc.find("failure") is not None:
            status = "FAILED"
        elif tc.find("error") is not None:
            status = "ERROR"
        cases.append(status)

    nodeids = [
        line.strip()
        for line in col_proc_stdout.splitlines()
        if line.strip() and "::" in line and not line.strip().startswith("=")
    ]
    if len(nodeids) != len(cases):
        raise RuntimeError(f"Mismatch collect ({len(nodeids)}) vs junitxml ({len(cases)})")
    return [f"{nid} :: {st}" for nid, st in zip(nodeids, cases)]


def run_4_1_and_4_2():
    xml_path = Path(tempfile.gettempdir()) / "pos_4_5c.xml"
    if xml_path.exists():
        xml_path.unlink()

    cmd_norm = [str(PY312), "-m", "pytest", "-v", "--tb=short", f"--junitxml={xml_path}"]
    proc_norm = subprocess.run(
        cmd_norm, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    (OUT_DIR / "pytest_normal.txt").write_text(
        f"$ {' '.join(cmd_norm)}\nexit_code={proc_norm.returncode}\n\n{proc_norm.stdout}\n{proc_norm.stderr}",
        encoding="utf-8",
    )
    if proc_norm.returncode != 0:
        raise RuntimeError(f"Normal pytest failed: {proc_norm.returncode}")

    col_proc = subprocess.run(
        [str(PY312), "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    pos_lines = parse_junit_ids(xml_path, col_proc.stdout)
    (OUT_DIR / "pos_ids.txt").write_text("\n".join(pos_lines) + "\n", encoding="utf-8")
    xml_path.unlink(missing_ok=True)

    # Compare baseline vs pos
    base_lines = [
        l.strip()
        for l in (OUT_DIR / "baseline_ids.txt").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    base_set = set(base_lines)
    pos_set = set(pos_lines)
    removed = sorted(base_set - pos_set)
    added = sorted(pos_set - base_set)
    kept = len(base_set & pos_set)

    cons_report = [
        "# Verificação 4.1 — Conservação de Testes (baseline vs pós-4.5c)",
        f"baseline_count={len(base_lines)}",
        f"pos_count={len(pos_lines)}",
        f"kept_unchanged={kept}",
        f"removed_count={len(removed)}",
        f"added_count={len(added)}",
        "",
        "## Removidos do baseline (esperado: exatamente 1 ID movido de test_concurrency_stress.py):",
        *[f"- {r}" for r in removed],
        "",
        "## Adicionados / Movidos em pos_ids (esperado: 9 IDs):",
        *[f"+ {a}" for a in added],
    ]
    (OUT_DIR / "verif_1_conservacao.txt").write_text("\n".join(cons_report) + "\n", encoding="utf-8")

    # 4.2 Ordem Reversa via pytest-reverse (--reverse)
    cmd_rev = [str(PY312), "-m", "pytest", "--reverse", "-v", "--tb=short"]
    proc_rev = subprocess.run(
        cmd_rev, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    (OUT_DIR / "pytest_reverso.txt").write_text(
        f"$ {' '.join(cmd_rev)}\nexit_code={proc_rev.returncode}\n\n{proc_rev.stdout}\n{proc_rev.stderr}",
        encoding="utf-8",
    )
    if proc_rev.returncode != 0:
        raise RuntimeError(f"Reverse pytest failed: {proc_rev.returncode}")
    print("4.1 and 4.2 OK")
    return proc_norm.stdout.strip().splitlines()[-1]


def run_4_7(py312_summary: str):
    ver312 = subprocess.run(
        [str(PY312), "--version"], capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()
    ver314 = subprocess.run(
        [str(PY314), "--version"], capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()

    cmd_314 = [str(PY314), "-m", "pytest", "-v", "--tb=short"]
    proc_314 = subprocess.run(
        cmd_314, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    tail_314 = "\n".join(proc_314.stdout.strip().splitlines()[-10:])
    report = [
        "# Verificação 4.7 — Versões de Python",
        f"## 1. {ver312} ({PY312})",
        f"summary: {py312_summary}",
        "",
        f"## 2. {ver314} ({PY314})",
        f"cmd: {' '.join(cmd_314)}",
        f"exit_code={proc_314.returncode}",
        "--- FULL OUTPUT ---",
        proc_314.stdout.strip(),
        proc_314.stderr.strip(),
    ]
    (OUT_DIR / "verif_7_python_versions.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    if proc_314.returncode != 0:
        raise RuntimeError(f"Python 3.14 pytest failed: {proc_314.returncode}\n{tail_314}")
    print("4.7 Python 3.14 OK")


if __name__ == "__main__":
    summary_312 = run_4_1_and_4_2()
    run_4_7(summary_312)
    print("ALL FULL SUITE VERIFICATIONS COMPLETE.")
