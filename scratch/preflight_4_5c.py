import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(r"C:\Nexus-Memory\GrafoConcierge")
OUT_DIR = ROOT / "scratch" / "evidencia_4_5c"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PY312 = Path(r"C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe")


def verify_lines():
    checks = [
        ("tests/test_interface_contracts.py", 214, 232, "REQUIRED_TOOLS"),
        ("tests/test_interface_contracts.py", 20, 20, "ActionHooks import"),
        ("tests/test_interface_contracts.py", 116, 123, "ActionHooks fixture/usage 1"),
        ("tests/test_interface_contracts.py", 156, 173, "ActionHooks usage 2"),
        ("tests/test_progressive_tool_disclosure.py", 23, 35, "setUp"),
        ("tests/test_progressive_tool_disclosure.py", 36, 82, "4 unit tests MCPToolGovernor"),
        ("tests/test_progressive_tool_disclosure.py", 84, 110, "REST xfail test"),
        ("tests/test_probabilistic_retriever.py", 18, 29, "temp_db fixture"),
        ("tests/test_probabilistic_retriever.py", 32, 53, "test_update_memory_utility"),
        ("storage/semantic_logic.py", 101, 125, "update_memory_utility"),
        ("tests/test_concurrency_stress.py", 138, 184, "TestCleanDatabaseManagerSchema"),
        ("core/mcp_governor.py", 43, 76, "TOOL_DISCLOSURE_MATRIX"),
        ("core/mcp_governor.py", 79, 126, "TOOL_CLASSIFICATION"),
        ("interface/mcp_server.py", 242, 267, "_setup_tool_governance (L242-266 + L267 blank)"),
    ]
    report = ["# Verificação de Citações de Linha (Regra 14)\n"]
    for rel, start, end, desc in checks:
        lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
        snippet = lines[start - 1 : end]
        report.append(f"## {rel}:{start}-{end} ({desc}) [total_lines={len(lines)}]")
        if snippet:
            report.append(f"L{start}: {snippet[0]}")
            if len(snippet) > 1:
                report.append(f"L{end}: {snippet[-1]}")
        report.append("")
    (OUT_DIR / "pre_voo_linhas.txt").write_text("\n".join(report), encoding="utf-8")


def run_baseline_pytest():
    xml_path = Path(tempfile.gettempdir()) / "baseline_4_5c.xml"
    if xml_path.exists():
        xml_path.unlink()
    cmd = [
        str(PY312),
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        f"--junitxml={xml_path}",
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    full_out = (
        f"$ {' '.join(cmd)}\n"
        f"exit_code={proc.returncode}\n\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
    (OUT_DIR / "baseline_pytest.txt").write_text(full_out, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"Baseline pytest failed with code {proc.returncode}")

    tree = ET.parse(xml_path)
    root_el = tree.getroot()
    cases = []
    for tc in root_el.iter("testcase"):
        cls = tc.attrib.get("classname", "")
        name = tc.attrib.get("name", "")
        status = "PASSED"
        if tc.find("skipped") is not None:
            sk = tc.find("skipped")
            sk_type = sk.attrib.get("type", "")
            status = "XFAIL" if "xfail" in sk_type.lower() else "SKIPPED"
        elif tc.find("failure") is not None:
            status = "FAILED"
        elif tc.find("error") is not None:
            status = "ERROR"
        cases.append((cls, name, status))

    # Also collect exact pytest nodeids via --collect-only -q
    col_cmd = [str(PY312), "-m", "pytest", "--collect-only", "-q"]
    col_proc = subprocess.run(
        col_cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    nodeids = []
    for line in col_proc.stdout.splitlines():
        line = line.strip()
        if line and "::" in line and not line.startswith("="):
            nodeids.append(line)

    if len(nodeids) != len(cases):
        raise RuntimeError(
            f"Mismatch collect-only ({len(nodeids)}) vs junitxml ({len(cases)})"
        )

    lines = []
    for nid, (_, _, status) in zip(nodeids, cases):
        lines.append(f"{nid} :: {status}")
    (OUT_DIR / "baseline_ids.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    xml_path.unlink(missing_ok=True)
    print(f"Baseline pytest OK: {len(lines)} tests recorded.")


def build_baseline_wheel():
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            str(PY312),
            "-c",
            (
                "import sys; from setuptools import build_meta; "
                "whl = build_meta.build_wheel(sys.argv[1]); print(whl)"
            ),
            tmp,
        ]
        proc = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
        )
        whl_name = proc.stdout.strip().splitlines()[-1]
        whl_path = Path(tmp) / whl_name
        with zipfile.ZipFile(whl_path) as zf:
            entries = sorted(zf.namelist())
        (OUT_DIR / "wheel_antes.txt").write_text(
            "\n".join(entries) + "\n", encoding="utf-8"
        )
        print(f"Baseline wheel OK: {len(entries)} entries ({whl_name}).")


if __name__ == "__main__":
    verify_lines()
    run_baseline_pytest()
    build_baseline_wheel()
