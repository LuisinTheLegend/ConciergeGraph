# Investigação Empírica das Alternativas para F4-008 e F4-009 (Fase 4, Rodada 4.1/C)

**Data:** 2026-10-18  
**Autor:** Antigravity (Pair Programming com Usuário)  
**Status:** Concluído — Em espera de decisão humana (GATE Regra 7)  
**Escopo de Código:** Nenhuma alteração em código de produção. Apenas investigações, benchmarks e protótipos em `scratch/`.

---

## 1. Evidências Empíricas

### 1.1 Como o Estado Fica Preso (Passo 4.1)

#### (a) Construção dos IDs dos Vetores no Chroma
Em `ingestion/orchestrator.py` (linhas 755–765), os identificadores de documentos adicionados ao Chroma são derivados diretamente do `id` inteiro gerado pela tabela `nodes` do SQLite:
```python
doc_id = f"node_{node_id}"
items.append({
    "doc_id": doc_id,
    "embedding": embedding,
    "metadata": {
        "node_id": node_id,
        "project_uuid": project_uuid,
        "source_file": chunk.source_file,
        "chunk_type": chunk.chunk_type.value,
        "symbol_name": chunk.symbol_name,
    },
})
```
No fixture de teste, para o nó de classe `models.py::User` cujo SQLite `id` é `2`, o ID no Chroma é literalmente `"node_2"`. Não é gerado nenhum hash de conteúdo nem UUID aleatório no vetor: há um acoplamento 1:1 estrito entre `nodes.id` e `Chroma doc_id`.

#### (b) Decisão de Pulo do Crawler e Intertravamento com SQLite
No crawler (`ingestion/crawler.py`, linhas 555–565):
```python
cached_node = self._store.find_node_by_hash(project_uuid, current_file_hash)
if cached_node:
    unchanged_files.append(ScannedFile(relative_path=rel_path, file_hash=current_file_hash, size_bytes=size))
    continue
```
O crawler consulta exclusivamente o banco SQLite. Se existir qualquer nó ativo para aquele projeto com o mesmo `file_hash`, o arquivo é categorizado como `unchanged`.
- Em `orchestrator.py:162`, se todos os arquivos forem considerados `unchanged`, o pipeline encerra imediatamente com `No change detected — ending pipeline. (noop)`.
- Em `orchestrator.py:213`, `cleanup_obsolete_nodes(project_uuid, f.relative_path, f.file_hash)` remove do SQLite nós cujo `file_hash != current_file_hash`.
- Em `orchestrator.py:207`, `_apply_cache_updates` atualiza o `file_hash` de nós cacheados.
Como o SQLite já gravou o `file_hash` no Step 4 (Store SQLite), qualquer falha subsequente no Step 5 (Embed) ou Step 6 (Store Vector) deixa os nós e seus hashes gravados no SQLite, enquanto o Chroma permanece vazio.

#### (c) Variante F4-009 via Ferramenta Oficial (`reset_collection`)
Executamos o experimento controlado em `scratch/fase4_1c_reset_collection_probe.py`:
1. `concierge_mine` indexou o fixture: 2 arquivos processados, 5 nós criados, 5 vetores no Chroma.
2. Transição para estado `MAINTENANCE` via `_governor.set_session_state`.
3. Execução da ferramenta MCP oficial `concierge_reset_collection`. A coleção do Chroma foi limpa (`count = 0`).
4. Execução de uma nova mineração `concierge_mine`.
**Resultado:**
- A segunda mineração retornou: `files_processed: 0, files_skipped: 2, embeddings_stored: 0`.
- Vetores no Chroma após a 2ª mineração: **0**.
- **Conclusão:** Uma ferramenta administrativa oficial do sistema (`reset_collection`) cria o estado permanentemente quebrado de índice zerado sem que o usuário consiga reverter via `concierge_mine`.

---

### 1.2 Gatilho Realista com o Modelo Real e Falha Parcial (Passo 4.2)

#### (a) Simulação Offline com Modelo Real (`sentence-transformers/all-MiniLM-L6-v2`)
Executamos `scratch/fase4_1c_offline_hf_probe.py` com o servidor real instanciado via `main.bootstrap()`, configurando `HF_HUB_OFFLINE=1` e `HF_HOME` apontando para um diretório temporário vazio (sem cache prévio do modelo).

**1ª Mineração (Offline):**
```json
{
  "success": true,
  "files_processed": 2,
  "nodes_created": 5,
  "embeddings_stored": 0,
  "files_skipped": 0,
  "errors": []
}
```
*Vetores no Chroma após 1ª mineração:* **0**.  
*Observação crítica:* O retorno indicou `success: True` e `errors: []`! A falha no carregamento do modelo foi absorvida pelo mecanismo de fallback silencioso (`[None] * len(texts)`), sem sinalizar erro no resultado da mineração.

**2ª Mineração (Conectividade e Modelo Restaurados):**
```json
{
  "success": true,
  "files_processed": 0,
  "nodes_created": 0,
  "embeddings_stored": 0,
  "files_skipped": 2,
  "errors": []
}
```
*Vetores no Chroma após 2ª mineração:* **0**.  
**Fato Comprovado:** A falha de download do modelo na primeira inicialização deixa o Chroma vazio para sempre, e minerações subsequentes pulam 100% dos arquivos silenciosamente.

#### (b) Falha Parcial de Lotes
Executamos `scratch/fase4_1c_partial_batch_probe.py` simulando o caso onde o primeiro lote de nós é gravado com sucesso no Chroma, mas o segundo lote falha (retornando `None` via fallback semântico):
- **1ª Mineração:** `files_processed: 2, nodes_created: 6, embeddings_stored: 2, errors: [], Chroma count: 2`.
- **2ª Mineração (com embedder funcionando 100%):** `files_processed: 0, files_skipped: 2, embeddings_stored: 0, Chroma count: 2`.
- **Fato Comprovado:** Uma falha parcial congela a coleção vetorial no estado incompleto. Os vetores faltantes nunca são criados nas minerações seguintes.

---

### 1.3 Observação Aberta: Sumários e Tags Ausentes na Busca (Passo 4.4)

Na prova ponta a ponta da Rodada 4.1/B, a resposta da mineração reportou `summaries_generated: 7`, mas a busca subsequente retornou `summary: null` e `tags: null`.
Investigamos a cadeia completa de execução em `scratch/fase4_1c_summary_probe_clean.py` e inspecionamos o código fonte:

1. **Geração vs. Persistência em `ingestion/orchestrator.py`:**
   - No Passo 3 do pipeline (`mine()`, linhas 190–193):
     ```python
     summaries = self._step_summarize(uncached_chunks, result)
     result.summaries_generated = len(summaries)
     ```
     `_step_summarize` gera os sumários L0 com o LLM (ou mock) e devolve a lista de `SummaryResult`.
   - No Passo 4 do pipeline (`mine()`, linhas 198–203):
     ```python
     nodes_created = self._step_store_sqlite(chunks, project_uuid, auto_tag, result)
     ```
     A lista `summaries` **nunca é repassada** para `_step_store_sqlite` nem associada aos objetos `chunk`!
   - Dentro de `_step_store_sqlite` (linhas 570–581):
     ```python
     for chunk in new_chunks:
         summary_text = chunk.cached_summary  # None para novos nós!
         nodes_to_create.append({
             "project_uuid": project_uuid,
             "label": f"{chunk.source_file}::{chunk.symbol_name}",
             "summary": summary_text,
             ...
         })
     ```
   - O campo `chunk.cached_summary` só é preenchido no Step 2.5 para nós reutilizados de execuções anteriores. Para todos os nós novos, `summary_text` é estritamente `None`.
2. **Inspeção Direta no Banco SQLite:**
   O `SELECT id, label, type, summary, tags FROM nodes` comprovou que todas as linhas recém-inseridas possuem `summary = NULL`.
3. **Comportamento das Tags:**
   `chunk.detected_tags` só é preenchido se o arquivo contiver palavras-chave heurísticas de parser (ex.: 'database', 'auth'). Se o analisador léxico não identificar nenhuma tag padrão, `detected_tags` é `[]`, o que é gravado como `NULL` no banco.
4. **Comportamento em `concierge_search`:**
   Ao enriquecer os resultados (`interface/mcp_server.py:1158`), o MCP server busca `node.get("summary", "")`. Como a coluna no SQLite é `NULL`, a busca retorna `summary: null`.

**Conclusão do Item 4.4:** Não se trata de defeito de formatação ou mapeamento da busca: **os sumários L0 gerados pelo LLM são gerados e imediatamente descartados pela memória, nunca sendo persistidos no banco de dados SQLite.**

---

## 2. Tabela Comparativa das Alternativas (Passo 4.3)

| Critério | Alternativa A (Checagem de IDs no Chroma antes de pular) | Alternativa B (Gravar file_hash apenas após persistência dos vetores) | Alternativa C (Coluna embedding_status na tabela nodes) | Alternativa D (Parâmetro force=True em concierge_mine) |
| :--- | :--- | :--- | :--- | :--- |
| **Descrição Resumida** | O crawler verifica se os IDs dos nós correspondentes ao arquivo existem no Chroma antes de considerá-lo inalterado. | Reordena os passos do pipeline, deixando `file_hash = NULL` no SQLite até que o Step 6 (Store Vector) tenha sucesso. | Adiciona coluna `embedding_status` em `nodes` (`PENDING`, `STORED`, `FAILED`) e faz transição de estados. | Adiciona flag `force: bool = False` que ignora o cache do crawler e reprocessa todos os arquivos. |
| **Arquivos de Produção Afetados** | `ingestion/crawler.py`, `ingestion/orchestrator.py` | `ingestion/orchestrator.py`, `storage/store.py`, `ingestion/crawler.py` | `storage/store.py`, `ingestion/orchestrator.py`, `ingestion/crawler.py` | `interface/mcp_server.py`, `ingestion/orchestrator.py`, `ingestion/crawler.py`, `middleware.py` |
| **Linhas Estimadas** | ~35–50 linhas | ~80–120 linhas | ~70–100 linhas (+ DDL migration) | ~20–30 linhas |
| **Efeito em Bancos Existentes (Recupera sozinho?)** | **SIM, 100% automático.** No próximo `concierge_mine`, detecta a ausência dos IDs no Chroma e reindexa. | **NÃO.** Nós já gravados com hash no passado continuam sendo pulados; exige script de reparo. | **PARCIAL.** Se o default da migração for `STORED`, não recupera; se for `PENDING`, força reindexação total. | **NÃO.** Requer intervenção manual do operador chamando `concierge_mine(..., force=True)`. |
| **Modo de Falha** | Se o Chroma estiver offline/inacessível na checagem, pode falhar de forma fechada (*fail closed*) ou forçar reprocessamento desnecessário. | Se o processo cair entre o Step 6 e o update do SQLite, gera nós órfãos sem hash. Se o cleanup rodar cedo, apaga nós novos. | Se a transação SQLite de status falhar, o estado do banco e do Chroma ficam dessincronizados. | Se mal utilizado em projetos grandes, gera consumo excessivo de cota de LLM e CPU para reprocessamento redundante. |
| **Custo de Desempenho** | **Desprezível.**<br>100 nós: 1,6 ms<br>1.000 nós: 9,0 ms<br>10.000 nós: 67,1 ms | **Moderado.** Exige um segundo passe de escrita (`UPDATE nodes`) em lote no SQLite WAL para cada arquivo. | **Moderado.** Exige atualização individual/lote de status no SQLite WAL no fim do pipeline. | **Zero** na execução padrão. **Alto** quando ativado manualmente (reprocessa tudo). |
| **Impacto de Schema** | **Nenhum.** Zero alterações em DDL do SQLite ou Chroma. | **Baixo/Semântico.** Não muda DDL, mas permite `file_hash` nulo temporariamente na tabela `nodes`. | **ALTO.** Requer alteração na tabela central `nodes` (`ALTER TABLE`), novo índice e migração de schema. | **Nenhum.** Apenas novo argumento na assinatura da ferramenta e métodos internos. |
| **Testes Necessários** | Testes de reconciliação de IDs parciais e totais; teste de comportamento com Chroma inacessível. | Testes de concorrência, testes de rollback de transação, testes de cleanup com hashes nulos. | Testes de migração de schema v3.8.0, testes de idempotência de status, testes de recuperação de falhas. | Testes de API da ferramenta MCP com e sem `force=True`, testes de sobrecarga de cache. |

---

## 3. Decisões Humanas Exigidas por Cada Alternativa

1. **Se escolhida a Alternativa A:**
   - Decidir a política quando o backend vetorial estiver indisponível durante o crawl: abortar imediatamente o pipeline (*fail closed* com mensagem de erro explícita) ou considerar ausente e tentar re-gerar (*fail open*)?
   - Decidir se a checagem deve ser em lote único por projeto antes do crawl ou sob demanda por arquivo/hash.
2. **Se escolhida a Alternativa B:**
   - Decidir como manter a integridade referencial com `cleanup_obsolete_nodes` e se o garbage collection deve ser totalmente postergado para depois da confirmação do Chroma.
   - Decidir como lidar com quedas do processo no meio do caminho sem deixar nós com `file_hash = NULL`.
3. **Se escolhida a Alternativa C:**
   - Decidir se o projeto aceita expandir o DDL da tabela central `nodes`, rompendo com o princípio do Caminho B de manter o schema enxuto e estável.
   - Decidir o valor padrão na migração para bases de dados já existentes (`PENDING` vs. `STORED`).
4. **Se escolhida a Alternativa D:**
   - Decidir se `force=True` deve reprocessar também os sumários LLM (com custo financeiro/cota) ou apenas forçar re-embedding vetorial.
   - Decidir se a ferramenta deve ser exposta livremente no MCP ou se requer permissão de manutenção/governor.
5. **Composições Possíveis (ex.: A + D):**
   - Decidir se a Alternativa A deve ser o mecanismo de autocura automática, e a Alternativa D um mecanismo administrativo explícito complementar.

---

## 4. Proposta de Severidade

- **F4-008 (Falha de rede/modelo no 1º mine congela o índice em 0 vetores permanentemente):**
  - **Proposta:** **CRÍTICA**.
  - **Justificativa:** A evidência com o modelo real e bootstrap de produção comprovou que:
    1. A falha ocorre silenciosamente na primeira execução sem rede prévia, reportando falsamente `success: true` e `errors: []`.
    2. O repositório é marcado como limpo no SQLite.
    3. Qualquer execução subsequente, mesmo com rede normalizada e modelo carregado, pula todos os arquivos e deixa o sistema de busca semântica permanentemente inoperante sem avisar o usuário.
- **F4-009 (Falha parcial de lotes ou reset_collection deixa o índice incompleto ou zerado):**
  - **Proposta:** **ALTA**.
  - **Justificativa:** Comprovamos que a ferramenta administrativa oficial `reset_collection` cria o estado quebrado e que falhas parciais em lotes não se recuperam sozinhas.
- **F4-010 (Sumários L0 gerados pelo LLM são descartados e gravados como NULL no SQLite):**
  - **Proposta:** **ALTA**.
  - **Justificativa:** Chamadas a modelos de linguagem são executadas, gastam tempo e cota, são contabilizadas no resultado de mineração (`summaries_generated`), mas o código descarta o retorno e persiste `summary = NULL` em todas as novas entidades no banco de dados.
