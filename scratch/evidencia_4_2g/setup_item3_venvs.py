import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
PY_127 = Path(r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe")
VENV_130_FULL = Path(r"C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full")
PY_130_FULL = VENV_130_FULL / "Scripts" / "python.exe"


def run_cmd(cmd, cwd=REPO_ROOT):
    print(f"Running: {' '.join(str(x) for x in cmd)}", flush=True)
    res = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = res.stdout
    if res.stderr:
        out += ("\n" if out and not out.endswith("\n") else "") + res.stderr
    return res.returncode, out


def main():
    # 3e) Save pip freeze of venv_mcp127
    rc, freeze_127 = run_cmd([PY_127, "-m", "pip", "freeze"])
    (HERE / "item3_venv_mcp127_pip_freeze.txt").write_text(freeze_127.strip() + "\n", encoding="utf-8")
    print(f"Saved item3_venv_mcp127_pip_freeze.txt (rc={rc})", flush=True)

    # 3a) Create new venv_mcp130_full with all project dependencies + mcp==1.30.0
    VENV_130_FULL.parent.mkdir(parents=True, exist_ok=True)
    if not PY_130_FULL.exists():
        # Create venv with --system-site-packages so torch/scipy/chromadb/sentence_transformers are present,
        # and also pip install requirements + mcp==1.30.0 into the venv itself
        rc, out = run_cmd([sys.executable, "-m", "venv", "--system-site-packages", str(VENV_130_FULL)])
        if rc != 0:
            raise RuntimeError(f"Failed to create venv_mcp130_full: {out}")

    rc, out = run_cmd([PY_130_FULL, "-m", "pip", "install", "-r", str(REPO_ROOT / "requirements.txt")])
    if rc != 0:
        raise RuntimeError(f"Failed to install requirements.txt: {out}")

    rc, out = run_cmd([PY_130_FULL, "-m", "pip", "install", "mcp==1.30.0"])
    if rc != 0:
        raise RuntimeError(f"Failed to install mcp==1.30.0: {out}")

    # Verify with pip show mcp, pip freeze, and runtime import check
    _, show_mcp = run_cmd([PY_130_FULL, "-m", "pip", "show", "mcp"])
    _, freeze_130 = run_cmd([PY_130_FULL, "-m", "pip", "freeze"])
    check_code = (
        "import importlib.metadata as m, mcp, chromadb, sentence_transformers, scipy, numpy, torch; "
        "pkgs = ['mcp', 'chromadb', 'sentence-transformers', 'scipy', 'numpy', 'torch']; "
        "print({p: m.version(p) for p in pkgs}); "
        "print('mcp.__file__ =', mcp.__file__)"
    )
    rc_chk, chk_out = run_cmd([PY_130_FULL, "-c", check_code])
    if rc_chk != 0:
        raise RuntimeError(f"Runtime import check failed: {chk_out}")

    combined = (
        "=== PIP SHOW MCP (venv_mcp130_full) ===\n"
        + show_mcp.strip()
        + "\n\n=== RUNTIME IMPORT & VERSIONS CHECK ===\n"
        + chk_out.strip()
        + "\n\n=== PIP FREEZE (venv_mcp130_full) ===\n"
        + freeze_130.strip()
        + "\n"
    )
    (HERE / "item3_venv_mcp130_full_pip.txt").write_text(combined, encoding="utf-8")
    print(show_mcp, flush=True)
    print(chk_out, flush=True)


if __name__ == "__main__":
    main()

