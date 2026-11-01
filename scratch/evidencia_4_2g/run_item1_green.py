import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
VENV_DIR = Path(r"C:\Nexus-Memory\_venvs_4_2g\venv_min_no_ml")
PY_MIN = VENV_DIR / "Scripts" / "python.exe"
CLEAN_APPDATA = VENV_DIR / "clean_appdata"


def run_cmd(cmd, cwd=REPO_ROOT, env=None):
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
    # Save diff of tests/test_stdin_decouple.py
    _, diff_out = run_cmd(["git", "diff", "--no-color", "--", "tests/test_stdin_decouple.py"])
    (HERE / "item1_item4a_test_diff.txt").write_text(diff_out.strip() + "\n", encoding="utf-8")

    # 1d) GREEN in minimal venv (without scipy / sentence_transformers)
    clean_env = os.environ.copy()
    clean_env["APPDATA"] = str(CLEAN_APPDATA)
    clean_env["PYTHONNOUSERSITE"] = "1"
    rc_min, out_min = run_cmd(
        [PY_MIN, "-m", "pytest", "tests/test_stdin_decouple.py", "-q", "-rs"],
        env=clean_env,
    )
    (HERE / "item1_d_green_venv_min.txt").write_text(out_min.strip() + "\n", encoding="utf-8")
    print(f"=== 1d (venv_min_no_ml, rc={rc_min}) ===", flush=True)
    print(out_min, flush=True)

    # 1e) GREEN in main Windows venv (with scipy / sentence_transformers)
    rc_main, out_main = run_cmd(
        [sys.executable, "-m", "pytest", "tests/test_stdin_decouple.py", "-q"],
    )
    (HERE / "item1_d_green_main_venv.txt").write_text(out_main.strip() + "\n", encoding="utf-8")
    print(f"=== 1e (main venv, rc={rc_main}) ===", flush=True)
    print(out_main, flush=True)


if __name__ == "__main__":
    main()

