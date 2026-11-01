import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
VENV_DIR = Path(r"C:\Nexus-Memory\_venvs_4_2g\venv_min_no_ml")
PY_EXE = VENV_DIR / "Scripts" / "python.exe"
CLEAN_APPDATA = VENV_DIR / "clean_appdata"


def run_cmd(cmd, cwd=REPO_ROOT, env=None):
    print(f"Running: {' '.join(str(x) for x in cmd)}", flush=True)
    res = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd),
        env=env,
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
    VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
    CLEAN_APPDATA.mkdir(parents=True, exist_ok=True)

    clean_env = os.environ.copy()
    clean_env["APPDATA"] = str(CLEAN_APPDATA)
    clean_env["PYTHONNOUSERSITE"] = "1"

    # Save pip freeze with isolated user-site
    rc, freeze_out = run_cmd([PY_EXE, "-m", "pip", "freeze"], env=clean_env)
    (HERE / "item1_venv_min_pip_freeze.txt").write_text(freeze_out.strip() + "\n", encoding="utf-8")
    print("Saved item1_venv_min_pip_freeze.txt", flush=True)

    # 1b) RED: run pytest tests/test_stdin_decouple.py -q on current HEAD
    rc, red_out = run_cmd(
        [PY_EXE, "-m", "pytest", "tests/test_stdin_decouple.py", "-q"],
        env=clean_env,
    )
    (HERE / "item1_d5_red.txt").write_text(red_out.strip() + "\n", encoding="utf-8")
    print(f"Saved item1_d5_red.txt (rc={rc})", flush=True)
    print(red_out, flush=True)


if __name__ == "__main__":
    main()
