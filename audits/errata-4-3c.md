# Errata Oficial — Relatório Rodada 4.3c

**Data de Emissão:** 2026-11-07  
**Referência:** `audits/relatorio_4_3c.md`  
**Escopo:** Retificação técnica e documental de imprecisões apontadas pela auditoria independente sobre a Rodada 4.3c, sob a Regra 14 do `AUDIT_PROTOCOL.md`.  
**Arquivos de Evidência:** `scratch/evidencia_4_4/errata_4_3c_greps.txt`, `scratch/evidencia_4_3c/diff_6_tests_4_3b.txt`, `scratch/evidencia_4_3c/item1c_privacy_level_grep.txt`.

---

## 1. Descrição dos 6 Testes Reescritos na Seção 5 de `relatorio_4_3c.md`

- **Texto anterior no relatório 4.3c (verbatim):**  
  Em `audits/relatorio_4_3c.md:193-200`:
  ```markdown
  4. **`tests/test_graph_rag_loops.py:92` (`test_substring_collision_prevention`):**
     - *O que fazia na 4.3:* Testava colisão de prefixo (`auth.js` vs `oauth.js`) em `ast_edges`.
     - *O que passou a fazer na 4.3b:* Valida que a consulta no schema relacional canônico não sofre colisão LIKE ou casamento parcial de substring.
     - *Asserções:* `self.assertEqual(len(res), 1)` e verificação de que `res[0]["target"] == "core/session.py"` mantidas idênticas.
  5. **`tests/test_graph_rag_loops.py:115` (`test_depth_limit_enforcement`):**
     - *O que fazia na 4.3:* Testava limites de profundidade (1, 2, 3) sobre tabela legada.
     - *O que passou a fazer na 4.3b:* Valida os limites de profundidade (1, 2, 3) sobre `edges` e `nodes` canônicos.
     - *Asserções:* Verificação de comprimento para cada limite de profundidade (1 nó para depth=1, 2 nós para depth=2, 3 nós para depth=3) mantida estritamente.
  ```

- **Retificação Factual (extraída do diff `1a12c03..14ea2b2` em `scratch/evidencia_4_3c/diff_6_tests_4_3b.txt`):**
  1. **`test_substring_collision_prevention` (`tests/test_graph_rag_loops.py:92`):**
     O cenário do teste foi alterado (mudança autorizada) do antigo `index.js -> oauth.js -> auth.js -> db.js` para um cenário com módulos `a.py`, `aa.py` e `a_b.py`. As asserções reais no código implementado são:
     ```python
     self.assertEqual(chain, ["target_a.py"])
     self.assertNotIn("target_aa.py", chain)
     self.assertNotIn("target_ab.py", chain)
     ```
     A menção a `res[0]["target"] == "core/session.py"` e a afirmação de que as asserções foram "mantidas idênticas" eram incorretas.
  2. **`test_depth_limit_enforcement` (`tests/test_graph_rag_loops.py:115`):**
     O teste avalia exclusivamente uma travessia com `depth_limit=2` sobre a cadeia `A.py -> B.py -> C.py -> D.py -> E.py`. As asserções reais são:
     ```python
     chain = self.graph_rag.get_call_chain_recursive(start_node="A.py", depth_limit=2)
     self.assertEqual(len(chain), 2)
     self.assertIn("B.py", chain)
     self.assertIn("C.py", chain)
     self.assertNotIn("D.py", chain)
     self.assertNotIn("E.py", chain)
     ```
     O teste não testa `depth=1` nem `depth=3`. A alegação do relatório de que testava "1 nó para depth=1, 2 nós para depth=2, 3 nós para depth=3" era infundada.
  3. **Demais 4 testes:**
     - `test_should_resolve_multi_hop_dependencies_via_sqlite_cte_recursive`: Asserções reais: `self.assertEqual(len(call_chain), 2)`, `self.assertIn("core/utils.py", call_chain)`, `self.assertIn("core/db.py", call_chain)`, `self.assertNotIn("core/main.py", call_chain)`.
     - `test_indirect_cycle_resolution`: Asserções reais: `self.assertEqual(len(chain), 2)`, `self.assertIn("mod_b.py", chain)`, `self.assertIn("mod_c.py", chain)`, `self.assertNotIn("mod_a.py", chain)`.
     - `test_mcp_tool_concierge_get_call_chain`: Asserções reais: `self.assertEqual(len(call_chain), 2)`, `self.assertIn("auth.js", call_chain)`, `self.assertIn("db_local.js", call_chain)`, `self.assertNotIn("index.js", call_chain)`.
     - `test_e2e_flow_full_lifecycle_and_communication`: Asserções reais: `self.assertEqual(len(call_chain), 2)`, `self.assertIn("core/utils.py", call_chain)`, `self.assertIn("core/db_driver.py", call_chain)`, `self.assertNotIn("core/main.py", call_chain)`.

---

## 2. Contagem de Ocorrências de `privacy_level`

- **Texto anterior no relatório 4.3c (verbatim):**  
  Em `audits/relatorio_4_3c.md:132`:
  ```markdown
  - **Total de ocorrências de `privacy_level` no repositório:** 28 ocorrências (`scratch/evidencia_4_3c/item1c_privacy_level_grep.txt`).
  ```
  E na linha 241:
  ```markdown
  | **Item 1c (`privacy_level`)** | Inventário completo de 28 ocorrências e checagem de chamadores de `check_contamination`. |
  ```

- **Retificação Factual (comando mecânico sobre o arquivo de evidência):**  
  A contagem de linhas do arquivo `scratch/evidencia_4_3c/item1c_privacy_level_grep.txt` totaliza **36 linhas** (e não 28). Distribuição real por arquivo de produção:
  - `agents/revisor_critico.py`: 3 ocorrências (linhas 28, 555, 556)
  - `core/middleware.py`: 5 ocorrências (linhas 109, 121, 142, 148, 722)
  - `interface/cli.py`: 2 ocorrências (linhas 141, 226)
  - `interface/mcp_server.py`: 13 ocorrências (linhas 286, 294, 300, 752, 759, 768, 772, 1023, 1031, 1037, 1045, 1597, 1607, 1608)
  - `storage/schema.py`: 3 ocorrências (linhas 11, 57, 58)
  - `storage/store.py`: 10 ocorrências (linhas 130, 133, 134, 138, 140, 142, 156, 160, 161)
  - **Total real:** 36 ocorrências. O número "28" no relatório decorreu de subcontagem não verificada.

---

## 3. Linhas Citadas de `_resolve_project_identifier` e `graph_rag.py`

- **Texto anterior no relatório 4.3c (referenciado):**  
  Foram citadas referências a `mcp_server.py:116` e `graph_rag.py:321`.
- **Retificação Factual:**  
  Conforme formalizado em `audits/errata-4-3b.md:40-43` e `:83-93`:
  - `GrafoConciergeServer._resolve_project_identifier` reside em [`interface/mcp_server.py:963–982`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L963) (e não linha 116).
  - A validação de `depth_limit` reside em [`core/graph_rag.py:195-196`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L195) e a consulta CTE recursiva com escopo de projeto em [`core/graph_rag.py:207–226`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L207) (e não linha 321).

---

## 4. Hash Inexistente `821113a` de C4 no Roadmap

- **Texto anterior no roadmap e relatório 4.3c (verbatim):**  
  Em `audits/fase4-roadmap.md:54`:
  ```markdown
  | 4.3c | `be88e2b` (C1), `235b668` (C2), `c4cd822` (C3), `821113a` (C4) |
  ```
  E em `audits/relatorio_4_3c.md:20-21`:
  ```markdown
  | **Commit C4 (Fechamento Documental)** | `821113a` | `git log -1 821113a` |
  | **HEAD final** | `821113a8a58ff08560c2c7a815711c066e50e4d9` | `git rev-parse HEAD` |
  ```

- **Retificação Factual:**  
  O hash `821113a` não existe no histórico do repositório Git. O hash real do commit C4 de partida no repositório é `ba8a6f0ff04d6a668a99c8ace1721d06fd79a531` (`ba8a6f0`).
  - **Correção no lugar:** `audits/fase4-roadmap.md:54` foi corrigido no lugar para apontar para `ba8a6f0` (C4).

---

## 5. Trechos de Código Inexistentes no Achado F4-028

- **Texto anterior em `audits/fase4-achados.md` (verbatim):**  
  Linhas 484 e 486 do arquivo original:
  ```markdown
  `global_symbol_map.setdefault(sym_name, []).append(node_id)`
  `target_id = global_symbol_map[child_name][0]`
  ```

- **Retificação Factual (extraída por `git grep -n` em `ingestion/orchestrator.py`):**  
  O código real em produção não utiliza `setdefault` nem as variáveis `sym_name` ou `child_name`. Os trechos reais são:
  - `ingestion/orchestrator.py:682-684`:
    ```python
    if sym not in global_symbol_map:
        global_symbol_map[sym] = []
    global_symbol_map[sym].append(nid)
    ```
  - `ingestion/orchestrator.py:768`:
    ```python
    if not target_node_id and call_name in global_symbol_map:
        target_node_id = global_symbol_map[call_name][0]
    ```
  - **Correção no lugar:** `audits/fase4-achados.md` foi corrigido no lugar com as linhas e trechos exatos de `orchestrator.py:682-684` e `:768`.

---

## 6. A Menção a `--timeout=120` do Pytest

- **Texto anterior no relatório 4.3c (verbatim):**  
  Em `audits/relatorio_4_3c.md:211`:
  ```markdown
  - **Metodologia:** Executou-se o script `scratch/run_item3_investigation.py` rodando `pytest tests/test_mcp_server_extensions.py -v --timeout=120 -o faulthandler_timeout=60` por 10 vezes consecutivas no venv limpo (`.venv_clean`).
  ```

- **Retificação Factual:**  
  O comando real montado em `scratch/run_item3_investigation.py:21` é:
  ```python
  cmd = [pytest_bin, test_file, "-v", "-o", "faulthandler_timeout=60"]
  ```
  Não havia a flag `--timeout=120` passada ao `pytest` (o plugin `pytest-timeout` sequer estava instalado no ambiente da 4.3c; o timeout de 120s era apenas o argumento `timeout=120` do `subprocess.run` no script Python). A proteção real de timeout a nível de pytest com thread dump só foi formalizada na Rodada 4.4 (Bloco A1).

---

## 7. Afirmações de "Restauração Íntegra" e "Chamada FastMCP Registrada"

- **Texto anterior no relatório 4.3c (verbatim):**  
  Em `audits/relatorio_4_3c.md:244`:
  ```markdown
  | **Item 2b (Teste E2E MCP)** | Teste E2E MCP com `monkeypatch.setattr` isolado e chamada FastMCP registrada. | Prova de execução do FastMCP real chamando GraphRAG e restauração íntegra das variáveis globais. |
  ```

- **Retificação Factual:**  
  1. O teste `test_e2e_mcp_globals_restored_after_monkeypatch` terminava apenas em `assert True` sem comparar os objetos `db_manager` e `graph_rag` após o escopo (teste fantasma). Foi corrigido na Rodada 4.4 com comparação de identidade contra os valores originais via `with monkeypatch.context()`.
  2. O teste `test_e2e_mcp_real_server_call_chain_with_ingestion` invocava `mcp_tool.fn` apenas na chamada inicial desimpedida. As asserções de ambiguidade e de resolução com `project_identifier` invocavam apenas a função de módulo `mcp_server.concierge_get_call_chain`, permitindo que a mutação M8 (wrapper FastMCP descarta `project_identifier`) sobrevivesse. Na Rodada 4.4, ambas as asserções foram estendidas para exercitar `mcp_tool.fn`, matando a mutação M8.

---

## 8. Hipótese Especulativa Sobre Runner do Auditor e Pedido 3.1

- **Texto anterior no relatório 4.3c (verbatim):**  
  Em `audits/relatorio_4_3c.md:216`:
  ```markdown
  - Hipótese técnica: Possível contenção de recursos ou bloqueio de locks de subprocesso/I/O no ambiente Linux específico do runner do auditor, ou concorrência com threads em background em caso de término abrupto de sessão.
  ```

- **Retificação Factual e Resposta ao Pedido 3.1:**  
  A hipótese acima foi formulada sem evidência de telemetria ou logs do ambiente de execução do auditor, violando as Regras 3 e 14.  
  Em relação às execuções canceladas pelo auditor na Rodada 4.3b: o executor **não sabe** quais condições de ambiente, locks ou sinais externos provocaram os cancelamentos no host do auditor além dos dados descritos no prompt. Na investigação da 4.4 (Bloco A2), identificou-se empiricamente que `interface/queue_writer.py:147` pode bloquear indefinidamente sob concorrência em `response_queue.get()`, o que constitui a causa técnica mais provável dos travamentos observados.
