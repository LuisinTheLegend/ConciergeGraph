"""Teste de integração da Fase 4 — interface/ package."""

import sys

print("=== FASE 4: TESTE DE INTEGRACAO ===")
print()

# 1. Import MCP Server
from interface.mcp_server import GrafoConciergeServer
print("[1] GrafoConciergeServer importado OK")
print()

# 2. Import ActionHooks
from interface.action_hooks import ActionHooks
print("[2] ActionHooks importado OK")
print()

# 3. Import CLI
from interface.cli import build_parser, COMMAND_MAP
parser = build_parser()
print("[3] CLI parser construido OK")
print(f"    - Comandos disponíveis: {list(COMMAND_MAP.keys())}")
assert len(COMMAND_MAP) == 9, f"Esperava 9 comandos, obteve {len(COMMAND_MAP)}"
print()

# 4. Valida que o MCP Server aceita GrafoConcierge (verificacao de assinatura)
import inspect
sig = inspect.signature(GrafoConciergeServer.__init__)
params = list(sig.parameters.keys())
print("[4] GrafoConciergeServer.__init__ params:")
print(f"    - {params}")
assert "concierge" in params, "Esperava param 'concierge' (GrafoConcierge)"
assert "janitor" in params, "Esperava param 'janitor'"
# NÃO deve ter os params antigos (sqlite_store, vector_store, etc.)
assert "sqlite_store" not in params, "LEGADO: ainda recebe sqlite_store diretamente!"
assert "vector_store" not in params, "LEGADO: ainda recebe vector_store diretamente!"
assert "embedding_manager" not in params, "LEGADO: ainda recebe embedding_manager diretamente!"
print("    - Confirmado: nao recebe dependencias internas (refatoracao OK)")
print()

# 5. Valida que ActionHooks aceita GrafoConcierge + RevisorCritico
sig_hooks = inspect.signature(ActionHooks.__init__)
params_hooks = list(sig_hooks.parameters.keys())
print("[5] ActionHooks.__init__ params:")
print(f"    - {params_hooks}")
assert "concierge" in params_hooks, "Esperava param 'concierge'"
assert "revisor" in params_hooks, "Esperava param 'revisor'"
print()

# 6. Valida metodos do ActionHooks
hooks_methods = [m for m in dir(ActionHooks) if m.startswith("on_")]
print("[6] ActionHooks metodos de ciclo de vida:")
print(f"    - {hooks_methods}")
assert "on_planning" in hooks_methods, "Falta on_planning"
assert "on_execution" in hooks_methods, "Falta on_execution"
assert "on_done" in hooks_methods, "Falta on_done"
print()

# 7. Valida CLI subcomandos
subcommands = ["register", "mine", "search", "wakeup", "resume", "commit", "load", "status", "projects"]
for cmd in subcommands:
    assert cmd in COMMAND_MAP, f"Falta comando: {cmd}"
print(f"[7] CLI: todos os {len(subcommands)} subcomandos presentes OK")
print()

# 8. Valida que o CLI parser aceita os argumentos corretos
args = parser.parse_args(["search", "--query", "test", "--project", "abc123"])
assert args.command == "search"
assert args.query == "test"
assert args.project == "abc123"
print("[8] CLI parser: argumentos de 'search' parseados corretamente OK")
print()

# 9. Valida argumentos do mine
args_mine = parser.parse_args(["mine", "--path", "/tmp/proj", "--name", "meu-projeto"])
assert args_mine.command == "mine"
assert args_mine.path == "/tmp/proj"
assert args_mine.name == "meu-projeto"
print("[9] CLI parser: argumentos de 'mine' parseados corretamente OK")
print()

# 10. Import completo do package interface
from interface import GrafoConciergeServer, ActionHooks
print("[10] interface/__init__.py exports OK")
print()

print("=" * 50)
print("FASE 4: TODOS OS 10 TESTES PASSARAM!")
print("=" * 50)
