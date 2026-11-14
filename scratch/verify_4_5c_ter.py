import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(r"C:\Nexus-Memory\GrafoConcierge")
PY312 = ROOT / ".venv_312" / "Scripts" / "python.exe"
OUT_DIR = ROOT / "scratch" / "evidencia_4_5c_ter"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def root_clean_state() -> dict:
    return {
        "build_exists": (ROOT / "build").exists(),
        "egg_info": [p.name for p in ROOT.glob("*.egg-info")],
    }


def check_flake8() -> None:
    lines = ["=== FLAKE8 CI EXACT ==="]
    cmd1 = [
        str(PY312),
        "-m",
        "flake8",
        ".",
        "--count",
        "--select=E9,F63,F7,F82",
        "--show-source",
        "--statistics",
    ]
    p1 = run_cmd(cmd1)
    lines.append(f"$ {' '.join(cmd1)}\nexit_code={p1.returncode}\n{p1.stdout}\n{p1.stderr}".strip())
    if p1.returncode != 0:
        cmd2 = [
            str(PY312),
            "-m",
            "flake8",
            ".",
            "--count",
            "--select=E9,F63,F7,F82",
            "--show-source",
            "--statistics",
            "--extend-exclude=.venv_310,.venv_311,.venv_312,.venv_313,.venv_clean",
        ]
        p2 = run_cmd(cmd2)
        lines.append("\n=== FLAKE8 (--extend-exclude=.venv*) ===")
        lines.append(f"$ {' '.join(cmd2)}\nexit_code={p2.returncode}\n{p2.stdout}\n{p2.stderr}".strip())
        if p2.returncode != 0:
            (OUT_DIR / "final_flake8.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            raise RuntimeError(f"flake8 with --extend-exclude failed: {p2.returncode}")
    (OUT_DIR / "final_flake8.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_ids_and_statuses(xml_path: Path) -> list[str]:
    tree = ET.parse(xml_path)
    statuses = []
    for tc in tree.getroot().iter("testcase"):
        st = "PASSED"
        if tc.find("skipped") is not None:
            sk = tc.find("skipped")
            st = "XFAIL" if "xfail" in sk.attrib.get("type", "").lower() else "SKIPPED"
        elif tc.find("failure") is not None:
            st = "FAILED"
        elif tc.find("error") is not None:
            st = "ERROR"
        statuses.append(st)
    col = run_cmd([str(PY312), "-m", "pytest", "tests/", "--collect-only", "-q"])
    nodeids = [
        line.strip()
        for line in col.stdout.splitlines()
        if line.strip() and "::" in line and not line.strip().startswith("=")
    ]
    if len(nodeids) != len(statuses):
        raise RuntimeError(f"Mismatch collect ({len(nodeids)}) vs xml ({len(statuses)})")
    return [f"{nid} :: {st}" for nid, st in zip(nodeids, statuses)]


def check_pytest_and_conservation() -> None:
    xml_path = Path(tempfile.gettempdir()) / "final_4_5c_ter.xml"
    xml_path.unlink(missing_ok=True)
    cmd_norm = [str(PY312), "-m", "pytest", "tests/", "-q", f"--junitxml={xml_path}"]
    p_norm = run_cmd(cmd_norm)
    (OUT_DIR / "final_pytest_normal.txt").write_text(
        f"$ {' '.join(cmd_norm)}\nexit_code={p_norm.returncode}\n{p_norm.stdout}\n{p_norm.stderr}",
        encoding="utf-8",
    )
    if p_norm.returncode != 0:
        raise RuntimeError(f"pytest normal failed: {p_norm.returncode}")

    final_lines = parse_ids_and_statuses(xml_path)
    xml_path.unlink(missing_ok=True)
    baseline_lines = (OUT_DIR / "baseline_ids.txt").read_text(encoding="utf-8").splitlines()
    equal = final_lines == baseline_lines
    (OUT_DIR / "final_conservation.txt").write_text(
        f"baseline_count={len(baseline_lines)}\n"
        f"final_count={len(final_lines)}\n"
        f"exact_match={equal}\n",
        encoding="utf-8",
    )
    if not equal:
        bset, fset = set(baseline_lines), set(final_lines)
        raise RuntimeError(f"Conservation mismatch! removed={bset-fset}, added={fset-bset}")

    cmd_rev = [str(PY312), "-m", "pytest", "tests/", "-q", "--reverse"]
    p_rev = run_cmd(cmd_rev)
    (OUT_DIR / "final_pytest_reverse.txt").write_text(
        f"$ {' '.join(cmd_rev)}\nexit_code={p_rev.returncode}\n{p_rev.stdout}\n{p_rev.stderr}",
        encoding="utf-8",
    )
    if p_rev.returncode != 0:
        raise RuntimeError(f"pytest --reverse failed: {p_rev.returncode}")


def check_scope_and_secrets() -> None:
    forbidden = [
        "core/",
        "storage/",
        "interface/",
        "ingestion/",
        "services/",
        "agent/",
        "agents/",
        "main.py",
        "pyproject.toml",
        ".github/",
    ]
    p_diff = run_cmd(["git", "diff", "--", *forbidden])
    clean_after = root_clean_state()
    (OUT_DIR / "final_scope_check.txt").write_text(
        f"forbidden_diff_bytes={len(p_diff.stdout.encode('utf-8'))}\n"
        f"clean_root_after_pytest={clean_after}\n"
        f"diff_output={p_diff.stdout!r}\n",
        encoding="utf-8",
    )
    if p_diff.stdout.strip():
        raise RuntimeError("Forbidden paths were modified!")
    if clean_after["build_exists"] or clean_after["egg_info"]:
        raise RuntimeError(f"Build artifacts left on repo root: {clean_after}")

    p_sec = run_cmd([str(PY312), "scratch/tools/scan_secrets.py"])
    (OUT_DIR / "final_scan_secrets.txt").write_text(
        f"$ python scratch/tools/scan_secrets.py\nexit_code={p_sec.returncode}\n{p_sec.stdout}\n{p_sec.stderr}",
        encoding="utf-8",
    )
    if p_sec.returncode != 0:
        raise RuntimeError(f"scan_secrets failed: {p_sec.returncode}")


def main() -> None:
    pre = root_clean_state()
    assert not pre["build_exists"] and not pre["egg_info"], f"Pre-verify root dirty: {pre}"
    check_flake8()
    check_pytest_and_conservation()
    check_scope_and_secrets()
    print("ALL FINAL 4.5c-ter VERIFICATIONS PASSED OK.")


if __name__ == "__main__":
    main()
