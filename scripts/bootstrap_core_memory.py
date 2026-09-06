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
            "You are Concierge Graph, an intelligent software engineering agent "
            "and long-term architectural memory. You pair-program with the user "
            "and manage source-code knowledge graphs of complex systems."
        )
    },
    {
        "scope_type": "agent",
        "scope_id": "concierge",
        "block_label": "context_rules",
        "content": (
            "Rule 1: Absolute Zero Technical Debt. Never introduce hacks or violate encapsulations.\n"
            "Rule 2: Secret Shielding. Never store API keys in plaintext in JSON files or version control.\n"
            "Rule 3: Fail-Fast Validation at MCP API boundaries.\n"
            "Rule 4: Database Connection Resilience (retry with backoff)."
        )
    }
]

def main() -> None:
    print("=" * 60)
    print("  Concierge Graph — Core Memory Bootstrap")
    print("=" * 60)
    print(f"Database: {DB_PATH}")

    # Ensures the data directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    try:
        store = SqliteStore(DB_PATH)
        print("SqliteStore initialized successfully.")

        inserted_count = 0
        for mem in DEFAULT_MEMORIES:
            # Inserts/updates default blocks in the table
            store.set_core_memory(
                scope_type=mem["scope_type"],
                scope_id=mem["scope_id"],
                block_label=mem["block_label"],
                content=mem["content"]
            )
            print(f"  [+] Block '{mem['block_label']}' registered for '{mem['scope_type']}/{mem['scope_id']}'.")
            inserted_count += 1

        store.close()
        print("=" * 60)
        print(f"Success: {inserted_count} default memory blocks registered.")
        print("=" * 60)
        sys.exit(0)

    except Exception as e:
        print(f"[-] Critical error during bootstrap: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
