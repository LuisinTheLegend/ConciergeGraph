"""Teste de integração da Fase 3 — agents/ package (RevisorCritico)."""

from agents.revisor_critico import RevisorCritico, AuditResult, RerankResult
from core.config import DEFAULT_CONFIG

print("=== FASE 3: TESTE DE INTEGRACAO ===")
print()

# 1. Import e inicialização (modo heurístico, sem LLM)
revisor = RevisorCritico(llm_adapter=None, config=DEFAULT_CONFIG)
print("[1] RevisorCritico inicializado (modo heuristico) OK")
print()

# 2. Auditoria — commit válido
draft_ok = {
    "phase": "build",
    "technical_changes": "Implementado endpoint /api/users com autenticacao JWT e middleware de rate limiting.",
    "updated_pointers": ["src/routes/users.py", "src/middleware/auth.py"],
    "source_wing": "gestao/saas",
}
result = revisor.audit(draft_ok)
print("[2] Auditoria commit valido:")
print(f"    - approved: {result.approved}")
print(f"    - reason: {result.reason}")
assert result.approved is True, f"Esperava aprovacao, obteve: {result.reason}"
print()

# 3. Auditoria — commit com technical_changes vazio
draft_empty = {
    "phase": "build",
    "technical_changes": "",
    "updated_pointers": ["file.py"],
}
result2 = revisor.audit(draft_empty)
print("[3] Auditoria commit technical_changes vazio:")
print(f"    - approved: {result2.approved}")
print(f"    - reason: {result2.reason}")
assert result2.approved is False, "Esperava rejeicao"
print()

# 4. Auditoria — commit sem pointers
draft_no_ptrs = {
    "phase": "review",
    "technical_changes": "Corrigido bug no parser de CSV que causava truncamento em linhas com aspas.",
    "updated_pointers": [],
}
result3 = revisor.audit(draft_no_ptrs)
print("[4] Auditoria commit sem pointers:")
print(f"    - approved: {result3.approved}")
print(f"    - reason: {result3.reason}")
assert result3.approved is False, "Esperava rejeicao"
print()

# 5. Auditoria — commit com technical_changes muito curto
draft_short = {
    "phase": "done",
    "technical_changes": "fix bug",
    "updated_pointers": ["x.py"],
}
result4 = revisor.audit(draft_short)
print("[5] Auditoria commit technical_changes curto:")
print(f"    - approved: {result4.approved}")
print(f"    - reason: {result4.reason}")
assert result4.approved is False, "Esperava rejeicao (< 10 chars)"
print()

# 6. audit_with_retry — fallback partial_audit
attempt_counter = {"count": 0}
def fake_regenerate(feedback):
    attempt_counter["count"] += 1
    # Sempre gera rascunho invalido
    return {
        "phase": "build",
        "technical_changes": "bad",
        "updated_pointers": [],
    }

result5 = revisor.audit_with_retry(
    draft=draft_short,
    generate_fn=fake_regenerate,
)
print("[6] audit_with_retry (3 rejeicoes -> partial_audit):")
print(f"    - approved: {result5.approved}")
print(f"    - partial_audit: {result5.partial_audit}")
print(f"    - loop_count: {result5.loop_count}")
assert result5.approved is True, "Esperava aprovacao por partial_audit"
assert result5.partial_audit is True, "Esperava partial_audit=True"
print()

# 7. Reranking heuristico
candidates = [
    {"node_id": 1, "score_final": 0.95, "score_breakdown": {"vetorial": 0.9}},
    {"node_id": 2, "score_final": 0.85, "score_breakdown": {"vetorial": 0.8}},
    {"node_id": 3, "score_final": 0.40, "score_breakdown": {"vetorial": 0.3}},
    {"node_id": 4, "score_final": 0.15, "score_breakdown": {"vetorial": 0.1}},
    {"node_id": 5, "score_final": 0.05, "score_breakdown": {"vetorial": 0.0}},
]

reranked = revisor.rerank(candidates, task_context="autenticacao JWT com refresh tokens")
print("[7] Reranking heuristico:")
print(f"    - Input: {len(candidates)} candidatos")
print(f"    - Output: {len(reranked)} aprovados")
print(f"    - Node IDs aprovados: {[c['node_id'] for c in reranked]}")
assert len(reranked) >= 1, "Deve ter pelo menos 1 resultado"
assert len(reranked) < len(candidates), "Deve ter filtrado ao menos 1"
print()

# 8. Barreira de Contaminacao
source_restricted = {"folder_name": "projeto-secreto", "privacy_level": "RESTRICTED"}
target_public = {"folder_name": "blog-publico", "privacy_level": "PUBLIC"}
is_safe, reason = revisor.check_contamination(source_restricted, target_public)
print("[8] Barreira de Contaminacao (RESTRICTED -> PUBLIC):")
print(f"    - is_safe: {is_safe}")
print(f"    - reason: {reason[:80]}...")
assert is_safe is False, "Esperava bloqueio"
print()

# 9. Contaminacao OK (PUBLIC -> INTERNAL)
source_public = {"folder_name": "lib-opensource", "privacy_level": "PUBLIC"}
target_internal = {"folder_name": "projeto-interno", "privacy_level": "INTERNAL"}
is_safe2, reason2 = revisor.check_contamination(source_public, target_internal)
print("[9] Contaminacao OK (PUBLIC -> INTERNAL):")
print(f"    - is_safe: {is_safe2}")
assert is_safe2 is True, "Esperava aprovacao"
print()

# 10. Rerank com lista vazia
empty_rerank = revisor.rerank([], task_context="qualquer coisa")
print("[10] Rerank com lista vazia:")
print(f"    - Output: {len(empty_rerank)} resultados")
assert empty_rerank == [], "Esperava lista vazia"
print()

print("=" * 50)
print("FASE 3: TODOS OS 10 TESTES PASSARAM!")
print("=" * 50)
