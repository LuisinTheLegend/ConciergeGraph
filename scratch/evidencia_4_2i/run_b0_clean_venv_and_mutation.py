"""Run Bloco 0 clean venv install + pytest + mutation (removing openai from dev)."""
import os
import pathlib
import subprocess
import sys

out_dir = pathlib.Path("scratch/evidencia_4_2i")
venv_py = r"C:\Nexus-Memory\_venvs_4_2i\venv_py314_clean\Scripts\python.exe"
pyproject = pathlib.Path("pyproject.toml")
orig_pyproject = pyproject.read_bytes()

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONNOUSERSITE"] = "1"
env["GRAFO_LLM_API_KEY"] = "AQ.FAKEFAKEFAKE0001"

print("[1/4] Installing pip install -e '.[dev]' in venv_py314_clean...")
r_inst = subprocess.run(
    [venv_py, "-m", "pip", "install", "-e", ".[dev]"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=env,
)
print(f"pip install rc={r_inst.returncode}")

print("[2/4] Running full pytest -v --tb=short in venv_py314_clean...")
r_test = subprocess.run(
    [venv_py, "-m", "pytest", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=env,
)
print(f"pytest rc={r_test.returncode}")
(out_dir / "b0_clean_venv_py314.txt").write_text(
    f"$ {venv_py} -m pip install -e \".[dev]\"\n[returncode={r_inst.returncode}]\n"
    f"{r_inst.stdout[-3000:]}\n{r_inst.stderr}\n"
    f"=================================================================\n"
    f"$ {venv_py} -m pytest -v --tb=short\n[returncode={r_test.returncode}]\n"
    f"{r_test.stdout}{r_test.stderr}",
    encoding="utf-8",
)

print("[3/4] Running Mutation: remove openai from dev extra in pyproject.toml...")
try:
    mut_text = orig_pyproject.decode("utf-8").replace(
        '    "google-genai>=0.1.0",\r\n    "openai>=1.0",\r\n]',
        '    "google-genai>=0.1.0",\r\n]',
        1,
    )
    assert mut_text != orig_pyproject.decode("utf-8"), "Mutation replacement failed"
    pyproject.write_bytes(mut_text.encode("utf-8"))

    subprocess.run([venv_py, "-m", "pip", "uninstall", "-y", "openai"], capture_output=True, env=env)
    r_mut_inst = subprocess.run(
        [venv_py, "-m", "pip", "install", "--no-deps", "-e", ".[dev]"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    r_mut_test = subprocess.run(
        [venv_py, "-m", "pytest", "tests/test_llm_egress_guard.py", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    print(f"mutation pytest rc={r_mut_test.returncode}")
    (out_dir / "b0_mut_remove_openai_from_dev.txt").write_text(
        f"# Mutacao Bloco 0: remover 'openai>=1.0' do extra [project.optional-dependencies].dev em pyproject.toml\n"
        f"# e desinstalar openai no venv limpo (PYTHONNOUSERSITE=1)\n"
        f"$ {venv_py} -m pytest tests/test_llm_egress_guard.py -v --tb=short\n"
        f"[returncode={r_mut_test.returncode}]\n{r_mut_test.stdout}{r_mut_test.stderr}",
        encoding="utf-8",
    )
finally:
    pyproject.write_bytes(orig_pyproject)
    print("[4/4] Restoring pyproject.toml and reinstalling openai in venv_py314_clean...")
    subprocess.run([venv_py, "-m", "pip", "install", "-e", ".[dev]"], capture_output=True, env=env)

print("Done!")

