import difflib
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

ROOT = Path(r"C:\Nexus-Memory\GrafoConcierge")
OUT_DIR = ROOT / "scratch" / "evidencia_4_5c"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PY312 = ROOT / ".venv_312" / "Scripts" / "python.exe"


def run_cmd(cmd, cwd=ROOT, env=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def verif_3_mutations():
    mutations = [
        {
            "id": "A1_register_tool",
            "file": ROOT / "interface" / "mcp_server.py",
            "old": '        @self._mcp.tool(\r\n            name="concierge_get_call_chain",',
            "old_alt": '        @self._mcp.tool(\n            name="concierge_get_call_chain",',
            "new": '        @self._mcp.tool(\n            name="concierge_get_call_chain_MUTATED",',
            "pytest_args": [
                "tests/test_interface_contracts.py",
                "-k",
                "TestMCPToolRegistration",
                "-v",
                "--tb=short",
            ],
        },
        {
            "id": "A2_tool_classification",
            "file": ROOT / "core" / "mcp_governor.py",
            "old": '            "concierge_get_call_chain": "READ_ONLY",',
            "new": '            # MUTATED: "concierge_get_call_chain": "READ_ONLY",',
            "pytest_args": [
                "tests/test_interface_contracts.py",
                "-k",
                "test_all_registered_tools_classified_in_governor",
                "-v",
                "--tb=short",
            ],
        },
        {
            "id": "A3_governed_call_tool",
            "file": ROOT / "interface" / "mcp_server.py",
            "old": "            self._governor.validate_tool_execution(session_id, name)",
            "new": "            pass  # MUTATED: bypassed validate_tool_execution(session_id, name)",
            "pytest_args": [
                "tests/test_interface_contracts.py",
                "-k",
                "test_governed_call_tool_executes_and_enforces_state",
                "-v",
                "--tb=short",
            ],
        },
        {
            "id": "B_mcp_governor_planning",
            "file": ROOT / "core" / "mcp_governor.py",
            "old": '            "PLANNING": {\r\n                "allowed_categories": ["READ_ONLY"],',
            "old_alt": '            "PLANNING": {\n                "allowed_categories": ["READ_ONLY"],',
            "new": '            "PLANNING": {\n                "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],',
            "pytest_args": ["tests/test_mcp_governor.py", "-v", "--tb=short"],
        },
        {
            "id": "C_semantic_facts_utility",
            "file": ROOT / "storage" / "semantic_logic.py",
            "old": "               SET utility_alpha = utility_alpha + 1.0",
            "new": "               SET utility_alpha = utility_alpha + 0.0",
            "pytest_args": ["tests/test_semantic_facts_utility.py", "-v", "--tb=short"],
        },
        {
            "id": "D_clean_database_schema",
            "file": ROOT / "core" / "database.py",
            "old": '    def _init_tables(self):\r\n        """No-op: Schema creation is managed exclusively by SchemaManager (storage/schema.py)."""\r\n        pass',
            "old_alt": '    def _init_tables(self):\n        """No-op: Schema creation is managed exclusively by SchemaManager (storage/schema.py)."""\n        pass',
            "new": (
                '    def _init_tables(self):\n'
                '        """No-op: Schema creation is managed exclusively by SchemaManager (storage/schema.py)."""\n'
                '        conn = sqlite3.connect(self.db_path)\n'
                '        conn.execute("CREATE TABLE IF NOT EXISTS test_log (id INT);")\n'
                '        conn.commit()\n'
                '        conn.close()'
            ),
            "pytest_args": ["tests/test_clean_database_schema.py", "-v", "--tb=short"],
        },
    ]

    log = ["# Verificação 4.3 — Mutações Red -> Green\n"]
    for m in mutations:
        fpath: Path = m["file"]
        orig_bytes = fpath.read_bytes()
        text = orig_bytes.decode("utf-8")
        target = m["old"] if m["old"] in text else m.get("old_alt", m["old"])
        if target not in text:
            raise RuntimeError(f"Mutation {m['id']}: target pattern not found in {fpath}")
        eol = "\r\n" if "\r\n" in text else "\n"
        replacement = m["new"].replace("\r\n", "\n").replace("\n", eol)
        mutated_text = text.replace(target, replacement, 1)

        log.append(f"## Mutation {m['id']} ({fpath.relative_to(ROOT)})")
        try:
            fpath.write_bytes(mutated_text.encode("utf-8"))
            red_proc = run_cmd([str(PY312), "-m", "pytest", *m["pytest_args"]])
            log.append(f"RED exit_code={red_proc.returncode}")
            log.append(red_proc.stdout.strip())
            if red_proc.stderr.strip():
                log.append(red_proc.stderr.strip())
            if red_proc.returncode == 0:
                raise RuntimeError(f"Mutation {m['id']} did NOT fail in RED phase!")
        finally:
            fpath.write_bytes(orig_bytes)

        green_proc = run_cmd([str(PY312), "-m", "pytest", *m["pytest_args"]])
        log.append(f"GREEN exit_code={green_proc.returncode}")
        log.append(green_proc.stdout.strip())
        if green_proc.returncode != 0:
            raise RuntimeError(f"Mutation {m['id']} did NOT pass in GREEN phase!")
        log.append("")

    diff_proc = run_cmd(
        [
            "git",
            "diff",
            "--",
            "core/",
            "storage/",
            "interface/",
            "ingestion/",
            "services/",
            "agent/",
            "agents/",
            "main.py",
            "pyproject.toml",
        ]
    )
    log.append("## Proof of clean product git diff after mutations")
    log.append(f"git diff exit_code={diff_proc.returncode}, bytes={len(diff_proc.stdout)}")
    if diff_proc.stdout.strip():
        log.append(diff_proc.stdout)
        raise RuntimeError("Product git diff is not empty after mutations!")
    (OUT_DIR / "verif_3_mutacoes_red_green.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print("verif_3_mutations OK")


def verif_4_isolation():
    code = (
        "import sys, pytest; "
        "sys.modules['interface.telemetry_api'] = None; "
        "sys.modules['core.probabilistic_retriever'] = None; "
        "raise SystemExit(pytest.main(['tests/test_mcp_governor.py', 'tests/test_semantic_facts_utility.py', '-v', '--tb=short']))"
    )
    cmd = [str(PY312), "-c", code]
    proc = run_cmd(cmd)
    out = (
        "# Verificação 4.4 — Isolamento dos novos testes com módulos dormentes bloqueados\n"
        f"cmd: {' '.join(cmd)}\nexit_code={proc.returncode}\n\n{proc.stdout}\n{proc.stderr}"
    )
    (OUT_DIR / "verif_4_isolamento.txt").write_text(out, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"verif_4_isolation failed with exit_code={proc.returncode}")
    print("verif_4_isolation OK")


def verif_5_wheel_and_venv_smoke():
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        wheel_out_dir = tmp_dir / "dist"
        wheel_out_dir.mkdir()
        build_proc = run_cmd(
            [
                str(PY312),
                "-c",
                (
                    "import sys; from setuptools import build_meta; "
                    "print(build_meta.build_wheel(sys.argv[1]))"
                ),
                str(wheel_out_dir),
            ],
            cwd=ROOT,
        )
        if build_proc.returncode != 0:
            raise RuntimeError(f"Wheel build failed: {build_proc.stderr}")
        whl_name = build_proc.stdout.strip().splitlines()[-1]
        whl_path = wheel_out_dir / whl_name

        with zipfile.ZipFile(whl_path) as zf:
            entries_after = sorted(zf.namelist())
        (OUT_DIR / "wheel_depois.txt").write_text("\n".join(entries_after) + "\n", encoding="utf-8")

        entries_before = (OUT_DIR / "wheel_antes.txt").read_text(encoding="utf-8").splitlines()
        diff_lines = list(
            difflib.unified_diff(
                entries_before,
                entries_after,
                fromfile="wheel_antes.txt",
                tofile="wheel_depois.txt",
                lineterm="",
            )
        )
        if diff_lines:
            raise RuntimeError(f"Wheel diff detected: {diff_lines}")

        # Clean venv (without editable finder from .venv_312 .pth files)
        clean_venv_dir = tmp_dir / "clean_venv"
        venv.create(clean_venv_dir, with_pip=False, symlinks=False)
        venv_python = clean_venv_dir / "Scripts" / "python.exe"
        venv_sp = clean_venv_dir / "Lib" / "site-packages"
        with zipfile.ZipFile(whl_path) as zf:
            zf.extractall(venv_sp)

        run_dir = tmp_dir / "isolated_run"
        run_dir.mkdir()
        deps_sp = str((ROOT / ".venv_312" / "Lib" / "site-packages").resolve())
        venv_sp_resolved = str(venv_sp.resolve())
        repo_resolved = str(ROOT.resolve())

        smoke_code = f"""
import os
import sys
from pathlib import Path

repo_root = Path({repo_resolved!r}).resolve()
venv_sp = Path({venv_sp_resolved!r}).resolve()
# Ensure clean_venv site-packages comes first and repo_root is never on sys.path.
# Appending deps_sp directly avoids executing __editable__*.pth hooks.
sys.path = [p for p in sys.path if Path(p or ".").resolve() != repo_root]
if {deps_sp!r} not in sys.path:
    sys.path.append({deps_sp!r})
    for _sub in ("win32", os.path.join("win32", "lib"), "Pythonwin"):
        _p = os.path.join({deps_sp!r}, _sub)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.append(_p)
    _pywin32_sys = os.path.join({deps_sp!r}, "pywin32_system32")
    if os.path.isdir(_pywin32_sys) and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_pywin32_sys)

assert not any("editable" in repr(f).lower() for f in sys.meta_path), f"Editable finder active: {{sys.meta_path}}"

import main
import core.database
import core.mcp_governor
import storage.store
import ingestion.orchestrator
import services.janitor
import interface.mcp_server

for mod_name in (
    "main",
    "core.database",
    "core.mcp_governor",
    "storage.store",
    "ingestion.orchestrator",
    "services.janitor",
    "interface.mcp_server",
):
    mod_file = Path(sys.modules[mod_name].__file__).resolve()
    assert mod_file.is_relative_to(venv_sp), f"{{mod_name}} loaded from {{mod_file}}, expected inside {{venv_sp}}"
    assert not mod_file.is_relative_to(repo_root), f"{{mod_name}} leaked from repo: {{mod_file}}"

srv, janitor, store = main.bootstrap()
try:
    tools = sorted(srv.mcp._tool_manager._tools.keys())
    print("MAIN_FILE=" + main.__file__)
    print("MCP_SERVER_FILE=" + interface.mcp_server.__file__)
    print(f"TOOL_COUNT={{len(tools)}}")
    for idx, t in enumerate(tools, 1):
        print(f"{{idx:02d}}. {{t}}")
    assert len(tools) == 31, f"Expected 31 tools, got {{len(tools)}}"
finally:
    if janitor is not None:
        janitor.stop_background(timeout=5.0)
    if store is not None:
        store.close()
"""
        env = os.environ.copy()
        env["GRAFO_LIGHTWEIGHT_MODE"] = "true"
        env["GRAFO_LLM_PROVIDER"] = "none"
        env["GRAFO_LLM_MODEL"] = "none"
        env["GRAFO_DB_PATH"] = str(run_dir / "smoke.db")
        env["GRAFO_CHROMA_PATH"] = str(run_dir / "chroma")
        env.pop("PYTHONPATH", None)

        smoke_proc = run_cmd([str(venv_python), "-c", smoke_code], cwd=run_dir, env=env)
        report = [
            "# Verificação 4.5 — Wheel Antes/Depois + Smoke em Venv Limpa",
            f"wheel_name={whl_name}",
            f"wheel_antes_count={len(entries_before)}",
            f"wheel_depois_count={len(entries_after)}",
            "wheel_diff_lines=0 (IDENTICAL)",
            "",
            f"smoke_cwd={run_dir}",
            f"smoke_exit_code={smoke_proc.returncode}",
            "--- STDOUT ---",
            smoke_proc.stdout.strip(),
            "--- STDERR ---",
            smoke_proc.stderr.strip(),
        ]
        (OUT_DIR / "verif_5_wheel_venv_smoke.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        if smoke_proc.returncode != 0:
            raise RuntimeError(f"Clean venv smoke failed: {smoke_proc.stderr}\n{smoke_proc.stdout}")
        print("verif_5_wheel_and_venv_smoke OK")


def verif_6_secrets_and_flake8():
    sec_proc = run_cmd([str(PY312), "scratch/tools/scan_secrets.py"])
    flake_proc = run_cmd(
        [
            str(PY312),
            "-m",
            "flake8",
            ".",
            "--extend-exclude=.venv*",
            "--count",
            "--select=E9,F63,F7,F82",
            "--show-source",
            "--statistics",
        ]
    )
    out = [
        "# Verificação 4.6 — Scanner de Segredos e Flake8",
        "## 1. Secret scanner (python scratch/tools/scan_secrets.py)",
        f"exit_code={sec_proc.returncode}",
        sec_proc.stdout.strip(),
        sec_proc.stderr.strip(),
        "",
        "## 2. Flake8 (E9,F63,F7,F82; excluindo .venv_* locais ausentes no CI)",
        f"exit_code={flake_proc.returncode}",
        flake_proc.stdout.strip(),
        flake_proc.stderr.strip(),
    ]
    (OUT_DIR / "verif_6_secrets_flake8.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    if sec_proc.returncode != 0 or flake_proc.returncode != 0:
        raise RuntimeError(
            f"verif_6 failed: secrets={sec_proc.returncode}, flake8={flake_proc.returncode}"
        )
    print("verif_6_secrets_and_flake8 OK")


if __name__ == "__main__":
    steps = set(sys.argv[1:]) or {"3", "4", "5", "6"}
    if "3" in steps:
        verif_3_mutations()
    if "4" in steps:
        verif_4_isolation()
    if "5" in steps:
        verif_5_wheel_and_venv_smoke()
    if "6" in steps:
        verif_6_secrets_and_flake8()
    print("ALL SANDBOX VERIFICATIONS COMPLETE.")
