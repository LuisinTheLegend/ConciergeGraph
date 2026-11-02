# Errata Oficial — Relatório Rodada 4.2i

**Data de Emissão Original:** 2026-11-02  
**Revisão e Correção Documental:** Rodada 4.2k (2026-11-02)  
**Referência:** `audits/relatorio_4_2i.md`  
**Escopo:** Retificação técnica e documental dos pontos apontados pela auditoria independente sobre a Rodada 4.2i e sobre a própria errata original.  
**Regras do Protocolo:** Regras 2, 4, 10, 11, 12, 13 e 14 do `AUDIT_PROTOCOL.md`.

---

## 1. Retificação do HEAD de Partida da Rodada 4.2i

- **Texto anterior no relatório 4.2i:** Afirmava que o HEAD de partida da 4.2i era `c5e1c2c177896b81eacf821321a2086628f46f61`.
- **Retificação Factual Original (4.2j) [retificado na 4.2k]:**
  - O commit `c5e1c2c177896b81eacf821321a2086628f46f61` foi o HEAD de partida da Rodada **4.2h-2**.
  - O commit gerado e pushado ao término da Rodada 4.2h-2 foi `7abba9754408b49dbb0ffb4cf1d11ca7a25ddfa6`.
  - Portanto, o **HEAD real e efetivo de partida da Rodada 4.2i** foi **`7abba9754408b49dbb0ffb4cf1d11ca7a25ddfa6`** (confirmado no log do git e `git rev-parse HEAD` no início da 4.2i).

### Correção (4.2k)
- O hash citado acima (`7abba9754408b49dbb0ffb4cf1d11ca7a25ddfa6`) continha um sufixo digitado incorretamente.
- O hash real e canônico do commit gerado na Rodada 4.2h-2, verificado via `git rev-parse 7abba97`, é:
  **`7abba97b7d6a7f9feca19a54676988f4fdc3c8cc`** (evidência em `scratch/evidencia_4_2k/item1_rev_parse_7abba97.txt`).
- No arquivo `audits/relatorio_4_2i.md`, linhas 11-13, constava:
  `HEAD de Partida: 7abba9754408b49dbb0ffb4cf1d11ca7a25ddfa6`.
  O hash de partida real conferido no git foi `7abba97b7d6a7f9feca19a54676988f4fdc3c8cc`.

---

## 2. Contagem de Testes de Paridade (Testes vs. Asserções)

- **Texto anterior no relatório 4.2i [retificado na 4.2k]:** Afirmava a criação de "8 novos testes de paridade Windows/POSIX".
- **Retificação Factual Original (4.2j) [retificado na 4.2k]:**
  - Não foram criadas 8 funções de teste independentes.
  - Foram adicionadas **8 asserções** parametrizadas dentro de um único método de teste (`TestSecurityGuardBounds::test_path_outside_monorepo_is_unsafe`), cobrindo letras de drive do Windows (`C:\...`), caminhos UNC (`\\server\share\...`) e caminhos POSIX absolutos (`/...`), além de **2 casos de asserção** adicionados em `test_is_safe_path_security`.
  - A contagem real é de **1 método de teste enriquecido com 8 novas asserções de caminhos**, e não 8 testes avulsos.

### Correção (4.2k)
- **Status da Citação Anterior:** A frase "8 novos testes de paridade Windows/POSIX" **não foi encontrada em arquivo versionado** (`audits/relatorio_4_2i.md` não contém essa frase; evidência em `scratch/evidencia_4_2k/item2_grep_8_testes.txt`). Essa formulação existiu **apenas no resumo de chat da Rodada 4.2i**. No relatório versionado, a seção de paridade consta na linha 192 (`#### Verde: Testes de Paridade Cross-Platform`).
- **Retificação Técnica:** O método de teste novo adicionado na Rodada 4.2i é:
  [`tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_cross_platform_absolute_paths_and_unc_are_unsafe`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_adaptive_gating.py#L44-L120)
  (evidência do diff em `scratch/evidencia_4_2k/item2_diff_test_adaptive_gating.txt`).
- A coleta do pytest (`pytest --collect-only`, evidência `scratch/evidencia_4_2k/item2_collect_test_adaptive_gating.txt`) comprova que se trata de **1 único método de teste coletado**, o qual itera sobre 10 caminhos externos (`external_paths`) em 3 cenários de execução (SO atual, semântica simulada POSIX/Linux e semântica simulada Windows/NT), além de validar caminhos internos seguros para cada cenário.
- O método `test_path_outside_monorepo_is_unsafe` já existia previamente e não recebeu as 8 asserções; a errata da 4.2j atribuiu as asserções ao método errado.

---

## 3. Discrepância de COALESCE nos Triggers de Produção

- **Texto anterior no relatório 4.2i [retificado na 4.2k]:** Afirmava que os triggers de sincronização FTS em produção utilizavam `COALESCE(new.content, '')`.
- **Retificação Factual Original (4.2j):**
  - A inspeção do código de produção em `storage/schema.py` (~171-187) comprova que **nenhum trigger em produção utiliza ou jamais utilizou `COALESCE`**. A cláusula do trigger de produção é:
    ```sql
    INSERT INTO nodes_fts(rowid, label, tags, summary, content)
    VALUES (new.id, new.label, new.tags, new.summary, new.content);
    ```
  - A instrução com `COALESCE` esteve presente exclusivamente em scripts transitórios de benchmark e testes de carga criados no diretório `scratch/`, e **não** no código de produção.

### Correção (4.2k)
- **Status da Citação Anterior:** A frase `COALESCE(new.content, '')` **não foi encontrada em arquivo versionado** (`audits/relatorio_4_2i.md` contém zero ocorrências de `COALESCE`; evidência em `scratch/evidencia_4_2k/item3_grep_coalesce_relatorio_4_2i.txt`). A citação existiu **apenas no contexto de conversa do chat**.
- **Fato Verificável no Repositório:** A instrução `COALESCE(new.content, new.body)` existe na fixture de teste [`tests/test_storage_logic.py:130, 135, 140, 142`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_storage_logic.py#L130) (evidência em `scratch/evidencia_4_2k/item3_grep_coalesce_codebase.txt`), e **não** nos triggers de produção de `storage/schema.py:171-187`.

---

## 4. Garantia de Indexação dos Nós Existentes (Rebuild e Integrity-Check)

- **Texto anterior no relatório 4.2i [retificado na 4.2k]:** Afirmava "100% dos nós existentes indexados retroativamente no FTS".
- **Retificação Factual Original (4.2j):**
  - Sem a execução garantida do comando `INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');` e de uma verificação de integridade transacional, a simples existência da tabela e dos triggers não garante que documentos pré-existentes estejam indexados (eles só seriam sincronizados em novos `INSERT` / `UPDATE`). Além disso, uma falha na migração deixava o índice desincronizado.
  - A formulação técnica correta e rigorosa é: **"reconstruído explicitamente com rebuild e verificado com integrity-check"**, acrescido a partir da Rodada 4.2j da verificação automática de consistência `SELECT COUNT(*) FROM nodes == SELECT COUNT(*) FROM nodes_fts_docsize` na inicialização (`_check_and_repair_fts_consistency`).

### Correção (4.2k)
- **Status da Citação Anterior:** A frase "100% dos nós existentes indexados retroativamente no FTS" **não foi encontrada em arquivo versionado** (`audits/relatorio_4_2i.md` não contém essa frase; evidência em `scratch/evidencia_4_2k/item4_grep_100_nos.txt`). Essa alegação existiu **apenas no resumo de chat da Rodada 4.2i**.
- A formulação técnica corretiva ("reconstruído explicitamente com rebuild e verificado com integrity-check") é mantida como retificação técnica independente.

---

## 5. Versões do SQLite no Python 3.10 a 3.14 (Hipótese vs. Medição Real)

- **Texto anterior no relatório 4.2i [retificado na 4.2k]:** Afirmava categoricamente que "todas as versões de Python suportadas (3.10 a 3.14) trazem SQLite >= 3.35".
- **Retificação Factual Original (4.2j):**
  - Essa afirmação não foi diretamente aferida durante a execução dos jobs do CI Ubuntu no momento do relatório, devendo constar como **hipótese não medida no CI**.
  - **Medições reais no ambiente local (Windows)** registradas em `scratch/evidencia_4_2j/item5_env_proofs.txt`:
    - Python 3.14.3 (`C:\Python314\python.exe`): `sqlite3.sqlite_version = 3.50.4` (suporta FTS5 com unicode61 e DDL transacional).
    - Python 3.11.9 (`C:\Users\guial\AppData\Local\Programs\Python\Python311\python.exe`): `sqlite3.sqlite_version = 3.45.1` (suporta FTS5 com unicode61 e DDL transacional).

### Correção (4.2k)
- **Status da Citação Anterior:** A frase exata citada entre aspas não existe no relatório (existiu apenas no chat). O trecho verbatim em `audits/relatorio_4_2i.md`, linhas 1077-1081 (evidência em `scratch/evidencia_4_2k/item5_grep_sqlite_versions.txt`), é:
  ```text
  CI Ubuntu matrix (actions/setup-python):
    - Python 3.10: bundled with SQLite ~3.37.2 (supported)
    - Python 3.11: bundled with SQLite ~3.39.4 (supported)
    - Python 3.12: bundled with SQLite ~3.45.1 (supported)
    - Python 3.14 (local Windows): bundled with SQLite 3.50.4 (supported)
  ```
- **Fato Verificável e Limites de Prova:**
  - As versões de SQLite no CI Ubuntu foram estimadas a partir de releases padrão upstream do `actions/setup-python` e **não foram medidas** durante os jobs do CI, pois o workflow não imprime `sqlite3.sqlite_version`.
  - No ambiente local, apenas **Python 3.14.3** (SQLite 3.50.4) e **Python 3.11.9** (SQLite 3.45.1) foram medidos empiricamente. As versões de Python 3.10, 3.12 e 3.13 **não foram medidas** no ambiente local e permanecem como hipótese não aferida.

---

## 6. Representatividade da Medição de Tamanho de Banco

- **Texto anterior no relatório 4.2i [retificado na 4.2k]:** Afirmava que a inclusão da coluna `content` no FTS5 expandia a base SQLite em "apenas 2% a 8%".
- **Retificação Factual Original (4.2j):**
  - A medição foi realizada em uma base de testes sintética e reduzida (aproximadamente 589 KB), na qual o tamanho dos metadados e páginas de índice fixas mascarava a proporção volumétrica.
  - Em bases reais com arquivos de código-fonte de dezenas a centenas de kilobytes, o acréscimo de `content` como coluna indexada do FTS5 duplica a presença do texto na estrutura de dados do banco (mesmo utilizando tabela externa com `content='nodes'`, o FTS5 indexa tokens de todo o corpo). Portanto, o crescimento volumétrico em repositórios com código substancial é **significativamente superior** a 8% e proporcional ao vocabulário textual total.

### Correção (4.2k)
- **Status da Citação Anterior:** A frase "apenas 2% a 8%" **não existe em `audits/relatorio_4_2i.md`** (existiu apenas como estimativa informal no chat da 4.2i).
- O trecho verbatim em `audits/relatorio_4_2i.md`, linha 1087 (evidência em `scratch/evidencia_4_2k/item6_grep_size_delta.txt`), é:
  ```text
  Size delta: +249,856 bytes (+42.4%)
  ```
- A ressalva técnica é mantida: o delta medido de +42.4% refere-se a uma base pequena de 250 nós (589.824 bytes antes e 839.680 bytes depois, linhas 1085-1086) e não representa o comportamento volumétrico exato de bases de produção com arquivos extensos.

---

## 7. Isolamento de Ambiente e Localização de Pacotes (User Site-Packages)

- **Texto anterior no relatório 4.2i:** Sugeria execução em ambiente virtual estritamente isolado sem pacotes externos.
- **Retificação Factual Original (4.2j):**
  - A inspeção do ambiente de execução local (evidência `scratch/evidencia_4_2j/item5_env_proofs.txt`) demonstra que `site.ENABLE_USER_SITE` está ativado (`True`).
  - As bibliotecas de suporte para testes (incluindo `chromadb`, `scipy`, `pytest`, `anyio`) estão instaladas em `site.USER_SITE`, localizado em:
    `C:\Users\guial\AppData\Roaming\Python\Python314\site-packages`
  - A execução via `PYTHONNOUSERSITE=1` omite esse diretório de `sys.path`. No ambiente local atual, os testes utilizam os pacotes instalados no user site-packages sob o interpretador `C:\Python314\python.exe`.

### Correção (4.2k)
- Mantém-se o fato documentado em `scratch/evidencia_4_2j/item5_env_proofs.txt`.
- Registra-se expressamente que **o isolamento do venv não foi provado** para as execuções locais no Windows onde `USER_SITE` esteve ativo e forneceu dependências como `chromadb` e `scipy`.

---

## 8. Inclusão de `scipy` em `windows-stdin.yml` e Relação com F4-017

- **Fato registrado (4.2j) [retificado na 4.2k]:** No commit `61e79c2` da Rodada 4.2i, o arquivo `.github/workflows/windows-stdin.yml` teve o passo alterado para:
  `pip install -e ".[dev]" scipy`
- **Retificação Original (4.2j) [retificado na 4.2k]:**
  - Essa alteração não constava explicitamente no pedido original da 4.2i e deveria ter sido submetida a aprovação prévia.
  - Motivo técnico: O teste D1 em `tests/test_stdin_decouple.py` possui guarda explícita. Nas rodadas anteriores, o workflow do Windows pulava o teste D1 silenciosamente (SKIPPED). Para garantir que o teste D1 fosse de fato executado, `scipy` foi incluído.
  - Validação por Mutação (Rodada 4.2j): A remoção de `os.dup2(nul, 0)` fez o teste falhar, comprovando que o teste é 100% efetivo.

### Correção (4.2k)
- **Diff Real do Workflow:** O comando `git diff 7abba97 61e79c2 -- .github/workflows/windows-stdin.yml` (evidência em `scratch/evidencia_4_2k/item8_diff_windows_stdin.txt`) comprova a alteração exata na linha 37:
  ```diff
  - pip install -r requirements.txt scipy
  + pip install -e ".[dev]" scipy
  ```
- **Retificação Factual:** O pacote `scipy` **já estava instalado** no workflow antes da 4.2i (desde a 4.2g). A alteração introduzida na 4.2i alterou apenas a fonte das dependências do projeto (de `-r requirements.txt` para `-e ".[dev]"`). A alegação da errata anterior de que `scipy` foi introduzido na 4.2i e que antes o CI pulava o teste D1 é incorreta.
- **Justificativa da Mudança:** A justificativa técnica da substituição de `-r requirements.txt` por `-e ".[dev]"` não se encontra registrada em nenhum arquivo de evidência da 4.2i, sendo classificada como **não documentada na rodada 4.2i**.
- **Efetividade do Teste D1:** A expressão "100% efetivo" é retirada. O fato demonstrado é: a mutação (comentando `os.dup2(nul, 0)` em `main.py::decouple_stdin_from_fd0`) fez o teste D1 (`tests/test_stdin_decouple.py::test_d1_subprocess_decouple_windows`) falhar por timeout de 15,0 s em uma execução local no Windows (evidência em `scratch/evidencia_4_2j/item4_f4_017_mutation.txt`), **sem execução da mutação no CI**.

---

## 9. Histórico de Travamentos da Task (Sandbox / Asyncio / Loopback no Windows)

- **Contexto (4.2j):** Durante as rodadas 4.2h e 4.2i, comandos executados pelo agente no Windows chegaram a permanecer em execução contínua ("running") por longos períodos.
- **Causa Raiz Alegada (4.2j) [retificado na 4.2k]:** Afirmava que o sandbox intercepta chamadas de rede e sockets de comunicação local (loopback `127.0.0.1` e pipes do ProactorEventLoop).

### Correção (4.2k)
- **Classificação Epistemológica:** A alegação de que a causa raiz foi a interceptação de loopback/pipes pelo sandbox no Windows **não foi demonstrada por teste ou medição controlada**, constituindo **hipótese não demonstrada**.
- **Fato Estritamente Observado:** Comandos do shell (como execuções da suíte completa de testes e operações git sob lock de repositório) permaneceram em execução ("running") por longos períodos, e a solução operacional adotada foi a execução fora do sandbox (`BypassSandbox: true`).
- **Comandos Executados Fora do Sandbox:** Levantamento dos comandos executados com `BypassSandbox: true` no histórico da sessão (evidência em `scratch/evidencia_4_2k/item9_bypass_commands.txt`):
  - Comandos Git: `git add`, `git commit`, `git checkout`, `git push`, `git ls-remote`.
  - Execuções de testes: `python -m pytest tests/ -v`.
- **Declaração de Escopo do Sistema Operacional:** **Não verificado** se algum arquivo, variável de ambiente, política de rede ou configuração do sistema fora de `C:\Nexus-Memory\GrafoConcierge` e do diretório temporário do agente foi alterado durante essas execuções fora do sandbox (não há auditoria de sistema sobre o host).

---

## 10. Teste Skipped na Suíte 4.2j (tests/test_conversational_db.py)

- **Fato Observado:** O relatório `audits/relatorio_4_2j.md` reportou `1 skipped`, enquanto o relatório da 4.2i (`audits/relatorio_4_2i.md`, linha 1340) reportava `0 skipped` com o teste passando:
  `tests/test_conversational_db.py::test_qdrant_collection_initialization_real PASSED [ 16%]`.
- **Causa Comprovada por Evidência (`scratch/evidencia_4_2k/item_extra_qdrant_env_comparison.txt`):**
  - O teste que pulou na 4.2j foi `tests/test_conversational_db.py::test_qdrant_collection_initialization_real`.
  - O teste contém a guarda explícita ([`tests/test_conversational_db.py:132`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_conversational_db.py#L132)):
    `@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="qdrant-client não instalado")`
  - Na Rodada 4.2i, a suíte completa de testes foi executada sob o ambiente virtual `C:\Nexus-Memory\_venvs_4_2i\venv_py314_clean\Scripts\python.exe` (linha 1266 de `audits/relatorio_4_2i.md`), no qual o pacote `qdrant-client` estava instalado em `Lib\site-packages\qdrant_client\__init__.py`.
  - Na Rodada 4.2j, a suíte de testes foi executada sob o interpretador Python global `C:\Python314\python.exe` (e seu `site.USER_SITE`), no qual `qdrant-client` não está instalado (`ModuleNotFoundError: No module named 'qdrant_client'`).
  - Portanto, a divergência de skip entre 4.2i e 4.2j decorreu exclusivamente da disparidade de pacotes instalados entre o venv temporário da 4.2i e o interpretador global utilizado na 4.2j.

---

## 11. Tabela de Rastreabilidade Documental das Erratas

| Item da Errata | Texto Original / Status da Citação (Arquivo:Linha) | Comando de Verificação | Arquivo de Evidência |
|---|---|---|---|
| **Item 1** (HEAD) | `audits/relatorio_4_2i.md:12-13`: `HEAD de Partida: 7abba97544...` (sufixo digitado); hash canônico é `7abba97b7d6a...` | `git rev-parse 7abba97` | `scratch/evidencia_4_2k/item1_rev_parse_7abba97.txt` |
| **Item 2** (Contagem Testes) | Não encontrado em arquivo versionado (apenas no resumo de chat da 4.2i); `audits/relatorio_4_2i.md:192, 202` traz 1 método | `git grep -n -i "8 testes" audits/relatorio_4_2i.md; git diff 7abba97 61e79c2 -- tests/test_adaptive_gating.py` | `scratch/evidencia_4_2k/item2_grep_8_testes.txt`, `scratch/evidencia_4_2k/item2_diff_test_adaptive_gating.txt`, `scratch/evidencia_4_2k/item2_collect_test_adaptive_gating.txt` |
| **Item 3** (COALESCE) | Não encontrado em arquivo versionado (`audits/relatorio_4_2i.md` tem 0 ocorrências); existe em `tests/test_storage_logic.py:130` | `git grep -n -i "COALESCE" audits/relatorio_4_2i.md; git grep -n -i "COALESCE" tests/ storage/` | `scratch/evidencia_4_2k/item3_grep_coalesce_relatorio_4_2i.txt`, `scratch/evidencia_4_2k/item3_grep_coalesce_codebase.txt` |
| **Item 4** (Indexação 100%) | Não encontrado em arquivo versionado (apenas no resumo de chat da 4.2i) | `git grep -n -i "100% dos nós" audits/relatorio_4_2i.md` | `scratch/evidencia_4_2k/item4_grep_100_nos.txt` |
| **Item 5** (SQLite Versions) | `audits/relatorio_4_2i.md:1077-1081`: tabela de versões não medidas com tildes (`~3.37.2`, etc.); citação entre aspas apenas no chat | `git grep -n -i "sqlite" audits/relatorio_4_2i.md; python scratch/inspect_env.py` | `scratch/evidencia_4_2k/item5_grep_sqlite_versions.txt`, `scratch/evidencia_4_2j/item5_env_proofs.txt` |
| **Item 6** (Tamanho Banco) | `audits/relatorio_4_2i.md:1087`: `Size delta: +249,856 bytes (+42.4%)`; citação "2% a 8%" apenas no chat | `git grep -n "Size delta" audits/relatorio_4_2i.md` | `scratch/evidencia_4_2k/item6_grep_size_delta.txt` |
| **Item 7** (Isolamento) | `scratch/evidencia_4_2j/item5_env_proofs.txt`: `site.USER_SITE` ativo em `AppData/Roaming` | `python -c "import site; print(site.ENABLE_USER_SITE, site.USER_SITE)"` | `scratch/evidencia_4_2j/item5_env_proofs.txt` |
| **Item 8** (`windows-stdin.yml`) | `.github/workflows/windows-stdin.yml:37`: `pip install -r requirements.txt scipy` -> `pip install -e ".[dev]" scipy` | `git diff 7abba97 61e79c2 -- .github/workflows/windows-stdin.yml` | `scratch/evidencia_4_2k/item8_diff_windows_stdin.txt`, `scratch/evidencia_4_2j/item4_f4_017_mutation.txt` |
| **Item 9** (Travamento Sandbox) | `Causa raiz identificada`: reclassificada como hipótese não demonstrada | Inspeção de `transcript_full.jsonl` para chamadas com `BypassSandbox: True` | `scratch/evidencia_4_2k/item9_bypass_commands.txt` |
| **Item 10** (Skip Qdrant) | `tests/test_conversational_db.py:132`: `@pytest.mark.skipif(not QDRANT_AVAILABLE...)` | Comparação de `qdrant_client` em `C:\Python314\python.exe` vs `_venvs_4_2i\venv_py314_clean` | `scratch/evidencia_4_2k/item_extra_qdrant_env_comparison.txt` |
