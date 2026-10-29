"""
save_venv_versions.py - Salva as versões reais instaladas em cada venv em arquivos de evidência.
"""
from pathlib import Path
import subprocess
import sys

EV_DIR = Path(r"c:\Nexus-Memory\GrafoConcierge\scratch\evidencia_4_2e")
VENVS = {
    "mcp127": r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe",
    "mcp130": r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp130\Scripts\python.exe",
}

out_lines = []
for name, py_exe in VENVS.items():
    cmd = [py_exe, "-c", "import importlib.metadata as m; print(m.version('mcp'))"]
    ver = subprocess.check_output(cmd, text=True).strip()
    out_lines.append(f"venv_{name}: mcp real = {ver} (executavel: {py_exe})")
    (EV_DIR / f"versao_real_{name}.txt").write_text(f"{ver}\n", encoding="utf-8")

txt = "\n".join(out_lines) + "\n"
(EV_DIR / "versoes_venvs_reais.txt").write_text(txt, encoding="utf-8")
print(txt)

