import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent


def main():
    # Ensure pure UTF-8 without BOM for git baseline files
    for fname in ["passo0_git_pull.txt", "passo0_head.txt", "passo0_ls_remote.txt", "passo0_git_status.txt"]:
        p = HERE / fname
        if p.exists():
            txt = p.read_text(encoding="utf-8-sig")
            p.write_text(txt, encoding="utf-8")

    outfile = HERE / "passo0_baseline_pytest.txt"
    print("Running pytest tests/ -q ...", flush=True)
    with outfile.open("w", encoding="utf-8") as f:
        p = subprocess.Popen(
            [sys.executable, "-u", "-m", "pytest", "tests/", "-q"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert p.stdout is not None
        for line in p.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            f.write(line)
            f.flush()
        rc = p.wait()
    print(f"pytest finished with returncode={rc}", flush=True)


if __name__ == "__main__":
    main()
