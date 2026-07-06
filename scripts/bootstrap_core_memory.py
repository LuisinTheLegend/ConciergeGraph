#!/usr/bin/env python
"""
scripts/bootstrap_core_memory.py — Grafo Concierge v3.8.0

Popular a tabela user_core_memory com informações de persona e regras de contexto 
padrão para o agente iniciar operacional e alinhado com as regras do projeto.
"""

import os
import sys
from dotenv import load_dotenv

# Garante o carregamento dos módulos do Grafo Concierge inserindo o caminho raiz no sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from storage import SqliteStore

# Definição do caminho do banco de dados (mesmo padrão do main.py)
DB_PATH = os.environ.get("GRAFO_DB_PATH", os.path.join(ROOT_DIR, "data", "concierge.db"))

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

    # Garante que o diretório de dados exista
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    try:
        store = SqliteStore(DB_PATH)
        print("SqliteStore inicializado com sucesso.")

        inserted_count = 0
        for mem in DEFAULT_MEMORIES:
            # Insere/atualiza os blocos padrão na tabela
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
