"""
tests/test_project_index.py — Status da Suíte de ProjectIndex (Pós-Aposentadoria de categorize_project)

Os testes antigos de categorização automática (TestProjectIndexCategorize) testavam a função
`categorize_project`, que foi aposentada e removida em definitivo por decisão do proprietário:
- Decisão registrada em audits/fase4-decisoes.md:27-31 (Item 4: Remoção Definitiva do Dicionário de Alas)
- Diretrizes de execução em audits/fase4-decisoes.md:92 (Item 7: Diretrizes de Execução)

A categorização automática por palavras-chave fixas de domínio violava a neutralidade de domínio
do Grafo Concierge. A gerência de alas agora é estritamente explícita (definida no cadastro ou via
update_project).

Lacuna de teste identificada via grep:
A gerência de alas no ProjectIndex (set_primary_wing, get_reference_wings, add_reference_wing,
remove_reference_wing, find_similar_projects) possui cobertura de integração via MCP handlers em
`tests/test_mcp_server_handlers.py:396-410`, porém não possui testes unitários isolados diretos
na classe ProjectIndex. Conforme instrução do protocolo da Rodada 4.4, essa lacuna é registrada
formalmente sem invenção de novos testes arbitrários nesta rodada.
"""

from core import ProjectIndex


def test_project_index_has_no_automatic_categorization():
    """Garante que ProjectIndex não expõe mais os métodos aposentados de categorização automática."""
    assert not hasattr(ProjectIndex, "categorize_project"), "categorize_project deve ser removido de ProjectIndex"
    assert not hasattr(ProjectIndex, "auto_categorize_project"), "auto_categorize_project deve ser removido de ProjectIndex"
