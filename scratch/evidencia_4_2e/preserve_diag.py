"""Passo 0: copia scripts e dumps de diagnostico para scratch/evidencia_4_2e/diag/ e lista tamanho/data."""
import datetime
import glob
import os
import shutil
import tempfile

ART = r"C:\Users\guial\.gemini\antigravity\brain\74748901-a8f5-45d9-a8b8-d486be789891"
DEST = r"c:\Nexus-Memory\GrafoConcierge\scratch\evidencia_4_2e\diag"
os.makedirs(DEST, exist_ok=True)

items = []  # (src, destname)
for f in sorted(glob.glob(os.path.join(ART, "scratch", "*.py"))):
    items.append((f, os.path.basename(f)))

tmp = tempfile.gettempdir()
for pat, label in (("dump_mine_*", "dump_mine"), ("diag_stack_*", "diag_stack"), ("diag_search_first_*", "diag_cases"), ("diag_mine_first_*", "diag_cases")):
    for d in sorted(glob.glob(os.path.join(tmp, pat))):
        if os.path.isdir(d):
            for name in ("stacks.txt", "stderr.txt", "stderr.log"):
                p = os.path.join(d, name)
                if os.path.exists(p):
                    items.append((p, f"out__{os.path.basename(d)}__{name}"))
for f in sorted(glob.glob(os.path.join(ART, ".system_generated", "tasks", "task-*.log"))):
    items.append((f, f"tasklog__{os.path.basename(f)}"))

lines = ["arquivo_destino | tamanho_bytes | mtime_origem | origem"]
for src, name in items:
    if os.path.getsize(src) == 0:
        continue
    shutil.copy2(src, os.path.join(DEST, name))
    st = os.stat(src)
    lines.append(f"{name} | {st.st_size} | {datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')} | {src}")

with open(os.path.join(DEST, "LISTA_ARQUIVOS.txt"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print(len(lines) - 1, "arquivos copiados")
