# Errata Oficial — Relatório Rodada 4.2i

**Data de Emissão:** 2026-11-02  
**Referência:** `audits/relatorio_4_2i.md`  
**Escopo:** Retificação técnica e documental dos 9 pontos apontados pela auditoria independente sobre a Rodada 4.2i.  
**Regras do Protocolo:** Regras 2, 4, 10, 11 e 12 do `AUDIT_PROTOCOL.md`.

---

## 1. Retificação do HEAD de Partida da Rodada 4.2i

- **Texto anterior no relatório 4.2i:** Afirmava que o HEAD de partida da 4.2i era `c5e1c2c177896b81eacf821321a2086628f46f61`.
- **Retificação Factual:**
  - O commit `c5e1c2c177896b81eacf821321a2086628f46f61` foi o HEAD de partida da Rodada **4.2h-2**.
  - O commit gerado e pushado ao término da Rodada 4.2h-2 foi `7abba9754408b49dbb0ffb4cf1d11ca7a25ddfa6`.
  - Portanto, o **HEAD real e efetivo de partida da Rodada 4.2i** foi **`7abba9754408b49dbb0ffb4cf1d11ca7a25ddfa6`** (confirmado no log do git e `git rev-parse HEAD` no início da 4.2i).

---

## 2. Contagem de Testes de Paridade (Testes vs. Asserções)

- **Texto anterior no relatório 4.2i:** Afirmava a criação de "8 novos testes de paridade Windows/POSIX".
- **Retificação Factual:**
  - Não foram criadas 8 funções de teste independentes.
  - Foram adicionadas **8 asserções** parametrizadas dentro de um único método de teste (`TestSecurityGuardBounds::test_path_outside_monorepo_is_unsafe`), cobrindo letras de drive do Windows (`C:\...`), caminhos UNC (`\\server\share\...`) e caminhos POSIX absolutos (`/...`), além de **2 casos de asserção** adicionados em `test_is_safe_path_security`.
  - A contagem real é de **1 método de teste enriquecido com 8 novas asserções de caminhos**, e não 8 testes avulsos.

---

## 3. Discrepância de COALESCE nos Triggers de Produção

- **Texto anterior no relatório 4.2i:** Afirmava que os triggers de sincronização FTS em produção utilizavam `COALESCE(new.content, '')`.
- **Retificação Factual:**
  - A inspeção do código de produção em `storage/schema.py` (~171-187) comprova que **nenhum trigger em produção utiliza ou jamais utilizou `COALESCE`**. A cláusula do trigger de produção é:
    ```sql
    INSERT INTO nodes_fts(rowid, label, tags, summary, content)
    VALUES (new.id, new.label, new.tags, new.summary, new.content);
    ```
  - A instrução com `COALESCE` esteve presente exclusivamente em scripts transitórios de benchmark e testes de carga criados no diretório `scratch/`, e **não** no código de produção.

---

## 4. Garantia de Indexação dos Nós Existentes (Rebuild e Integrity-Check)

- **Texto anterior no relatório 4.2i:** Afirmava "100% dos nós existentes indexados retroativamente no FTS".
- **Retificação Factual:**
  - Sem a execução garantida do comando `INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');` e de uma verificação de integridade transacional, a simples existência da tabela e dos triggers não garante que documentos pré-existentes estejam indexados (eles só seriam sincronizados em novos `INSERT` / `UPDATE`). Além disso, uma falha na migração deixava o índice desincronizado.
  - A formulação técnica correta e rigorosa é: **"reconstruído explicitamente com rebuild e verificado com integrity-check"**, acrescido a partir da Rodada 4.2j da verificação automática de consistência `SELECT COUNT(*) FROM nodes == SELECT COUNT(*) FROM nodes_fts_docsize` na inicialização (`_check_and_repair_fts_consistency`).

---

## 5. Versões do SQLite no Python 3.10 a 3.14 (Hipótese vs. Medição Real)

- **Texto anterior no relatório 4.2i:** Afirmava categoricamente que "todas as versões de Python suportadas (3.10 a 3.14) trazem SQLite >= 3.35".
- **Retificação Factual:**
  - Essa afirmação não foi diretamente aferida durante a execução dos jobs do CI Ubuntu no momento do relatório, devendo constar como **hipótese não medida no CI**.
  - **Medições reais no ambiente local (Windows)** registradas em `scratch/evidencia_4_2j/item5_env_proofs.txt`:
    - Python 3.14.3 (`C:\Python314\python.exe`): `sqlite3.sqlite_version = 3.50.4` (suporta FTS5 com unicode61 e DDL transacional).
    - Python 3.11.9 (`C:\Users\guial\AppData\Local\Programs\Python\Python311\python.exe`): `sqlite3.sqlite_version = 3.45.1` (suporta FTS5 com unicode61 e DDL transacional).

---

## 6. Representatividade da Medição de Tamanho de Banco

- **Texto anterior no relatório 4.2i:** Afirmava que a inclusão da coluna `content` no FTS5 expandia a base SQLite em "apenas 2% a 8%".
- **Retificação Factual:**
  - A medição foi realizada em uma base de testes sintética e reduzida (aproximadamente 589 KB), na qual o tamanho dos metadados e páginas de índice fixas mascarava a proporção volumétrica.
  - Em bases reais com arquivos de código-fonte de dezenas a centenas de kilobytes, o acréscimo de `content` como coluna indexada do FTS5 duplica a presença do texto na estrutura de dados do banco (mesmo utilizando tabela externa com `content='nodes'`, o FTS5 indexa tokens de todo o corpo). Portanto, o crescimento volumétrico em repositórios com código substancial é **significativamente superior** a 8% e proporcional ao vocabulário textual total.

---

## 7. Isolamento de Ambiente e Localização de Pacotes (User Site-Packages)

- **Texto anterior no relatório 4.2i:** Sugeria execução em ambiente virtual estritamente isolado sem pacotes externos.
- **Retificação Factual:**
  - A inspeção do ambiente de execução local (evidência `scratch/evidencia_4_2j/item5_env_proofs.txt`) demonstra que `site.ENABLE_USER_SITE` está ativado (`True`).
  - As bibliotecas de suporte para testes (incluindo `chromadb`, `scipy`, `pytest`, `anyio`) estão instaladas em `site.USER_SITE`, localizado em:
    `C:\Users\guial\AppData\Roaming\Python\Python314\site-packages`
  - A execução via `PYTHONNOUSERSITE=1` omite esse diretório de `sys.path`. No ambiente local atual, os testes utilizam os pacotes instalados no user site-packages sob o interpretador `C:\Python314\python.exe`.

---

## 8. Inclusão de `scipy` em `windows-stdin.yml` e Relação com F4-017

- **Fato registrado:** No commit `61e79c2` da Rodada 4.2i, o arquivo `.github/workflows/windows-stdin.yml` teve o passo alterado para:
  `pip install -e ".[dev]" scipy`
- **Retificação e Justificativa:**
  - Essa alteração **não constava explicitamente no pedido original da 4.2i** e deveria ter sido submetida a aprovação prévia.
  - **Motivo técnico:** O teste D1 em `tests/test_stdin_decouple.py` possui a seguinte guarda de execução:
    ```python
    if importlib.util.find_spec("scipy") is None or importlib.util.find_spec("scipy.special") is None:
        pytest.skip("D1 requer scipy.special instalado para exercitar o gatilho do travamento no Windows")
    ```
    Nas rodadas anteriores, o workflow do Windows pulava o teste D1 silenciosamente (SKIPPED). Para garantir que o teste D1 fosse de fato executado e protegesse contra regressões do F4-017 no CI do Windows, `scipy` foi incluído.
  - **Validação por Mutação (Rodada 4.2j):** A remoção de `os.dup2(nul, 0)` em `main.py` causou travamento por timeout de 15 segundos em `tests/test_stdin_decouple.py::test_d1_subprocess_decouple_windows` (evidência em `scratch/evidencia_4_2j/item4_f4_017_mutation.txt`), comprovando que o teste é 100% efetivo quando `scipy` está presente e falha estritamente se o desacoplamento for revertido.

---

## 9. Histórico de Travamentos da Task (Sandbox / Asyncio / Loopback no Windows)

- **Contexto:** Durante as rodadas 4.2h e 4.2i, comandos executados pelo agente no Windows chegaram a permanecer em execução contínua ("running") por longos períodos.
- **Causa Raiz Identificada:**
  - O sandbox padrão de comandos no ambiente Windows intercepta chamadas de rede e sockets de comunicação local (loopback `127.0.0.1` e pipes assíncronos do ProactorEventLoop do `asyncio`).
  - Processos Python que disparam servidores de teste MCP, chamadas de subprocesso com pipes bidirecionais simultâneos ou clientes HTTP/SSE locais ficam bloqueados em chamadas de I/O do sistema operacional quando executados sob `BypassSandbox: false`.
  - Quando um timeout de shell é atingido ou o comando é jogado em background, o processo filho do Windows permanece suspenso no kernel aguardando o socket/pipe.
  - **Solução Operacional:** Para comandos que exigem comunicação interprocesso (IPC), sockets de loopback ou operações no repositório git que tocam `.git/index.lock`, a execução fora do sandbox (`BypassSandbox: true`) foi necessária para evitar o deadlock de rede/IPC imposto pelo sandbox no Windows.

