"""Passo 1: coleta versoes e ambiente -> ambiente.txt (UTF-8, sem BOM)."""
import importlib.metadata as md
import os
import platform
import subprocess
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ambiente.txt")
lines = []


def add(k, v):
    lines.append(f"{k}: {v}")


add("python", sys.version.replace("\n", " "))
add("executable", sys.executable)
for pkg in ("mcp", "anyio", "scipy", "numpy", "scikit-learn", "torch", "transformers", "sentence-transformers", "chromadb", "psutil", "uvicorn", "starlette"):
    try:
        add(pkg, md.version(pkg))
    except md.PackageNotFoundError:
        add(pkg, "NAO INSTALADO")
add("platform", platform.platform())
add("windows_version", platform.version())


def ps(cmd):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        return (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa
        return f"ERRO: {e}"


add("os_caption_build", ps("(Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber | Format-List | Out-String).Trim()").replace("\r\n", " ; "))
add("defender_realtime", ps("try { (Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled,AntivirusEnabled,AMServiceEnabled,BehaviorMonitorEnabled,IoavProtectionEnabled | Format-List | Out-String).Trim() } catch { 'ERRO: ' + $_.Exception.Message }").replace("\r\n", " ; "))
add("antivirus_products", ps("try { (Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntivirusProduct | Select-Object displayName | Format-List | Out-String).Trim() } catch { 'ERRO: ' + $_.Exception.Message }").replace("\r\n", " ; "))
add("launch_context", "processo lancado pelo AGENTE (run_command da ferramenta), NAO por terminal interativo do dono")
add("stdin_isatty", sys.stdin.isatty() if sys.stdin else "sem stdin")
add("stdout_isatty", sys.stdout.isatty())
add("env_PROMPT_or_WT_SESSION", f"WT_SESSION={os.environ.get('WT_SESSION')!r} TERM_PROGRAM={os.environ.get('TERM_PROGRAM')!r}")
add("PYTHONPATH", os.environ.get("PYTHONPATH"))
add("OPENBLAS_NUM_THREADS", os.environ.get("OPENBLAS_NUM_THREADS"))
add("OMP_NUM_THREADS", os.environ.get("OMP_NUM_THREADS"))
add("git_head", subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip())

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print("escrito", OUT)

