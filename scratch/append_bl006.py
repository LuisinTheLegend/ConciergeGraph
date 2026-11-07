bl_entry = """

---

### [BL-006] Checkpoints Salvos Fora da Fila Serializada SerializedWriteQueue
- **Status:** **ABERTO (registrado na Rodada 4.3 pelo executor, aguardando priorização e planejamento)**
- **Severidade Proposta:** 🟡 MÉDIA (Risco de contenção transacional e falhas do tipo `database is locked` sob concorrência de múltiplos agentes ou quando o `JanitorService` / `Store` executam escritas em segundo plano via `SerializedWriteQueue`).
- **Arquivos & Linhas:** [`core/checkpointer.py:113-114, 139-140, 206-209`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L113-L114), [`interface/mcp_server.py:164-166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L164-L166)
- **Mecanismo da Falha:**
  Em `core/checkpointer.py`, os métodos de escrita de checkpoints (`save_checkpoint`, `restore_checkpoint`, `_cleanup_old_checkpoints`) invocam `write_fn` diretamente através de reflexão:
  `write_fn = getattr(self.db, "execute_write", getattr(self.db, "write_query", None))`
  e realizam chamadas diretas como `write_fn(query, params)`.
  No MCP Server (`interface/mcp_server.py:166`), a instância de `AgnosticCheckpointer` é conectada a `db_manager` (`ConciergeDatabaseManager`). Se `db_manager` for instanciado sem fila (`write_queue=None`), as escritas abrem conexões efêmeras imediatas (`sqlite3.connect`) fora do controle do thread único de gravação. Mesmo quando há uma fila conectada, a arquitetura mantém dois subsistemas de gravação concorrentes (a fila de `core/database.py` e a fila de `storage/store.py`), violando o princípio do escritor único e criando risco real de bloqueio em cenários de alta frequência de checkpoints.
- **Justificativa da Severidade (MÉDIA):**
  Embora o SQLite WAL permita múltiplos leitores concorrentes, ele admite apenas um escritor por vez. Quando múltiplos agentes tentam salvar checkpoints simultaneamente à ingestão ou compactação do Janitor, a escrita direta contorna a política central de serialização transacional do sistema, gerando potenciais exceções e degradação de confiabilidade na retenção de memória de longo prazo dos agentes.
- **Resolução Recomendada (Para Rodada Futura):**
  Unificar o canal de persistência do `AgnosticCheckpointer` para utilizar estritamente a fila central de escrita serializada de produção (`SerializedWriteQueue`), padronizando o timeout e o tratamento transacional assíncrono.
"""

with open('audits/fase4-achados.md', 'r', encoding='utf-8') as f:
    content = f.read()

content += bl_entry

with open('audits/fase4-achados.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('Appended BL-006 successfully.')

