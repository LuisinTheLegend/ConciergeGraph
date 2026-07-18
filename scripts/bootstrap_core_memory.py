#!/usr/bin/env python
"""
scripts/bootstrap_core_memory.py — Grafo Concierge v3.8.0

Populate the user_core_memory table with persona information and default
context rules so that the agent starts operational and aligned with project guidelines.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensures loading of Grafo Concierge modules by inserting the root directory path into sys.path
ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

load_dotenv(str(ROOT_DIR / ".env"))

from storage import SqliteStore

def resolve_project_path(env_value: str, default_rel: str) -> str:
    val = env_value or default_rel
    path = Path(val)
    if path.is_absolute():
        return str(path)
    return str((ROOT_DIR / path).resolve())

DB_PATH = resolve_project_path(os.environ.get("GRAFO_DB_PATH", ""), "data/concierge.db")

DEFAULT_MEMORIES = [
    {
        "scope_type": "agent",
        "scope_id": "concierge",
        "block_label": "persona",
        "content": (
            "Você é o Grafo Concierge, um agente inteligente de engenharia de software "
            "e memória arquitetural de longo prazo. Você pair-programa com o usuário "
            "e gerencia grafos de código-fonte de sistemas complexos."
        )
    },
    {
        "scope_type": "agent",
        "scope_id": "concierge",
        "block_label": "context_rules",
        "content": (
            "Regra 1: Dívida Técnica Zero Absoluta. Nunca introduzir hacks ou violar encapsulamentos.\n"
            "Regra 2: Blindagem de Segredos. Nunca deixar chaves de API em texto plano em arquivos JSON ou versionados.\n"
            "Regra 3: Validação Fail-Fast nas bordas da API MCP.\n"
            "Regra 4: Resiliência em conexões de banco de dados (retry com backoff)."
        )
    }
]

def main() -> None:
    print("=" * 60)
    print("  Grafo Concierge — Bootstrap da Core Memory")
    print("=" * 60)
    print(f"Banco de dados: {DB_PATH}")

    # Ensures the data directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    try:
        store = SqliteStore(DB_PATH)
        print("SqliteStore inicializado com sucesso.")

        inserted_count = 0
        for mem in DEFAULT_MEMORIES:
            # Inserts/updates default blocks in the table
            store.set_core_memory(
                scope_type=mem["scope_type"],
                scope_id=mem["scope_id"],
                block_label=mem["block_label"],
                content=mem["content"]
            )
            print(f"  [+] Bloco '{mem['block_label']}' registrado para '{mem['scope_type']}/{mem['scope_id']}'.")
            inserted_count += 1

        store.close()
        print("=" * 60)
        print(f"Sucesso: {inserted_count} blocos de memória padrão registrados.")
        print("=" * 60)
        sys.exit(0)

    except Exception as e:
        print(f"[-] Erro crítico durante o bootstrap: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
