# Errata Oficial — Rodada 4.3b (Regra 14 do AUDIT_PROTOCOL.md)

**Data de Emissão:** 2026-11-06  
**Referência Principal:** `audits/errata-4-3.md` e `audits/relatorio_4_3b.md`  
**Escopo:** Retificação técnica e documental estrita dos apontamentos da auditoria independente sobre a errata e o relatório da Rodada 4.3b.  
**Regras do Protocolo:** Regras 2, 4, 10, 11, 12, 13 e 14 do `AUDIT_PROTOCOL.md`.  
**Diretório de Evidências:** `scratch/evidencia_4_3c/`.

---

## 1. Retificações sobre a Errata 4.3 (`audits/errata-4-3.md`)

### 1a. Rastreabilidade dos Scripts Geradores (§5 da Errata 4.3)
- **Texto anterior verbatim em `audits/errata-4-3.md:94-95`:**
  ```text
  - O arquivo `audits/relatorio_4_3.md` foi gerado programaticamente através do script auxiliar `scratch/build_relatorio_4_3.py` (evidência `generator_script_check` em `scratch/evidencia_4_3b/item5_errata_greps.txt`).
  - O script foi mantido no repositório como evidência de rastreabilidade da geração do relatório da rodada anterior.
  ```
- **Retificação Factual (4.3c):**
  - A afirmação de que o script "foi mantido no repositório" continha imprecisão técnica: a evidência citada na própria errata (`scratch/evidencia_4_3b/item5_errata_greps.txt:53`) exibia o status `?? scratch/build_relatorio_4_3.py`, ou seja, o script estava presente no disco local do executor, mas **não estava rastreado pelo Git**.
  - A execução de `git ls-files` comprovou que nenhum dos quatro scripts citados pela auditoria estava rastreado no commit `14ea2b2` (evidência em [`scratch/evidencia_4_3c/item1a_git_ls_files.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3c/item1a_git_ls_files.txt)).
  - **Inventário em disco verificado:** Todos os 4 scripts existiam no disco local (comprovado em [`scratch/evidencia_4_3c/item1a_disk_status.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3c/item1a_disk_status.txt)):
    - `scratch/build_relatorio_4_3.py` (9.599 bytes)
    - `scratch/build_relatorio_4_3b.py` (14.526 bytes)
    - `scratch/reproduce_item2_defects.py` (7.247 bytes)
    - `scratch/run_full_suite.py` (597 bytes)
  - Todos foram revisados via `scan_secrets.py` (0 violações) e foram formalmente commitados no repositório no commit `235b668` (C2).
  - **Comprovação da geração de `relatorio_4_3.md`:** A comparação automatizada entre o template textual de `scratch/build_relatorio_4_3.py` e o arquivo `audits/relatorio_4_3.md` resultou em **0 linhas de diff (EXACT MATCH verbatim)**, provando empiricamente que `audits/relatorio_4_3.md` foi de fato gerado por esse script e não se trata de suposição (evidência em [`scratch/evidencia_4_3c/item1a_diff_build_relatorio_4_3.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3c/item1a_diff_build_relatorio_4_3.txt)).

---

### 1b. Origem da Afirmação sobre `_resolve_project_identifier` e `ConciergeFacade` (§2 da Errata 4.3)
- **Texto anterior verbatim em `audits/errata-4-3.md:52-53`:**
  ```text
  - A redação do relatório da 4.3 induzia à interpretação de que a resolução de projeto utilizava o método utilitário `_resolve_project_identifier` (pertencente à camada `ConciergeFacade` / `interface/mcp_server.py`).
  ```
- **Retificação Factual (4.3c):**
  - A linha 23 de `audits/relatorio_4_3.md` citada na errata não contém os termos `_resolve_project_identifier` nem `ConciergeFacade`. A busca no arquivo (`git grep -n -E "_resolve_project_identifier|ConciergeFacade" audits/relatorio_4_3.md`) retornou zero resultados (evidência em [`scratch/evidencia_4_3c/item1b_resolve_project_identifier_greps.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3c/item1b_resolve_project_identifier_greps.txt)).
  - **Origem da afirmação:** Essa formulação não existe em nenhum arquivo versionado da Rodada 4.3. Ela existiu **apenas em texto de chat das orientações da rodada; tratada documentalmente como hipótese não comprovada em arquivo versionado**.
  - **Inexistência de `ConciergeFacade`:** A classe `ConciergeFacade` **não existe na base de código** (ocorre no repositório unicamente na própria errata `audits/errata-4-3.md:53`). A classe real que encapsula o método de resolução é [`GrafoConciergeServer._resolve_project_identifier`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L963) em `interface/mcp_server.py:963`.
  - **Tabela Comparativa de Comportamento Concreto de Resolução de Projeto:**

| Cenário de Entrada | `GrafoConciergeServer._resolve_project_identifier`<br>([`interface/mcp_server.py:963–982`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L963)) | `SqliteStore.get_project`<br>([`storage/store.py:144–152`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L144)) | `GraphRAGEngine.get_call_chain_recursive`<br>([`core/graph_rag.py:207–226`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L207)) |
|---|---|---|---|
| **Identificador sintaticamente válido como UUID** | Tenta `uuid.UUID(id)`. Se sintaxe válida, **retorna imediatamente a string sem consultar o banco** (aceita UUID fantasma inexistente no SQLite). | Executa `SELECT * FROM projects WHERE uuid = ? OR folder_name = ?`. Retorna `dict(row)` se existir; levanta `ProjectNotFoundError` se inexistente. | Consulta `SELECT uuid FROM projects WHERE uuid = ?;`. Se encontrado, usa o UUID real verificado no SQLite; se inexistente, tenta `folder_name`. |
| **Identificador igual a `folder_name` (único)** | Falha no `uuid.UUID()`, cai no `except ValueError`, chama `store.get_project(id)` e retorna `project["uuid"]`. | Encontra o registro via cláusula `OR folder_name = ?` e retorna `dict(row)`. | `uuid_rows` é vazio; consulta `SELECT uuid FROM projects WHERE folder_name = ?;`. Como há exatamente 1 registro, adota o UUID retornado. |
| **`folder_name` duplicado (múltiplos projetos)** | Delega para `store.get_project(id)`. Como `get_project` usa `cursor.fetchone()`, **retorna silenciosamente o primeiro projeto retornado pelo SQLite**, sem detectar ambiguidade. | Executa `fetchone()` sem `ORDER BY`. Retorna silenciosamente a primeira linha recuperada pela query sem alertar sobre duplicidade. | Consulta `folder_rows`. Detecta `len(folder_rows) > 1` e **levanta `ValueError`**: `Multiple projects ({len(folder_rows)}) share folder_name '{project_identifier}'. Please specify the project by its unique UUID.` |
| **Identificador inexistente no banco** | Se formato UUID: retorna o UUID sem checar no banco.<br>Se texto comum: `store.get_project` levanta `ProjectNotFoundError`, capturado e relançado como `ValueError: Project '{id}' not found. Please list available projects using concierge_list_projects.` | Levanta `ProjectNotFoundError(f"Project not found: {project_id}")`. | `uuid_rows` e `folder_rows` ambos vazios. Levanta `ValueError: Project '{project_identifier}' not found.` |

---

### 1c. Análise Rigorosa de `privacy_level` (§3 da Errata 4.3)
- **Texto anterior em `audits/errata-4-3.md:68-69`:**
  Reconhecia que `privacy_level` possuía zero ocorrências em `audits/relatorio_4_3.md`, tendo a seção sido criada com base em discussões conceituais. O grep de verificação foi restrito a `core/`.
- **Retificação Factual (4.3c):**
  - **Origem da discussão:** A menção a `privacy_level` existiu **apenas no diálogo do chat**, não tendo constado no relatório 4.3.
  - **Varredura exaustiva no repositório inteiro:** O comando `git grep -n "privacy_level" -- '*.py' ':!tests' ':!scratch'` identificou 28 linhas com o termo em código de produção (evidência em [`scratch/evidencia_4_3c/item1c_privacy_level_grep.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3c/item1c_privacy_level_grep.txt)).
  - **Classificação técnica das ocorrências:**
    1. *Cadastro e Validação (24 ocorrências):* DDL de bootstrap com restrição CHECK (`storage/schema.py:11, 57-58`); validação de tipos válidos `VALID_PRIVACY_LEVELS` em `create_project` e `update_project` (`storage/store.py:130, 133, 134, 138, 140, 142, 156, 160, 161`); parâmetros de entrada em `register_project` (`core/middleware.py:109, 121, 142, 148, 722`); ferramentas MCP `concierge_register` e `update_project` (`interface/mcp_server.py:286, 294, 300, 752, 759, 768, 772, 1023, 1031, 1037, 1045, 1597, 1607, 1608`); e flag CLI `--privacy` (`interface/cli.py:141`).
    2. *Exibição (1 ocorrência):* Exibição formatada em coluna na listagem de projetos da CLI (`interface/cli.py:226`).
    3. *Decisão (3 ocorrências):* Método `check_contamination` em [`agents/revisor_critico.py:28, 555-556`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L555).
  - **Verificação de chamadores reais de `check_contamination`:**
    A busca por referências em código de produção (`git grep -n "check_contamination" -- ':!tests' ':!scratch' ':!audits'`, evidência em [`scratch/evidencia_4_3c/item1c_check_contamination_callers.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3c/item1c_check_contamination_callers.txt)) retornou **nenhum chamador encontrado** em todo o código executável (a única ocorrência é a própria definição em `agents/revisor_critico.py:538`).
  - **Conclusão precisa:** O campo `privacy_level` hoje é persistido no banco e exibido na CLI, mas **não atua como filtro de consulta, listagem de nós, busca vetorial/híbrida nem no `concierge_get_call_chain`**. A barreira de contaminação em `RevisorCritico` está dormente e não é invocada por nenhum fluxo de execução do sistema.

---

## 2. Retificações sobre o Relatório 4.3b (`audits/relatorio_4_3b.md`)

### 2a. Ocorrência de Byte Order Mark (BOM) em Arquivo de Evidência
- **Texto anterior verbatim em `audits/relatorio_4_3b.md:213`:**
  ```text
  3. **Integridade de Codificação:** Todos os arquivos de evidência em `scratch/evidencia_4_3b/` e os documentos Markdown em `audits/` foram gravados em **UTF-8 puro, sem BOM e com zero bytes nulos**.
  ```
- **Retificação Factual (4.3c):**
  - A varredura de integridade em todos os 69 arquivos de `scratch/evidencia_4_3b/` e `audits/*.md` (evidência em [`scratch/evidencia_4_3c/item1d_bom_scan.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3c/item1d_bom_scan.txt)) revelou que **1 arquivo continha BOM UTF-8**:
    - `scratch/evidencia_4_3b/item4_green_checkpoints.txt`: tamanho 2.210 bytes, iniciava com `\xef\xbb\xbf` (gerado por redirecionamento PowerShell padrão).
  - Os demais 68 arquivos foram validados como `CLEAN_UTF8` (0 BOM, 0 nulos, 0 UTF-16).
  - Para preservar a integridade do histórico git sem sobrescrever silenciosamente evidências commitadas, foi criado o arquivo [`scratch/evidencia_4_3b/item4_green_checkpoints_utf8.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/item4_green_checkpoints_utf8.txt) (2.207 bytes) em UTF-8 puro, commitado em `235b668` (C2).

---

### 2b. Validação Efetiva de `depth_limit` em `core/graph_rag.py`
- **Texto anterior verbatim em `audits/relatorio_4_3b.md:32`:**
  ```text
  5. **Rejeição Estrita de Tipos Booleanos em `depth_limit` (Item 2e):**
     - *Problema:* Em Python, `bool` é subclasse de `int` (`isinstance(True, int) == True`, com valor 1). Chamadas com `depth_limit=True` eram silenciosamente executadas com profundidade 1.
     - *Decisão:* Validação explícita `if isinstance(depth_limit, bool) or not isinstance(depth_limit, int) or depth_limit <= 0:` levantando `ValueError`.
  ```
- **Retificação Factual (4.3c):**
  - A condição citada no relatório (`depth_limit <= 0`) não corresponde ao código real de produção.
  - O código implementado em [`core/graph_rag.py:195-196`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L195) (evidência em [`scratch/evidencia_4_3c/item1b_resolve_project_identifier_greps.txt:29-30`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3c/item1b_resolve_project_identifier_greps.txt)) é:
    ```python
    if isinstance(depth_limit, bool) or not isinstance(depth_limit, int) or depth_limit < 1 or depth_limit > 10:
        raise ValueError(f"Invalid depth_limit: {depth_limit}. Must be an integer between 1 and 10.")
    ```
  - Portanto, a faixa permitida é `1 <= depth_limit <= 10`, e valores menores que 1 ou maiores que 10 são estritamente rejeitados.

---

### 2c. Alcance Real do Teste de Símbolo Global Repetido (Item 2f)
- **Texto anterior verbatim em `audits/relatorio_4_3b.md:104-106`:**
  ```text
  - **Comportamento 2f (Símbolo Global Repetido):** Documentado e testado. O orquestrador de ingestão utiliza `global_symbol_map[name][0]` quando há colisão global não qualificada; o `GraphRAGEngine` reflete esse mapeamento de forma determinística sem alterações na lógica central do orquestrador.
  ```
- **Retificação Factual (4.3c):**
  - Na Rodada 4.3b, o teste `test_repeated_symbol_name_orchestrator_behavior` criava as arestas manualmente via `store.create_edge` e não passava pelo orquestrador. Uma mutação trocando `[0]` por `[-1]` no orquestrador não era detectada por aquele teste.
  - Na Rodada 4.3c, o teste foi substituído por um teste que minera arquivos reais via `IngestionManager.mine` (`GRAFO_LLM_MODEL=none`). A investigação comprovou que a ordem dos arquivos depende de `os.walk`, que não ordena os nomes; logo, a escolha de `[0]` reflete o arquivo visitado primeiro pelo sistema de arquivos. O teste foi tornado robusto aferindo o nó de menor ID (inserido primeiro) e matou a mutação M6 (troca de `[0]` por `[-1]`), conforme detalhado na Seção 2a do relatório da 4.3c.

---

### 2d. Alcance Real do Teste de Threads do Checkpointer (Item 4)
- **Texto anterior verbatim em `audits/relatorio_4_3b.md:36`:**
  ```text
  6. **Eliminação de Estado Compartilhado Concorrente no Checkpointer (Item 4):**
     - *Problema:* `AgnosticCheckpointer` mantinha um atributo de instância mutável `self.last_error`. Se duas threads executassem `save_checkpoint` simultaneamente, a mensagem de erro da Thread A sobrescrevia a da Thread B antes que ela pudesse ser serializada na resposta MCP.
     - *Decisão:* Criação do método `save_checkpoint_detailed(...) -> Tuple[bool, Optional[str]]`, retornando o erro localmente por chamada sem estado global. O método `save_checkpoint` original foi preservado como wrapper retrocompatível.
  ```
- **Retificação Factual (4.3c):**
  - O teste com 2 threads da 4.3b provava apenas que os retornos das duas chamadas simultâneas não se misturavam na saída (`results["t1"]` e `results["t2"]`), mas não detectava se `self.last_error` continuava sendo mutado ou lido pelo MCP sob concorrência.
  - Na Rodada 4.3c, foram adicionados dois testes determinísticos específicos:
    1. `test_save_checkpoint_detailed_does_not_mutate_instance_state` (comprova que `vars(checkpointer)` não é mutado);
    2. `test_agent_save_checkpoint_does_not_read_last_error_poison` (injeta veneno em `checkpointer.last_error` e comprova que a ferramenta MCP não o consome).
  - Ambos mataram as mutações M7a e M7b. O teste de duas threads teve seu docstring ajustado para declarar com precisão apenas o que ele de fato comprova.
