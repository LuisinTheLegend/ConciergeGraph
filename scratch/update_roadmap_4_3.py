target_old = "| 4.3 | — | DDL só de `agent_checkpoints`; reimplementar `concierge_get_call_chain` sobre `edges`/`nodes` (caminhos de arquivo, só `calls`) | PLANEJADO, NÃO AUTORIZADO | — |"

replacement_new = "| 4.3 | `f17cc7d` (B0), `d63b638` (B1), `f25d319` (B2), `ad39881` (B3) | Bloco 0 (documental: F4-018, errata §§13-14, relatorio_4_2k UTF-8 puro); Bloco 1 (schema oficial DDL `agent_checkpoints`, índice, `verify_tables_exist`, `last_error`, ordenação determinística); Bloco 2 (reimplementação de call chain sobre `edges`/`nodes` canônicos, Opção A escopo estrito de projeto, proteção de ciclo, relation_type='calls', 1..10 profundidade); Bloco 3 (remoção de `test_log` de `core/database.py` e isolamento em teste) | Concluída pelo executor, aguardando verificação independente | — |"

roadmap_file = r"audits\fase4-roadmap.md"
with open(roadmap_file, "r", encoding="utf-8") as f:
    content = f.read()

assert target_old in content, "Old 4.3 line not found in roadmap"
content = content.replace(target_old, replacement_new)

# Add BL-006 to Section 4
target_table_end = "| F4-027 | Filtro de AND/OR/NOT/NEAR no builder FTS impedia buscas com termos literais legítimos | BAIXA | corrigido pelo executor, aguardando verificação independente | `storage/logic.py`, `tests/test_fts_code_search.py`, `scratch/evidencia_4_2j/` |"
bl006_line = "| BL-006 | Checkpoints salvos fora da fila serializada SerializedWriteQueue (risco de lock sob concorrência) | MÉDIA | ABERTO (registrado na 4.3) | `core/checkpointer.py:113-114, 139-140, 206-209`, `interface/mcp_server.py:164-166`, `audits/fase4-achados.md` |"

assert target_table_end in content, "F4-027 line not found in roadmap"
content = content.replace(target_table_end, target_table_end + "\n" + bl006_line)

with open(roadmap_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated fase4-roadmap.md successfully.")

