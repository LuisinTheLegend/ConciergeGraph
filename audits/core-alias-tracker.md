# Auditoria — `core/alias_tracker.py`

> **Item:** `core/alias_tracker.py` (Mapeamento e Migração de Alias/Renomeação de Arquivos)  
> **Fase:** 1 — Auditoria módulo a módulo  
> **Data:** 2026-10-13  
> **Status:** Concluído  

---

## 1. Ferramentas Estáticas e Reprodução Executada

| Ferramenta | Comando | Resultado |
|------------|---------|-----------|
| **Reprodução Dinâmica** | `python scratch/fase3_redo_repro_alias.py` | ❌ **Falha reproduzida**: `apply_alias_migration` executa UPDATEs sequenciais sem transação unificada; falha no 3º UPDATE deixa tabelas anteriores (`files`, `nodes`) migradas e commitadas. |

---

## 2. Inventário de Chamadores em Produção

| Arquivo Chamador | Linha | Método Invocado | Contexto de Operação |
|------------------|-------|-----------------|----------------------|
| [`interface/watcher.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L179) | 179 | `apply_alias_migration(matched_old, rel_path)` | Reconciliação de renomeação de arquivo detectada por hash estrutural idêntico no Watcher |
| [`interface/watcher.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L240) | 240 | `apply_alias_migration(src_rel, dest_rel)` | Evento direto de movimentação/renomeação (`on_moved`) no Watchdog |

---

## 3. Tabela de Achados (Formato Oficial do Protocolo)

| # | arquivo | linha | severidade | mecanismo | reprodução | status |
|---|---------|-------|-----------|-----------|------------|--------|
| 1 | `core/alias_tracker.py` | 185–259 | **MÉDIA** | `apply_alias_migration` não é atômico. A função aplica UPDATEs em `files`, `nodes`, `ast_edges` e `fsm_checkpoints` em loop sequencial, onde cada chamada a `execute_write`/`write_query` confirma a transação isoladamente. Se ocorrer uma falha intermediária (ex: timeout SQLite, erro de coluna ou interrupção de I/O), as mutações anteriores permanecem persistidas e commitadas. A função captura a exceção, registra log de erro crítico e retorna `False` sem desfazer os UPDATEs prévios, deixando o banco de dados em estado inconsistente e corrompido de migração parcial. | Script `scratch/fase3_redo_repro_alias.py` forçou falha na 3ª query (`ast_edges`): `apply_alias_migration` retornou `False`, mas `files.path` e `nodes.label` já haviam sido alterados e comitados permanentemente no banco. | **CONFIRMADO** |

---

## 4. Detalhamento do Achado

### Achado #1 — Falha de Atomicidade em `apply_alias_migration` (Migração Parcial sem Rollback)

- **Arquivos & Linhas:** [`core/alias_tracker.py:185–259`](file:///c:/Nexus-Memory/GrafoConcierge/core/alias_tracker.py#L185)
- **Chamadores em Produção:** [`interface/watcher.py:179, 240`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L179)
- **Severidade:** 🟡 **MÉDIA**
- **Mecanismo da Falha:**
  O método `apply_alias_migration` itera sobre a lista de queries de atualização (`files`, `nodes`, `ast_edges`, `fsm_checkpoints`):
  ```python
  for query, params in queries:
      if hasattr(self.db, "execute_write"):
          success, res = self.db.execute_write(query, params)
          if not success:
              raise Exception(f"Transaction failed: {res}")
      else:
          self.db.write_query(query, params)
  ```
  Como o gerenciador de banco de dados (`ConciergeDatabaseManager`) comita imediatamente cada instrução individual dentro de `execute_write` (ou `write_query`), cada UPDATE é uma transação separada. Ao encontrar uma falha na 3ª ou 4ª query, o bloco `except Exception` apenas loga e retorna `False`, sem qualquer mecanismo de compensação ou rollback para reverter as tabelas já alteradas.
- **Diretriz de Remediação:**
  Executar todos os UPDATEs dentro de uma única transação SQLite atômica com rollback automático em caso de exceção (suporte condicionado à fila unificada transacional da Track 2 / BL-006).
- **Critério de Validação:**
  Teste automatizado simulando falha na atualização de `ast_edges` ou `fsm_checkpoints`, assegurando que `files` e `nodes` revertam integralmente aos caminhos originais (`old_path`).
