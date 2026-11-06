# Errata Oficial — Relatório Rodada 4.3

**Data de Emissão:** 2026-11-06  
**Referência:** `audits/relatorio_4_3.md`  
**Escopo:** Retificação técnica e documental dos apontamentos da auditoria independente sobre a Rodada 4.3.  
**Regras do Protocolo:** Regras 2, 4, 10, 11, 12, 13 e 14 do `AUDIT_PROTOCOL.md`.  
**Arquivo de Evidência:** `scratch/evidencia_4_3b/item5_errata_greps.txt`.

---

## 1. Discrepância de Nomes de Parâmetros e Assinatura de `concierge_get_call_chain`

- **Texto anterior no relatório 4.3 (verbatim):**  
  Em `audits/relatorio_4_3.md`, linha 23:
  ```text
  - **Mecanismo:** A ferramenta aceita `project_id` ou `project_name`. Se não fornecido e o identificador (`symbol_or_path`) existir em múltiplos projetos ativos, a execução **rejeita a consulta com `ValueError` descritivo**, exigindo a especificação do projeto.
  ```
  *(evidência de extração por comando em `scratch/evidencia_4_3b/item5_errata_greps.txt` sob `grep_relatorio_4_3_line23`).*

- **Retificação Factual (4.3b):**
  - A ferramenta `concierge_get_call_chain` e o método subjacente `GraphRAGEngine.get_call_chain_recursive` **não possuem parâmetros denominados `project_id`, `project_name` ou `symbol_or_path`**.
  - As assinaturas reais e canônicas no código-fonte são:
    - MCP Tool ([`interface/mcp_server.py:873-877`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L873-L877)):
      ```python
      def tool_concierge_get_call_chain(
          start_node: str,
          depth_limit: int = 5,
          project_identifier: Optional[str] = None,
      ) -> list:
      ```
    - Engine ([`core/graph_rag.py:161-166`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L161-L166)):
      ```python
      def get_call_chain_recursive(
          self,
          start_node: str,
          depth_limit: int = 5,
          project_identifier: Optional[str] = None,
      ) -> List[str]:
      ```
  - Portanto, o parâmetro de entrada do nó raiz é `start_node`, o escopo opcional é `project_identifier`, e o limitador de profundidade é `depth_limit`.

---

## 2. Resolução de Projeto (`_resolve_project_identifier` vs. SQL Próprio em `core/graph_rag.py`)

- **Texto anterior no relatório 4.3 (verbatim):**  
  Em `audits/relatorio_4_3.md`, linha 23:
  ```text
  - **Mecanismo:** A ferramenta aceita `project_id` ou `project_name`. Se não fornecido e o identificador (`symbol_or_path`) existir em múltiplos projetos ativos, a execução **rejeita a consulta com `ValueError` descritivo**, exigindo a especificação do projeto.
  ```

- **Retificação Factual (4.3b):**
  - A redação do relatório da 4.3 induzia à interpretação de que a resolução de projeto utilizava o método utilitário `_resolve_project_identifier` (pertencente à camada `ConciergeFacade` / `interface/mcp_server.py`).
  - No Bloco 2 da Rodada 4.3, o motor `GraphRAGEngine` em `core/graph_rag.py` implementou **resolução SQL própria e direta** sobre o SQLite (consultando `projects.folder_name`, `projects.uuid` e cruzando nós em `nodes`).
  - Essa implementação direta no motor gerou comportamentos particulares (como desconsiderar duplicatas de `folder_name` ou aceitar tipos não-inteiros para `depth_limit`), os quais foram sanados e formalizados nos Itens 2a a 2e da Rodada 4.3b.

---

## 3. Ausência de Checagem de `privacy_level` em Consultas de Leitura

- **Texto anterior no relatório 4.3:**  
  Não há citação explícita do termo `privacy_level` no corpo do relatório `audits/relatorio_4_3.md` (0 ocorrências encontradas via `git grep -n "privacy_level" audits/relatorio_4_3.md`). Contudo, o conceito foi ventilado nas discussões de projeto e escopo da 4.3.

- **Retificação Factual (4.3b):**
  - A varredura no repositório (`git grep -n "privacy_level" core/graph_rag.py`, evidência `grep_privacy_level_core` em `scratch/evidencia_4_3b/item5_errata_greps.txt`) confirma que **`privacy_level` não é lido, filtrado ou considerado em nenhuma consulta do `GraphRAGEngine`**.
  - No diretório `core/`, ocorrências de `privacy_level` existem unicamente em `core/middleware.py` (linhas 109, 121, 142, 148 e 722) para metadados de registro de projetos (`INTERNAL`, `PUBLIC`, `RESTRICTED`). Nenhuma restrição de leitura por nível de privacidade é imposta durante a expansão do grafo de chamadas ou na busca do GraphRAG.

---

## 4. Omissão da Execução da Suíte Completa de Testes

- **Texto anterior no relatório 4.3:**  
  O relatório da Rodada 4.3 contém zero ocorrências do comando `pytest tests` (evidência `grep_full_suite_mention_relatorio_4_3` em `scratch/evidencia_4_3b/item5_errata_greps.txt`). A seção 4 listou apenas execuções pontuais dos blocos 0 a 3.

- **Retificação Factual (4.3b):**
  - A suíte completa de testes do projeto (`pytest tests`) **não foi executada nem reportada ao término da Rodada 4.3**.
  - A alteração da assinatura de `get_call_chain_recursive` e a remoção da tabela `ast_edges` no Bloco 2 deixaram 6 testes existentes quebrados na base de código:
    1. `tests/test_graph_rag_loops.py::test_depth_limit_enforcement`
    2. `tests/test_graph_rag_loops.py::test_indirect_cycle_resolution`
    3. `tests/test_graph_rag_loops.py::test_substring_collision_prevention`
    4. `tests/test_graph_rag_janitor.py::test_should_resolve_multi_hop_dependencies_via_sqlite_cte_recursive`
    5. `tests/test_mcp_server_extensions.py::test_mcp_tool_concierge_get_call_chain`
    6. `tests/test_e2e_concierge_integration.py::test_e2e_flow_full_lifecycle_and_communication`
  - Essa omissão violou a integridade da suíte de regressão. Na Rodada 4.3b, todos os 6 testes foram reescritos sobre as tabelas canônicas `nodes` e `edges` com `SchemaManager` oficial, e a suíte completa foi executada e aferida em venv limpo.

---

## 5. Script Gerador do Relatório 4.3

- **Texto anterior no relatório 4.3:**  
  O relatório não explicitava o mecanismo de sua própria geração.

- **Retificação Factual (4.3b):**
  - O arquivo `audits/relatorio_4_3.md` foi gerado programaticamente através do script auxiliar `scratch/build_relatorio_4_3.py` (evidência `generator_script_check` em `scratch/evidencia_4_3b/item5_errata_greps.txt`).
  - O script foi mantido no repositório como evidência de rastreabilidade da geração do relatório da rodada anterior.
