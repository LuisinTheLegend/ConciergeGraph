import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Nexus-Memory\GrafoConcierge")
PY312 = ROOT / ".venv_312" / "Scripts" / "python.exe"
OUT = ROOT / "scratch" / "evidencia_4_5c_bis" / "task1_wheel_proof.txt"
PYPROJECT = ROOT / "pyproject.toml"


def clean_build_artifacts(log: list[str], label: str) -> None:
    for name in ("build", "dist"):
        p = ROOT / name
        if p.exists():
            shutil.rmtree(p)
            log.append(f"[{label}] Removed {p.name}/")
    for egg in ROOT.glob("*.egg-info"):
        if egg.is_dir():
            shutil.rmtree(egg)
        else:
            egg.unlink()
        log.append(f"[{label}] Removed {egg.name}")


def check_root_clean() -> dict:
    eggs = [p.name for p in ROOT.glob("*.egg-info")]
    return {
        "build_exists": (ROOT / "build").exists(),
        "build_lib_exists": (ROOT / "build" / "lib").exists(),
        "egg_info": eggs,
    }


def run_cmd(cmd: list[str], cwd: Path = ROOT) -> tuple[int, str]:
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    out = f"$ {' '.join(cmd)}\nexit_code={proc.returncode}\n{proc.stdout}"
    if proc.stderr.strip():
        out += f"\n[stderr]\n{proc.stderr}"
    return proc.returncode, out


def main() -> None:
    log: list[str] = ["=== TASK 1 PROOFS (a), (b), (c) ==="]
    orig_pyproject_bytes = PYPROJECT.read_bytes()

    try:
        # Prepare clean root for Case (b)
        clean_build_artifacts(log, "pre-b")
        log.append("\n--- CASE (b): Fixed test leaves zero build/ or *.egg-info ---")
        log.append(f"Before test: {check_root_clean()}")
        rc_b, out_b = run_cmd([str(PY312), "-m", "pytest", "tests/test_wheel_integrity.py", "-v", "--tb=short"])
        log.append(out_b.strip())
        after_b = check_root_clean()
        log.append(f"After test:  {after_b}")
        assert rc_b == 0, f"Case (b) failed: exit_code={rc_b}"
        assert not after_b["build_exists"] and not after_b["egg_info"], f"Polluted root in (b): {after_b}"

        # Create pre-existing build/lib/ in repo root (simulating dirty tree)
        log.append("\n--- SETUP: Create build/lib/ on repo root ---")
        with tempfile.TemporaryDirectory() as dist_tmp:
            rc_bld, out_bld = run_cmd(
                [str(PY312), "-c", f"from setuptools import build_meta; print(build_meta.build_wheel({dist_tmp!r}))"],
                cwd=ROOT,
            )
            log.append(out_bld.strip())
            assert rc_bld == 0, "Failed to generate build/lib/ in repo root"
        setup_state = check_root_clean()
        log.append(f"Root state after build_wheel: {setup_state}")
        log.append(
            f"build/lib/services exists: {(ROOT / 'build' / 'lib' / 'services').is_dir()}, "
            f"build/lib/storage exists: {(ROOT / 'build' / 'lib' / 'storage').is_dir()}"
        )

        # Case (c): Run old f66259c test under M1 with build/ present
        log.append("\n--- CASE (c): Old test (f66259c) under M1 ('services*' removed) with build/ present ---")
        rc_show, old_test_src = run_cmd(["git", "show", "f66259c:tests/test_wheel_integrity.py"])
        assert rc_show == 0, "Failed git show f66259c:tests/test_wheel_integrity.py"
        # git show output wrapped by run_cmd has header lines; fetch raw stdout directly
        raw_old = subprocess.check_output(
            ["git", "show", "f66259c:tests/test_wheel_integrity.py"], cwd=ROOT
        )
        old_tmp_test = ROOT / "tests" / "_tmp_old_wheel_4_5c_bis.py"
        try:
            old_tmp_test.write_bytes(raw_old)
            orig_text = orig_pyproject_bytes.decode("utf-8")
            assert '"services*",' in orig_text, 'Pattern "services*", not found in pyproject.toml'
            m1_text = orig_text.replace('"services*",', "", 1)
            PYPROJECT.write_bytes(m1_text.encode("utf-8"))
            rc_c, out_c = run_cmd(
                [str(PY312), "-m", "pytest", f"tests/{old_tmp_test.name}", "-v", "--tb=short"]
            )
            log.append(out_c.strip())
            log.append(f"OBSERVED CASE (c) EXIT CODE: {rc_c}")
        finally:
            PYPROJECT.write_bytes(orig_pyproject_bytes)
            old_tmp_test.unlink(missing_ok=True)

        # Case (a): Fixed test under M1 and M2 with pre-existing build/lib/ in repo root
        log.append("\n--- CASE (a): Fixed test under M1 ('services*' removed) with build/lib/ present ---")
        orig_text = orig_pyproject_bytes.decode("utf-8")
        try:
            PYPROJECT.write_bytes(orig_text.replace('"services*",', "", 1).encode("utf-8"))
            rc_a1, out_a1 = run_cmd([str(PY312), "-m", "pytest", "tests/test_wheel_integrity.py", "-v", "--tb=short"])
            log.append(out_a1.strip())
            assert rc_a1 != 0, "Expected M1 to FAIL on fixed test!"
        finally:
            PYPROJECT.write_bytes(orig_pyproject_bytes)

        log.append("\n--- CASE (a): Fixed test under M2 ('storage*' removed) with build/lib/ present ---")
        try:
            assert '"storage*",' in orig_text, 'Pattern "storage*", not found in pyproject.toml'
            PYPROJECT.write_bytes(orig_text.replace('"storage*",', "", 1).encode("utf-8"))
            rc_a2, out_a2 = run_cmd([str(PY312), "-m", "pytest", "tests/test_wheel_integrity.py", "-v", "--tb=short"])
            log.append(out_a2.strip())
            assert rc_a2 != 0, "Expected M2 to FAIL on fixed test!"
        finally:
            PYPROJECT.write_bytes(orig_pyproject_bytes)

        log.append("\n--- CASE (a): Fixed test AFTER restoring pyproject.toml ---")
        rc_a3, out_a3 = run_cmd([str(PY312), "-m", "pytest", "tests/test_wheel_integrity.py", "-v", "--tb=short"])
        log.append(out_a3.strip())
        assert rc_a3 == 0, "Expected fixed test to PASS after restoring pyproject.toml!"

        rc_diff, out_diff = run_cmd(["git", "diff", "--", "pyproject.toml"])
        log.append(f"\n$ git diff -- pyproject.toml (len={len(out_diff.splitlines()) - 2}):")
        log.append(out_diff.strip())
    finally:
        PYPROJECT.write_bytes(orig_pyproject_bytes)
        clean_build_artifacts(log, "cleanup")
        log.append(f"Final root state: {check_root_clean()}")

    OUT.write_text("\n".join(log) + "\n", encoding="utf-8")
    print("Task 1 proof script finished OK.")


if __name__ == "__main__":
    main()
