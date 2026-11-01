"""Bloco 0 Mutation Proof:
Demonstrates that if openai is omitted from the dev extra,
an environment installed without openai fails tests/test_llm_egress_guard.py (S1 to S8).
"""
import os
import pathlib
import subprocess
import sys

out_dir = pathlib.Path("scratch/evidencia_4_2i")
min_py = r"C:\Nexus-Memory\_venvs_4_2g\venv_min_no_ml\Scripts\python.exe"

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONNOUSERSITE"] = "1"
env["GRAFO_LLM_API_KEY"] = "AQ.FAKEFAKEFAKE0001"

r = subprocess.run(
    [min_py, "-m", "pytest", "tests/test_llm_egress_guard.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=env,
)

content = (
    f"# Mutacao Bloco 0: ambiente instalado sem o extra 'openai' (como ocorria no CI quando openai nao estava em dev/all)\n"
    f"# Comando: {min_py} -m pytest tests/test_llm_egress_guard.py -v --tb=short\n"
    f"[returncode={r.returncode}]\n"
    f"{r.stdout}\n{r.stderr}"
)
(out_dir / "b0_mut_remove_openai_from_dev.txt").write_text(content, encoding="utf-8")
print(f"Mutation proof saved to b0_mut_remove_openai_from_dev.txt (returncode={r.returncode})")

