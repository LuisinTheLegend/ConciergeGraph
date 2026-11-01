# Errata da Rodada 4.2g e do Relatório do Teste de Aceitação no Claude Desktop

> **Data:** 2026-11-01  
> **Referência:** Auditoria independente da Rodada 4.2g (`96ba4d0`) e do log do servidor `"grafo-teste"` no teste de aceitação no Claude Desktop real, com correções de segurança tratadas na Rodada 4.2h.

---

## 1. Resumo indevido de "sem erros" omitindo HTTP 401 na OpenAI e 9 tracebacks `Event loop is closed / Task exception was never retrieved`

- **O que foi afirmado após a 4.2g / Fase B do teste no Claude Desktop:** O resumo da extração de logs afirmou que o servidor operou "sem erros" durante a mineração com `GRAFO_LLM_MODEL=none`.
- **Correção factual:** Embora o travamento de `stdio` (`F4-017`) estivesse resolvido e os 3 arquivos `.md` tenham sido minerados e vetorizados no Chroma (`3 nós` e `3 vetores`), o log do servidor `"grafo-teste"` continha:
  1. **Chamadas indevidas à API da OpenAI com erro `HTTP 401` de chave rejeitada (`F4-019`, Crítica):** Mesmo com `GRAFO_LLM_MODEL=none`, `ingestion/summarizer.py` (`generate_async`) não desligava o LLM; qualquer modelo que não começasse com `"gemini-"` (e sem `base_url`) caía no bloco `else:` instanciando `openai.AsyncOpenAI(api_key=self.api_key)` e enviando a chave configurada no ambiente para `https://api.openai.com/v1/chat/completions`.
  2. **9 tracebacks `RuntimeError: Event loop is closed` / `Task exception was never retrieved` (`F4-020`, Média):** Como `openai.AsyncOpenAI` era instanciado a cada tentativa sem `async with` (nem `await client.close()`) e `ingestion/orchestrator.py` executava `asyncio.run(...)` por arquivo com 3 tentativas de retry (`tenacity`), o fechamento do event loop antes do `aclose()` do cliente `httpx` interno gerou `3 arquivos × 3 tentativas = 9 tracebacks` no log.
- **Resolução na Rodada 4.2h:**
  - `F4-019` e `F4-020` tratados em `ingestion/summarizer.py`, `ingestion/orchestrator.py`, `main.py` e `interface/cli.py` (desligamento real em `none`/`off`/`disabled`/vazio, exigência de `GRAFO_LLM_PROVIDER` explícito para provedores não-Gemini sem `base_url`, remoção total de fallback entre provedores, e fechamento determinístico dos clientes via `with` / `async with`).
  - Nos relatórios de evidência (a partir da 4.2h), é proibido resumir logs como "sem erros": a contagem literal de linhas `ERROR` e `WARNING` por categoria em cada execução é extraída mecanicamente dos arquivos de evidência.

---

## 2. Descrição incompleta das colunas indexadas pela tabela virtual `nodes_fts` (FTS5)

- **O que foi afirmado na análise pós-4.2g:** Foi afirmado que a tabela FTS5 `nodes_fts` indexava apenas `(label, summary)`.
- **Correção factual:** Conforme definido em `storage/schema.py:163-168`:
  ```sql
  CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
      label,
      tags,
      summary,
      content='nodes',
      content_rowid='rowid'
  );
  ```
  O esquema real indexa **`(label, tags, summary)`** — e **não** indexa `nodes.content`. Quando o LLM está desativado (`GRAFO_LLM_MODEL=none`), `nodes.summary` permanece `NULL`, de modo que a busca lexical FTS5 consulta apenas `label` e `tags`, não alcançando palavras presentes exclusivamente em `nodes.content`.
- **Encaminhamento:** Registrado como achado **`F4-018` (`GRAVE`, `ABERTO`)** em `audits/fase4-achados.md`, planejado para a Rodada `4.2i` (fora do escopo da Rodada `4.2h`).

