import subprocess
import time
from pathlib import Path

ROOT = Path(r"C:\Nexus-Memory\GrafoConcierge")
PY312 = ROOT / ".venv_312" / "Scripts" / "python.exe"
OUT = ROOT / "scratch" / "evidencia_4_5c_ter" / "task1_zombie_proof.txt"
TEST_FILE = ROOT / "tests" / "test_alias_tracker.py"
TARGET_METHOD = "test_should_purge_zombie_node_when_buffer_timeout_expires"

RUNNER_CODE = "\n".join([
    "import sys, time, pytest",
    "from core.database import ConciergeDatabaseManager",
    "delay = float(sys.argv[1])",
    "target = sys.argv[2]",
    "_orig = ConciergeDatabaseManager.execute_write",
    "def _delayed(self, query, params=()):",
    "    if delay > 0 and 'DELETE FROM files' in query:",
    "        time.sleep(delay)",
    "    return _orig(self, query, params)",
    "ConciergeDatabaseManager.execute_write = _delayed",
    "raise SystemExit(pytest.main([target, '-v', '--tb=short']))",
])


def run_with_delay(test_path: str, delay_s: float) -> tuple[int, str, float]:
    target = f"{test_path}::TestAliasTracker::{TARGET_METHOD}"
    cmd = [str(PY312), "-c", RUNNER_CODE, str(delay_s), target]
    t0 = time.monotonic()
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    dt = time.monotonic() - t0
    out = f"$ delay={delay_s}s target={target}\nexit_code={p.returncode} elapsed={dt:.2f}s\n{p.stdout.strip()}"
    if p.stderr.strip():
        out += f"\n[stderr]\n{p.stderr.strip()}"
    return p.returncode, out, dt


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    log: list[str] = ["=== TASK 1 PROOFS (a), (b), (c), (d) ==="]

    # (a) Old test from 43ea935 under 0.0, 0.05, 0.12, 0.2s DELETE latency
    log.append("\n--- (a) ANTES: git show 43ea935:tests/test_alias_tracker.py ---")
    old_bytes = subprocess.check_output(
        ["git", "show", "43ea935:tests/test_alias_tracker.py"], cwd=ROOT
    )
    old_tmp = ROOT / "tests" / "_tmp_old_alias_4_5c_ter.py"
    try:
        old_tmp.write_bytes(old_bytes)
        for d in (0.0, 0.05, 0.12, 0.2):
            rc, out, _ = run_with_delay(f"tests/{old_tmp.name}", d)
            log.append(out)
            if d < 0.2:
                assert rc == 0, f"Expected pass at delay={d}s, got {rc}"
            else:
                assert rc != 0, f"Expected FAIL at delay={d}s on old test, got {rc}"
    finally:
        old_tmp.unlink(missing_ok=True)

    # (b) New test under 0.2s and 1.0s DELETE latency
    log.append("\n--- (b) DEPOIS: teste novo com latencia 0.2s e 1.0s ---")
    for d in (0.2, 1.0):
        rc, out, _ = run_with_delay("tests/test_alias_tracker.py", d)
        log.append(out)
        assert rc == 0, f"Expected new test to PASS at delay={d}s, got {rc}"

    # (c) Mutation: remove DELETE from _handle_purge -> new test must FAIL (~5s timeout)
    log.append("\n--- (c) MUTACAO: remover DELETE de _handle_purge ---")
    orig_test_bytes = TEST_FILE.read_bytes()
    delete_line = '        self.db_manager.write_query("DELETE FROM files WHERE path = ?;", (rel_path,))'
    try:
        text = orig_test_bytes.decode("utf-8")
        assert delete_line in text, "Expected DELETE line not found in tests/test_alias_tracker.py"
        mutated = text.replace(delete_line, "        pass  # MUTACAO: DELETE removido", 1)
        TEST_FILE.write_bytes(mutated.encode("utf-8"))
        rc_m, out_m, dt_m = run_with_delay("tests/test_alias_tracker.py", 0.0)
        log.append(out_m)
        assert rc_m != 0, "Expected mutated _handle_purge (no DELETE) to FAIL!"
        assert dt_m >= 4.5, f"Expected timeout wait ~5s, finished too fast ({dt_m:.2f}s)"
    finally:
        TEST_FILE.write_bytes(orig_test_bytes)

    p_diff = subprocess.run(
        ["git", "diff", "tests/test_alias_tracker.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.append("\n--- DIFF DE tests/test_alias_tracker.py APOS RESTAURACAO ---")
    log.append(p_diff.stdout.strip())

    # (d) 30 consecutive runs of the new isolated test
    log.append("\n--- (d) ESTABILIDADE: 30 execucoes seguidas ---")
    failures = 0
    timings: list[float] = []
    target_rel = f"tests/test_alias_tracker.py::TestAliasTracker::{TARGET_METHOD}"
    for i in range(1, 31):
        t0 = time.monotonic()
        p = subprocess.run(
            [str(PY312), "-m", "pytest", target_rel, "-q", "--tb=short"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        dt = time.monotonic() - t0
        timings.append(dt)
        if p.returncode != 0:
            failures += 1
            log.append(f"Run {i}/30 FAILED (rc={p.returncode}):\n{p.stdout}\n{p.stderr}")
    log.append(
        f"30/30 runs summary: falhas={failures}/30, "
        f"min={min(timings):.2f}s, max={max(timings):.2f}s, avg={sum(timings)/len(timings):.2f}s"
    )
    assert failures == 0, f"Had {failures}/30 failures!"

    OUT.write_text("\n".join(log) + "\n", encoding="utf-8")
    print("Task 1 zombie proof finished OK.")


if __name__ == "__main__":
    main()
