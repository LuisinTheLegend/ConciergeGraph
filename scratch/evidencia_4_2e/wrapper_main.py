# scratch/evidencia_4_2e/wrapper_main.py
"""
Wrapper para o servidor de producao Grafo Concierge.
Aplica a tecnica vencedora sem alterar nenhum arquivo de producao.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TECHNIQUE = os.environ.get("CONCIERGE_WRAPPER_TECHNIQUE", "decouple_fd0")

if TECHNIQUE == "decouple_fd0":
    nul = os.open(os.devnull, os.O_RDONLY)
    fd2 = os.dup(0)
    os.dup2(nul, 0)
    sys.stdin = open(fd2, "r", encoding="utf-8", errors="replace", closefd=False)

elif TECHNIQUE == "preimport":
    import sentence_transformers

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import main

if __name__ == "__main__":
    main.main()
