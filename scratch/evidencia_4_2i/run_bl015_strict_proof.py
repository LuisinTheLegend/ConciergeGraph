"""Prove BL-015 xfail(strict=True) behavior: XFAIL when bug is present, XPASS(strict) failure when BL-015 is fixed."""
import os
import pathlib
import subprocess
import sys

out_dir = pathlib.Path("scratch/evidencia_4_2i")
gov_path = pathlib.Path("core/mcp_governor.py")
orig_bytes = gov_path.read_bytes()

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["GRAFO_LLM_API_KEY"] = "AQ.FAKEFAKEFAKE0001"

# 1. With BL-015 open (default_state='EXECUTION')
r1 = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_progressive_tool_disclosure.py", "-v", "-rxX"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=env,
)
(out_dir / "b0_bl015_xfail_active.txt").write_text(
    f"$ pytest tests/test_progressive_tool_disclosure.py -v -rxX\n[returncode={r1.returncode}]\n{r1.stdout}{r1.stderr}",
    encoding="utf-8",
)

# 2. Simulate fixing BL-015 in core/mcp_governor.py (changing default "EXECUTION" -> "PLANNING")
try:
    patched = orig_bytes.decode("utf-8").replace(
        'os.environ.get("GRAFO_DEFAULT_STATE", "EXECUTION")',
        'os.environ.get("GRAFO_DEFAULT_STATE", "PLANNING")',
        1,
    )
    gov_path.write_bytes(patched.encode("utf-8"))
    r2 = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_progressive_tool_disclosure.py", "-v", "-rxX"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    (out_dir / "b0_bl015_xpass_strict_proof.txt").write_text(
        f"# Mutacao temporaria: core/mcp_governor.py:37 default 'EXECUTION' -> 'PLANNING' (simulando correcao do BL-015)\n"
        f"$ pytest tests/test_progressive_tool_disclosure.py -v -rxX\n[returncode={r2.returncode}]\n{r2.stdout}{r2.stderr}",
        encoding="utf-8",
    )
finally:
    gov_path.write_bytes(orig_bytes)

print(f"r1.returncode={r1.returncode} (expected 0), r2.returncode={r2.returncode} (expected 1 - XPASS strict)")

