# Errata Oficial — Relatório Rodada 4.2i

**Data de Emissão Original:** 2026-11-02  
**Revisão e Correção Documental:** Rodada 4.2k (2026-11-02); Rodada 4.2l (2026-11-02)  
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
- **Status da Citação Anterior [retificado na 4.2l]:** A frase "8 novos testes de paridade Windows/POSIX" **não foi encontrada em arquivo versionado** (`audits/relatorio_4_2i.md` não contém essa frase; evidência em `scratch/evidencia_4_2k/item2_grep_8_testes.txt`). Essa formulação existiu **apenas no resumo de chat da Rodada 4.2i** [retificado na 4.2l]. No relatório versionado, a seção de paridade consta na linha 192 (`#### Verde: Testes de Paridade Cross-Platform`).
- **Retificação Técnica:** O método de teste novo adicionado na Rodada 4.2i é:
  [`tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_cross_platform_absolute_paths_and_unc_are_unsafe`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_adaptive_gating.py#L44-L120)
  (evidência do diff em `scratch/evidencia_4_2k/item2_diff_test_adaptive_gating.txt`).
- A coleta do pytest (`pytest --collect-only`, evidência `scratch/evidencia_4_2k/item2_collect_test_adaptive_gating.txt`) comprova que se trata de **1 único método de teste coletado**, o qual itera sobre 10 caminhos externos (`external_paths`) em 3 cenários de execução (SO atual, semântica simulada POSIX/Linux e semântica simulada Windows/NT), além de validar caminhos internos seguros para cada cenário.
- O método `test_path_outside_monorepo_is_unsafe` já existia previamente e não recebeu as 8 asserções; a errata da 4.2j atribuiu as asserções ao método errado.

### Correção (4.2l)
- **Retificação da Citação do Resumo de Chat:** A redação citada na errata da 4.2k ("8 novos testes de paridade Windows/POSIX") não corresponde ao texto original do resumo de chat da Rodada 4.2i entregue pelo dono. A citação original verbatim é **"8 testes de paridade cross-platform"** (evidência em `scratch/evidencia_4_2l/busca_frase4_8_testes_paridade.txt`).
- **Status no Repositório Versionado:** No relatório versionado, a subseção correspondente é intitulada `#### Verde: Testes de Paridade Cross-Platform (`scratch/evidencia_4_2i/b0_green_security_guard_parity.txt`)` (`audits/relatorio_4_2i.md:192`). O teste implementado na Rodada 4.2i foi 1 único método de teste: [`tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_cross_platform_absolute_paths_and_unc_are_unsafe`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_adaptive_gating.py#L44-L120), que itera sobre 10 caminhos em 3 plataformas (evidências em `scratch/evidencia_4_2k/item2_diff_test_adaptive_gating.txt` e `scratch/evidencia_4_2k/item2_collect_test_adaptive_gating.txt`).

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
- **Status da Citação Anterior [retificado na 4.2l]:** A frase `COALESCE(new.content, '')` **não foi encontrada em arquivo versionado** (`audits/relatorio_4_2i.md` contém zero ocorrências de `COALESCE`; evidência em `scratch/evidencia_4_2k/item3_grep_coalesce_relatorio_4_2i.txt`). A citação existiu **apenas no contexto de conversa do chat** [retificado na 4.2l].
- **Fato Verificável no Repositório:** A instrução `COALESCE(new.content, new.body)` existe na fixture de teste [`tests/test_storage_logic.py:130, 135, 140, 142`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_storage_logic.py#L130) (evidência em `scratch/evidencia_4_2k/item3_grep_coalesce_codebase.txt`), e **não** nos triggers de produção de `storage/schema.py:171-187`.

### Correção (4.2l)
- **Origem da Expressão COALESCE:** No resumo de chat da Rodada 4.2i entregue pelo dono, a expressão citada foi `COALESCE(new.content, new.body)`, e não `COALESCE(new.content, '')`.
- **Status no Repositório Versionado:** A instrução `COALESCE(new.content, new.body)` consta em `audits/fase4-achados.md:321`, `scratch/evidencia_4_2i/apply_b1_changes.py:431, 443` e nas fixtures de teste `tests/test_storage_logic.py:130, 142` (evidência em `scratch/evidencia_4_2l/item1_grep_coalesce_codebase.txt`). Em `audits/relatorio_4_2i.md`, a palavra `COALESCE` possui zero ocorrências. Os triggers de produção em `storage/schema.py:171-187` jamais utilizaram `COALESCE`.

---

## 4. Garantia de Indexação dos Nós Existentes (Rebuild e Integrity-Check)

- **Texto anterior no relatório 4.2i [retificado na 4.2k]:** Afirmava "100% dos nós existentes indexados retroativamente no FTS".
- **Retificação Factual Original (4.2j):**
  - Sem a execução garantida do comando `INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');` e de uma verificação de integridade transacional, a simples existência da tabela e dos triggers não garante que documentos pré-existentes estejam indexados (eles só seriam sincronizados em novos `INSERT` / `UPDATE`). Além disso, uma falha na migração deixava o índice desincronizado.
  - A formulação técnica correta e rigorosa é: **"reconstruído explicitamente com rebuild e verificado com integrity-check"**, acrescido a partir da Rodada 4.2j da verificação automática de consistência `SELECT COUNT(*) FROM nodes == SELECT COUNT(*) FROM nodes_fts_docsize` na inicialização (`_check_and_repair_fts_consistency`).

### Correção (4.2k)
- **Status da Citação Anterior [retificado na 4.2l]:** A frase "100% dos nós existentes indexados retroativamente no FTS" **não foi encontrada em arquivo versionado** (`audits/relatorio_4_2i.md` não contém essa frase; evidência em `scratch/evidencia_4_2k/item4_grep_100_nos.txt`). Essa alegação existiu **apenas no resumo de chat da Rodada 4.2i** [retificado na 4.2l].
- A formulação técnica corretiva ("reconstruído explicitamente com rebuild e verificado com integrity-check") é mantida como retificação técnica independente.

### Correção (4.2l)
- **Retificação da Origem da Frase:** A frase "100% dos nós existentes indexados retroativamente no FTS" **não foi encontrada em arquivo versionado nem no histórico pesquisado; origem não determinada** (evidência em `scratch/evidencia_4_2l/busca_frase1_100_nos.txt`). A busca literal e insensível a maiúsculas (`git grep -n -i -F` no HEAD e no histórico completo da sessão `transcript_full.jsonl`) confirmou zero ocorrências da frase no relatório ou nas mensagens da rodada 4.2i. O resumo de chat da 4.2i entregue pelo dono também não contém essa frase. Retifica-se a atribuição de que a frase teria existido no resumo de chat da 4.2i.
- **Retificação Técnica:** Permanece inalterada a retificação técnica de que a garantia de indexação decorre exclusivamente do comando explícito de rebuild e integrity-check (e da checagem automática de consistência implementada na 4.2j).

---

## 5. Versões do SQLite no Python 3.10 a 3.14 (Hipótese vs. Medição Real)

- **Texto anterior no relatório 4.2i [retificado na 4.2k]:** Afirmava categoricamente que "todas as versões de Python suportadas (3.10 a 3.14) trazem SQLite >= 3.35".
- **Retificação Factual Original (4.2j):**
  - Essa afirmação não foi diretamente aferida durante a execução dos jobs do CI Ubuntu no momento do relatório, devendo constar como **hipótese não medida no CI**.
  - **Medições reais no ambiente local (Windows)** registradas em `scratch/evidencia_4_2j/item5_env_proofs.txt`:
    - Python 3.14.3 (`C:\Python314\python.exe`): `sqlite3.sqlite_version = 3.50.4` (suporta FTS5 com unicode61 e DDL transacional).
    - Python 3.11.9 (`C:\Users\guial\AppData\Local\Programs\Python\Python311\python.exe`): `sqlite3.sqlite_version = 3.45.1` (suporta FTS5 com unicode61 e DDL transacional).

### Correção (4.2k)
- **Status da Citação Anterior [retificado na 4.2l]:** A frase exata citada entre aspas não existe no relatório (existiu apenas no chat) [retificado na 4.2l]. O trecho verbatim em `audits/relatorio_4_2i.md`, linhas 1077-1081 (evidência em `scratch/evidencia_4_2k/item5_grep_sqlite_versions.txt`), é:
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

### Correção (4.2l)
- **Retificação da Origem da Frase:** A frase "todas as versões de Python suportadas (3.10 a 3.14) trazem SQLite >= 3.35" **não foi encontrada em arquivo versionado nem no histórico pesquisado; origem não determinada** (evidência em `scratch/evidencia_4_2l/busca_frase2_sqlite_335.txt`). A busca por `git grep -n -i -F` no HEAD e no histórico `transcript_full.jsonl` não encontrou essa frase em nenhuma mensagem original da 4.2i, e o resumo de chat da 4.2i entregue pelo dono também não a contém. Retifica-se a afirmação de que a citação exata entre aspas existiu no chat.
- **Fato Aferido no Relatório Versionado:** No relatório versionado (`audits/relatorio_4_2i.md:1077-1081`), constam estimativas de versões do Ubuntu com tildes (`~3.37.2`, etc.) não medidas nos jobs do CI. As únicas medições empíricas no ambiente local Windows foram Python 3.14.3 (SQLite 3.50.4) e Python 3.11.9 (SQLite 3.45.1).

---

## 6. Representatividade da Medição de Tamanho de Banco

- **Texto anterior no relatório 4.2i [retificado na 4.2k]:** Afirmava que a inclusão da coluna `content` no FTS5 expandia a base SQLite em "apenas 2% a 8%".
- **Retificação Factual Original (4.2j):**
  - A medição foi realizada em uma base de testes sintética e reduzida (aproximadamente 589 KB), na qual o tamanho dos metadados e páginas de índice fixas mascarava a proporção volumétrica.
  - Em bases reais com arquivos de código-fonte de dezenas a centenas de kilobytes, o acréscimo de `content` como coluna indexada do FTS5 duplica a presença do texto na estrutura de dados do banco (mesmo utilizando tabela externa com `content='nodes'`, o FTS5 indexa tokens de todo o corpo). Portanto, o crescimento volumétrico em repositórios com código substancial é **significativamente superior** a 8% e proporcional ao vocabulário textual total.

### Correção (4.2k)
- **Status da Citação Anterior [retificado na 4.2l]:** A frase "apenas 2% a 8%" **não existe em `audits/relatorio_4_2i.md`** (existiu apenas como estimativa informal no chat da 4.2i) [retificado na 4.2l].
- O trecho verbatim em `audits/relatorio_4_2i.md`, linha 1087 (evidência em `scratch/evidencia_4_2k/item6_grep_size_delta.txt`), é:
  ```text
  Size delta: +249,856 bytes (+42.4%)
  ```
- A ressalva técnica é mantida: o delta medido de +42.4% refere-se a uma base pequena de 250 nós (589.824 bytes antes e 839.680 bytes depois, linhas 1085-1086) e não representa o comportamento volumétrico exato de bases de produção com arquivos extensos.

### Correção (4.2l)
- **Retificação da Origem da Frase:** A frase "apenas 2% a 8%" **não foi encontrada em arquivo versionado nem no histórico pesquisado; origem não determinada** (evidência em `scratch/evidencia_4_2l/busca_frase3_2_a_8_porcento.txt`). A busca textual estrita e de variações (`"2%"`, `"8%"`) no repositório e no `transcript_full.jsonl` confirmou que a frase não existiu no relatório nem no resumo de chat da 4.2i entregue pelo dono (o qual registrava `+42.4%`). Retifica-se a afirmação de que teria existido como estimativa informal no chat da 4.2i.
- **Fato Documental Provado:** O trecho verbatim em `audits/relatorio_4_2i.md:1087` é `Size delta: +249,856 bytes (+42.4%)` para base sintética de 250 nós (linhas 1085-1086).

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
| **Item 2** (Contagem Testes) | Resumo de chat da 4.2i trazia "8 testes de paridade cross-platform" (retificada citação anterior "8 novos testes de paridade Windows/POSIX"); `audits/relatorio_4_2i.md:192` traz 1 método novo (`test_cross_platform_absolute_paths_and_unc_are_unsafe`) | `python scratch/inspect_transcripts.py; git diff 7abba97 61e79c2 -- tests/test_adaptive_gating.py` | `scratch/evidencia_4_2l/busca_frase4_8_testes_paridade.txt`, `scratch/evidencia_4_2k/item2_grep_8_testes.txt`, `scratch/evidencia_4_2k/item2_diff_test_adaptive_gating.txt`, `scratch/evidencia_4_2k/item2_collect_test_adaptive_gating.txt` |
| **Item 3** (COALESCE) | `audits/relatorio_4_2i.md` tem 0 ocorrências de `COALESCE`; resumo de chat da 4.2i citou `COALESCE(new.content, new.body)` presente em `tests/test_storage_logic.py:130, 142` e `audits/fase4-achados.md:321` | `git grep -n -i "COALESCE" audits/relatorio_4_2i.md; git grep -n "COALESCE(new.content"` | `scratch/evidencia_4_2k/item3_grep_coalesce_relatorio_4_2i.txt`, `scratch/evidencia_4_2l/item1_grep_coalesce_codebase.txt` |
| **Item 4** (Indexação 100%) | Origem não determinada (não encontrada em arquivo versionado nem no histórico pesquisado da sessão da 4.2i) | `git grep -n -i -F "100% dos nós existentes indexados retroativamente no FTS"; busca transcript_full.jsonl` | `scratch/evidencia_4_2l/busca_frase1_100_nos.txt` |
| **Item 5** (SQLite Versions) | Origem não determinada (não encontrada em arquivo versionado nem no histórico pesquisado da sessão da 4.2i); `audits/relatorio_4_2i.md:1077-1081` traz estimativas não medidas com tildes (`~3.37.2`, etc.) | `git grep -n -i -F "todas as versões de Python suportadas (3.10 a 3.14) trazem SQLite >= 3.35"; busca transcript_full.jsonl; git grep -n -i "sqlite" audits/relatorio_4_2i.md` | `scratch/evidencia_4_2l/busca_frase2_sqlite_335.txt`, `scratch/evidencia_4_2k/item5_grep_sqlite_versions.txt`, `scratch/evidencia_4_2j/item5_env_proofs.txt` |
| **Item 6** (Tamanho Banco) | Origem não determinada (não encontrada em arquivo versionado nem no histórico pesquisado da sessão da 4.2i); texto verbatim em `audits/relatorio_4_2i.md:1087` é `Size delta: +249,856 bytes (+42.4%)` para base sintética de 250 nós | `git grep -n -i -F "apenas 2% a 8%"; busca transcript_full.jsonl; git grep -n "Size delta" audits/relatorio_4_2i.md` | `scratch/evidencia_4_2l/busca_frase3_2_a_8_porcento.txt`, `scratch/evidencia_4_2k/item6_grep_size_delta.txt` |
| **Item 7** (Isolamento) | `scratch/evidencia_4_2j/item5_env_proofs.txt`: `site.USER_SITE` ativo em `AppData/Roaming` | `python -c "import site; print(site.ENABLE_USER_SITE, site.USER_SITE)"` | `scratch/evidencia_4_2j/item5_env_proofs.txt` |
| **Item 8** (`windows-stdin.yml`) | `.github/workflows/windows-stdin.yml:37`: `pip install -r requirements.txt scipy` -> `pip install -e ".[dev]" scipy` | `git diff 7abba97 61e79c2 -- .github/workflows/windows-stdin.yml` | `scratch/evidencia_4_2k/item8_diff_windows_stdin.txt`, `scratch/evidencia_4_2j/item4_f4_017_mutation.txt` |
| **Item 9** (Travamento Sandbox) | `Causa raiz identificada`: reclassificada como hipótese não demonstrada | Inspeção de `transcript_full.jsonl` para chamadas com `BypassSandbox: True` | `scratch/evidencia_4_2k/item9_bypass_commands.txt` |
| **Item 10** (Skip Qdrant) | `tests/test_conversational_db.py:132`: `@pytest.mark.skipif(not QDRANT_AVAILABLE...)` | Comparação de `qdrant_client` em `C:\Python314\python.exe` vs `_venvs_4_2i\venv_py314_clean` | `scratch/evidencia_4_2k/item_extra_qdrant_env_comparison.txt` |
| **Item 12** (Resíduo Relatório 4.2j) | `audits/relatorio_4_2j.md:65` cita "8 asserções" e "test_is_safe_path_security" (que não existe em `tests/` nem `core/`). Relatório 4.2j mantido como registro histórico; remete ao Item 2 | `git grep -n "foram 8 asserções" audits/relatorio_4_2j.md; git grep -n "test_is_safe_path_security"` | `scratch/evidencia_4_2l/item2_relatorio_4_2j_linha_65.txt`, `scratch/evidencia_4_2l/item2_grep_test_is_safe_path_security.txt`, `scratch/evidencia_4_2l/item2_grep_8_assercoes.txt` |

---

## 12. Ocorrência Residual em `audits/relatorio_4_2j.md:65` (test_is_safe_path_security e 8 Asserções)

- **Citação Verbatim da Linha 65:**
  Extraída via `git grep -n "foram 8 asserções" audits/relatorio_4_2j.md` (evidência em `scratch/evidencia_4_2l/item2_relatorio_4_2j_linha_65.txt`):
  ```text
  audits/relatorio_4_2j.md:65:2. **Contagem de Testes:** Esclarecido que foram 8 asserções num único método de teste (`test_path_outside_monorepo_is_unsafe`) e 2 em `test_is_safe_path_security`, e não 8 novos testes avulsos.
  ```
- **Preservação Histórica:** O arquivo `audits/relatorio_4_2j.md` não é modificado por constituir registro histórico imutável gerado por script ao término da Rodada 4.2j.
- **Inexistência de `test_is_safe_path_security` no Repositório:**
  O comando `git grep -n "test_is_safe_path_security"` executado em todo o repositório em HEAD (evidência em `scratch/evidencia_4_2l/item2_grep_test_is_safe_path_security.txt`) comprova que o identificador `test_is_safe_path_security` **não existe em nenhum arquivo de teste (`tests/`) nem de código (`core/`, `storage/`)**. Ele constou apenas na errata da 4.2j (linha 34 desta errata) e na linha 65 do relatório histórico da 4.2j.
- **Levantamento de Ocorrências de `8 asserções` no Repositório:**
  O comando `git grep -n "8 asserções"` (evidência em `scratch/evidencia_4_2l/item2_grep_8_assercoes.txt`) confirma que essa expressão existe apenas em `audits/errata-4-2i.md:34, 43` e em `audits/relatorio_4_2j.md:65`.
- **Remissão ao Item 2:**
  Remete-se expressamente à retificação detalhada do **Item 2** desta errata: o teste adicionado na Rodada 4.2i é exclusivamente o método [`tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_cross_platform_absolute_paths_and_unc_are_unsafe`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_adaptive_gating.py#L44-L120). O método `test_path_outside_monorepo_is_unsafe` já existia previamente e não recebeu essas asserções.
