# Registro de Observações Fora de Escopo

> **Base Normativa:** Regra 4 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md).  
> **Objetivo:** Registrar ocorrências notadas durante as execuções e validações que estão fora do escopo estrito da auditoria de produção, preservando o backlog sem investigar nem alterar código de testes ou de terceiros prematuramente.  
> **Classificação:** Todas as entradas abaixo são rotuladas formalmente como **Observações**, e **NÃO** como achados de auditoria do produto.

---

## 1. Observações em Código e Infraestrutura de Teste

### Observação 1: Falta de `import importlib.util` em `tests/test_vector_reconciler.py`
- **Arquivo & Linhas:** [`tests/test_vector_reconciler.py:17, 27, 31, 37, 41`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_vector_reconciler.py#L17)
- **O que foi observado:** O arquivo executa `import importlib` na linha 17, mas referencia o submódulo `importlib.util` diretamente nas linhas 27, 31, 37 e 41 (`importlib.util.spec_from_file_location`, `importlib.util.module_from_spec`). Em Python, `import importlib` não vincula automaticamente o submódulo `util` ao namespace `importlib`. Trata-se de um bug latente no arquivo de teste, mascarado sempre que outro módulo importado previamente no mesmo processo já carregou `importlib.util`.
- **Por que NÃO foi tratado nesta auditoria:** A auditoria em curso tem escopo restrito às vulnerabilidades, defeitos arquiteturais e contratos de código de produção e catálogo do backlog (Regras 4 e 8). Edições em suítes de teste de terceiros ou arquivos de teste pré-existentes estão fora do escopo estrito da Fase 3 e foram contornadas no ambiente de auditoria através de pré-carregamento explícito de `importlib.util` no script de reprodução [`scratch/reproduce_all_targets.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_all_targets.py).

### Observação 2: Acoplamento de Imports no Topo de `tests/test_interface_contracts.py` Bloqueia Importação Isolada
- **Arquivo & Linhas:** [`tests/test_interface_contracts.py:15, 19`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L15)
- **O que foi observado:** O arquivo importa `pytest` (linha 15) e `interface.mcp_server.GrafoConciergeServer` (linha 19) no nível de módulo (top-level). Por sua vez, `interface/mcp_server.py` requer a biblioteca externa `mcp` (`FastMCP`). Isso impede que utilitários de inspeção ou revisores externos importem diretamente classes utilitárias isoladas definidas no mesmo arquivo — como `_MockVectorStore` (linhas 40–65) — sem que todo o ambiente de produção e dependências externas do projeto estejam previamente instalados e funcionais.
- **Por que NÃO foi tratado nesta auditoria:** Trata-se de uma característica de design e empacotamento da suíte de testes legada. Modificar a estrutura de imports do arquivo de teste violaria o escopo estrito das Regras 4 e 8 (não editar código de teste ou produção pré-existente). A questão foi remediada no script de auditoria [`scratch/reproduce_all_targets.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_all_targets.py) através de stubs via `unittest.mock` e fallback autônomo via AST parsing.

### Observação 4: Divergência de Nomenclatura de Parâmetro em `MockIngestionManager.mine` (`path` vs `source_path`)
- **Arquivo & Linhas:** [`tests/test_mcp_server_handlers.py:79, 83`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L79), [`ingestion/orchestrator.py:127–130`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L127), [`interface/mcp_server.py:1076`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L1076)
- **O que foi observado:** O mock `MockIngestionManager.mine(self, project_uuid, path, auto_tag=True)` em `tests/test_mcp_server_handlers.py` define o segundo argumento como `path`, enquanto a classe real `IngestionManager.mine(self, project_uuid, source_path, auto_tag=True)` em `ingestion/orchestrator.py` utiliza `source_path`. A inspeção via AST (análise sintática estática) confirmou as assinaturas:
  - AST `MockIngestionManager.mine`: `['self', 'project_uuid', 'path', 'auto_tag']`
  - AST `IngestionManager.mine`: `['self', 'project_uuid', 'source_path', 'auto_tag']`
  O chamador em produção em `interface/mcp_server.py:1076` executa `result = self._gc.mine(project_uuid, path, auto_tag=auto_tag)`, passando os parâmetros `project_uuid` e `path` **posicionalmente**. Como a invocação ocorre por posição e não por palavra-chave (`source_path=...`), a chamada não falha em tempo de execução. O item constava na Tabela 2 do relatório [`audits/mock-vs-real-audit.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/mock-vs-real-audit.md) (item #11, linha 35), mas não foi transposto para a Tabela 3 de achados de produto justamente por não configurar quebra funcional.
- **Por que NÃO foi tratado nesta auditoria:** A auditoria restringe-se a defeitos de software e quebras contratuais ativas de produto (Regras 4 e 8). Como a divergência reside em uma fixture de teste e é absorvida pelo despacho posicional sem gerar crash ou regressão de runtime, o alinhamento da assinatura do mock permanece como item de refatoração de suíte de testes fora do escopo do backlog executivo.

---

## 2. Divergências Documentais

### Observação 3: Divergência de Modos no Gating Interceptor (`VALID_MODES` vs Documentação Arquitetural)
- **Arquivo & Linhas:** [`core/gating_interceptor.py:46`](file:///c:/Nexus-Memory/GrafoConcierge/core/gating_interceptor.py#L46), [`docs-grafo-concierge/01_ARCHITECTURE.md:456-457`](file:///c:/Nexus-Memory/GrafoConcierge/docs-grafo-concierge/01_ARCHITECTURE.md#L456), [`docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md:368`](file:///c:/Nexus-Memory/GrafoConcierge/docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md#L368)
- **O que foi observado:** O interceptador de runtime `core/gating_interceptor.py:46` define e aceita estritamente o conjunto:
  `VALID_MODES = {"plan-only", "ask", "auto-approve"}`
  No entanto, os documentos formais de arquitetura e referência de API ainda documentam modos legados/não implementados (`auto_read` e `autonomous`):
  - `docs-grafo-concierge/01_ARCHITECTURE.md:456`: `* auto_read: Non-mutating tools (READ_ONLY) execute autonomously; mutating tools require explicit confirmation.`
  - `docs-grafo-concierge/01_ARCHITECTURE.md:457`: `* autonomous: Full autonomy within the allowed bounds of the current HSM state.`
  - `docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md:368`: `| **/api/gating/config** | GET / POST | {"mode": "ask" | "auto_read" | "autonomous"} | Inspects or toggles the runtime adaptive gating autonomy mode. |`
  
  **Saída bruta do grep:**
  ```text
  core/gating_interceptor.py:46:    VALID_MODES = {"plan-only", "ask", "auto-approve"}
  docs-grafo-concierge/01_ARCHITECTURE.md:456:  * `auto_read`: Non-mutating tools (`READ_ONLY`) execute autonomously; mutating tools require explicit confirmation.
  docs-grafo-concierge/01_ARCHITECTURE.md:457:  * `autonomous`: Full autonomy within the allowed bounds of the current HSM state.
  docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md:368:| **`/api/gating/config`** | `GET` / `POST` | `{"mode": "ask" \| "auto_read" \| "autonomous"}` | Inspects or toggles the runtime adaptive gating autonomy mode. |
  ```
- **Por que NÃO foi tratado nesta auditoria:** A auditoria da Fase 3 consolida achados de código de produção e suas respectivas remediações técnicas. A divergência documental é um desalinhamento de especificação estática que não afeta a segurança do código em si (o interceptor rejeita com segurança qualquer modo fora de `VALID_MODES`), demandando decisão deliberada de documentação pela engenharia antes de qualquer edição textual nos documentos oficiais.
