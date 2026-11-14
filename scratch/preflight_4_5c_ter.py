import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(r"C:\Nexus-Memory\GrafoConcierge")
OUT_DIR = ROOT / "scratch" / "evidencia_4_5c_ter"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PY312 = ROOT / ".venv_312" / "Scripts" / "python.exe"


def save_preflight_git() -> None:
    cmds = [
        ["git", "rev-parse", "HEAD"],
        ["git", "ls-remote", "origin", "main"],
        ["git", "status", "--short"],
    ]
    lines = []
    for c in cmds:
        p = subprocess.run(c, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        lines.append(f"$ {' '.join(c)}\nexit_code={p.returncode}\n{p.stdout.strip()}")
        if p.stderr.strip():
            lines.append(p.stderr.strip())
    lines.append(f"build_exists={(ROOT / 'build').exists()}")
    lines.append(f"egg_info={[x.name for x in ROOT.glob('*.egg-info')]}")
    (OUT_DIR / "pre_voo_git.txt").write_text("\n\n".join(lines) + "\n", encoding="utf-8")


def run_baseline() -> None:
    xml_path = Path(tempfile.gettempdir()) / "baseline_4_5c_ter.xml"
    xml_path.unlink(missing_ok=True)
    cmd = [str(PY312), "-m", "pytest", "tests/", "-q", f"--junitxml={xml_path}"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (OUT_DIR / "baseline_pytest.txt").write_text(
        f"$ {' '.join(cmd)}\nexit_code={proc.returncode}\n\n{proc.stdout}\n{proc.stderr}",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Baseline pytest failed: exit_code={proc.returncode}")

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

    col = subprocess.run(
        [str(PY312), "-m", "pytest", "tests/", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    nodeids = [
        line.strip()
        for line in col.stdout.splitlines()
        if line.strip() and "::" in line and not line.strip().startswith("=")
    ]
    if len(nodeids) != len(statuses):
        raise RuntimeError(f"Mismatch collect ({len(nodeids)}) vs junitxml ({len(statuses)})")
    lines = [f"{nid} :: {st}" for nid, st in zip(nodeids, statuses)]
    (OUT_DIR / "baseline_ids.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    xml_path.unlink(missing_ok=True)
    print(f"Baseline 4.5c-ter OK: {len(lines)} tests")


if __name__ == "__main__":
    save_preflight_git()
    run_baseline()
