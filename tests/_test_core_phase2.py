"""Teste de integração rápido da Fase 2 — core/ package."""

from core import GrafoConcierge, ConciergeConfig, ProjectIndex, HybridSearchEngine
from core.config import DEFAULT_CONFIG

print("=== FASE 2: TESTE DE INTEGRACAO ===")
print()

# 1. Config
cfg = DEFAULT_CONFIG
print("[1] ConciergeConfig OK")
print(f"    - weight_vector: {cfg.weight_vector}")
print(f"    - weight_fts5: {cfg.weight_fts5}")
print(f"    - recency_lambda: {cfg.recency_lambda:.5f}")
print(f"    - alas definidas: {list(cfg.wing_keywords.keys())}")
print()

# 2. ProjectIndex - categorize standalone
pi_standalone = ProjectIndex.__new__(ProjectIndex)
pi_standalone._config = cfg
pi_standalone._store = None
wing = pi_standalone.categorize_project(
    labels=["api_vendas.py", "landing_page.html", "copy_email.txt"],
    tags=["marketing", "copy", "CTA"],
)
print("[2] ProjectIndex.categorize_project OK")
print(f'    - Input: marketing + landing + copy')
print(f'    - Resultado: "{wing}"')
assert wing == "marketing/vendas", f"Esperava marketing/vendas, obteve {wing}"
print()

# 3. Teste categorizacao financas
wing2 = pi_standalone.categorize_project(
    labels=["robo_daytrade.py", "crypto_wallet.ts"],
    tags=["trade", "crypto", "investimento"],
)
print("[3] Categorizacao financas OK")
print(f'    - Input: daytrade + crypto + investimento')
print(f'    - Resultado: "{wing2}"')
assert wing2 == "finanças/quant", f"Esperava financas/quant, obteve {wing2}"
print()

# 4. Teste categorizacao default
wing3 = pi_standalone.categorize_project(
    labels=["arquivo_aleatorio.xyz"],
    tags=[],
)
print("[4] Categorizacao geral (fallback) OK")
print(f'    - Input: nenhuma keyword')
print(f'    - Resultado: "{wing3}"')
assert wing3 == "geral", f"Esperava geral, obteve {wing3}"
print()

print("=" * 50)
print("FASE 2: TODOS OS 4 TESTES PASSARAM!")
print("=" * 50)
