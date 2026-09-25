# Relatório de Auditoria: `interface/telemetry_api.py` (Camada REST e Streaming SSE)

> **Data:** 24 de Setembro de 2026  
> **Status:** AUDITADO / PARADO NO GATE (Regra 7)  
> **Prioridade Geral:** 🔴 **CRÍTICA (INOPERÂNCIA FORA DA CAIXA, CRASH EM PRODUÇÃO E QUEBRA DE SEGURANÇA)**  
> **Arquivos Auditados:**
> - [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py) (596 linhas)
> - [`tests/test_telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_telemetry_api.py) (144 linhas)

---

## 1. Resumo Executivo e Contexto de Execução

O módulo [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py) implementa a camada de telemetria REST e streaming via Server-Sent Events (SSE) usando FastAPI, destinada a alimentar o dashboard web Next.js ([`grafo-dashboard-web/`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web)).

A auditoria aprofundada revelou que o módulo sofre de **inoperância fatal imediata se executado contra o banco de dados real em produção**:
1. **Suposição de Esquema Inexistente:** As consultas de snapshot e streaming pressupõem tabelas (`files` e `agent_checkpoints`) que **não existem** no banco de produção ([`data/concierge.db`](file:///c:/Nexus-Memory/GrafoConcierge/data/concierge.db)) nem no [`SchemaManager`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py). Tais tabelas só existiam nos testes porque eram criadas manualmente no `setUp()` de [`tests/test_telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_telemetry_api.py).
2. **Inoperância Fora da Caixa:** A dependência `get_db_manager()` inicia como `None` e lança `RuntimeError` em 100% dos endpoints de dados a menos que um script externo invoque `set_db_manager()` antes de subir o servidor.
3. **Mutilação do Streaming SSE:** O gerador SSE contém um limite hardcoded de teste (`max_checks = 5`) que encerra e desconecta o cliente após exatamente 5 segundos de streaming. Além disso, a presença de `datetime.now()` dinâmico no payload quebra 100% o mecanismo de cache por hash SHA-256, forçando retransmissões redundantes a cada segundo.
4. **Vulnerabilidade de CORS e Mutações Sem Autenticação:** A política CORS `allow_origins=["*"]` associada a `allow_credentials=True` e a ausência de qualquer autenticação permite que scripts executando no navegador de um usuário alterem estados mentais de agentes (`/api/mcp/state`), relaxem o modo de segurança para `auto-approve` (`/api/gating/config`), adulterem orçamentos de tokens (`/api/governor/report`) e apaguem checkpoints (`/api/checkpoints/time-travel`).

---

## 2. Tabela Consolidada de Achados

| # | Arquivo(s) | Linha(s) | Severidade | Mecanismo Resumido | Status |
|---|---|---|---|---|---|
| **#1** | [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L153) | `153–161, 181–184, 252, 550, 564` | 🔴 **CRÍTICA** | **Falha Fatal em Produção por Suposição de Esquema Inexistente (`OperationalError: no such table: files` e `agent_checkpoints`)**: `_build_telemetry_payload` executa `SELECT COUNT(*) FROM files` e consulta `agent_checkpoints`. No banco de produção (`data/concierge.db`) e no `SchemaManager`, estas tabelas **não existem** (foram forjadas exclusivamente no `setUp` dos testes). Qualquer requisição a `GET /api/telemetry/snapshot` ou `GET /api/telemetry/stream` em produção quebra imediatamente com HTTP 500. | **CONFIRMADO E REPRODUZIDO** |
| **#2** | [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L114) | `114–126, 74–89` | 🔴 **CRÍTICA** | **Inoperância Fora da Caixa por Dependência Não Configurada (`RuntimeError`)**: `_db_manager_instance` inicia como `None`. `get_db_manager()` é exigido por quase todos os endpoints. Como o módulo não possui `lifespan` handler nem resolução via variáveis de ambiente (`GRAFO_DB_PATH`), subir o app com `uvicorn interface.telemetry_api:app` resulta em falha 500 imediata em qualquer chamada. | **CONFIRMADO E REPRODUZIDO** |
| **#3** | [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L556) | `556–572` | 🟠 **GRAVE** | **Falso Stream Contínuo: SSE Aborta após 5 Segundos por Trava de Teste Codificada em Produção (`max_checks = 5`)**: O gerador assíncrono `_telemetry_event_generator` limita o loop a `max_checks = 5` ("Limit to prevent infinite loop in tests"). A conexão com o dashboard web é abruptamente encerrada a cada 5 segundos, forçando o frontend a cair em ciclo infinito de reconexões (`reconnect loop`). | **CONFIRMADO E REPRODUZIDO** |
| **#4** | [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L226) | `226, 234–237, 563–570` | 🟠 **GRAVE** | **Invalidação Perpétua do SHA-256 no SSE por Timestamp Dinâmico (`datetime.now()`)**: O gerador SSE promete emitir dados apenas quando o hash do payload mudar. Porém, `_build_telemetry_payload` gera `next_scheduled_run = datetime.now(tz=timezone.utc)` com milissegundos em cada execução. O hash SHA-256 é diferente a cada segundo mesmo em banco ocioso, anulando 100% o algoritmo de detecção de mudanças e saturando a rede. | **CONFIRMADO E REPRODUZIDO** |
| **#5** | [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L98) | `98–105, 357–369, 431–447, 325–347, 398–408` | 🟠 **GRAVE** | **Insegurança Total de CORS e Ausência Completa de Autenticação em Endpoints Mutantes**: Configuração de CORS com `allow_origins=["*"]` e `allow_credentials=True` combinada com ausência total de tokens ou API keys. Qualquer página web aberta no navegador do usuário pode disparar `POST`s para `http://localhost:8000` alterando o estado do MCP (`/api/mcp/state`), relaxando o regime de segurança para `auto-approve` (`/api/gating/config`) ou corrompendo checkpoints (`/api/checkpoints/time-travel`). | **CONFIRMADO E REPRODUZIDO** |
| **#6** | [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L166) | `166, 199, 304–319` | 🟡 **MÉDIA** | **Dessincronização de Esquema e Crash de Tipagem em Timestamps (`NoneType` e `str`)**: (1) `_build_telemetry_payload` chama `datetime.fromtimestamp(ts)`, falhando com `TypeError` se `ts` for `NULL` ou string ISO (`'2026-09-24 21:00:00'`); (2) dessincronização interna: enquanto o snapshot lê de `agent_checkpoints` com coluna `timestamp`, o endpoint `/api/checkpoints/{session_id}` lê de `fsm_checkpoints` com colunas `state_name, task_id, created_at`. | **CONFIRMADO E REPRODUZIDO** |
| **#7** | [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L56) | `56–68` | 🟡 **MÉDIA** | **Thread Daemônica Órfã e Singletons Desconectados no Import do Módulo**: A mera importação de `interface.telemetry_api` (feita por `interface/mcp_server.py:151`) invoca `rate_governor_service.start()`, subindo uma thread consumidora que roda em loop contínuo consumindo CPU sem receber requisições de produção. Singletons de `SecurityGuard` e `GatingInterceptor` também são instanciados sem governar as ferramentas reais do FastMCP. | **CONFIRMADO** |

---

## 3. Detalhamento Técnico dos Achados e Mecanismos de Falha

### Achado #1: Falha Fatal em Produção por Suposição de Esquema Inexistente (`OperationalError: no such table: files` e `agent_checkpoints`)
- **Severidade:** 🔴 **CRÍTICA**
- **Arquivo:** [`interface/telemetry_api.py:153–161, 181–184, 252, 550, 564`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L153)
- **Mecanismo:**
  A função `_build_telemetry_payload(db_manager)` consolida as métricas do sistema realizando três queries SQL:
  ```python
  total_files_rows = db_manager.read_query("SELECT COUNT(*) FROM files;")
  dirty_rows = db_manager.read_query("SELECT path, community_id, last_modified FROM files WHERE is_dirty = 1;")
  checkpoint_rows = db_manager.read_query("SELECT agent_id, session_id, checkpoint_id, timestamp FROM agent_checkpoints ORDER BY timestamp ASC;")
  ```
  Entretanto, uma inspeção direta no banco real de produção ([`data/concierge.db`](file:///c:/Nexus-Memory/GrafoConcierge/data/concierge.db)) e no [`SchemaManager`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py) comprova que o banco possui apenas as tabelas:
  `['projects', 'nodes', 'edges', 'reference_wings', 'trajectories', 'commit_log', 'user_core_memory', 'semantic_facts', 'test_log']`.
  **As tabelas `files` e `agent_checkpoints` não existem e nunca são criadas em produção**.
  Elas só existiam nos testes unitários porque `tests/test_telemetry_api.py:38-47` executa DDLs ad-hoc no `setUp()`.
- **Impacto:**
  Ao apontar a API para o banco real, chamar `GET /api/telemetry/snapshot` ou abrir o stream SSE resulta imediatamente em:
  `sqlite3.OperationalError: no such table: files` e retorno de HTTP 500.

---

### Achado #2: Inoperância Fora da Caixa por Dependência Não Configurada (`RuntimeError`)
- **Severidade:** 🔴 **CRÍTICA**
- **Arquivo:** [`interface/telemetry_api.py:114–126, 74–89`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L114)
- **Mecanismo:**
  O módulo utiliza injeção de dependência via FastAPI:
  ```python
  _db_manager_instance = None

  def get_db_manager() -> ConciergeDatabaseManager:
      if _db_manager_instance is None:
          raise RuntimeError(
              "ConciergeDatabaseManager not configured. "
              "Call set_db_manager() before starting the server."
          )
      return _db_manager_instance
  ```
  Quase todos os endpoints (`snapshot`, `stream`, `reconcile`, `checkpoints`, `time-travel`, e todos os endpoints de `hsm`) declaram `Depends(get_db_manager)`.
  Não existe no módulo nenhum `lifespan` handler, nenhum fallback para inicializar com `data/concierge.db`, nem variáveis de ambiente padrão.
- **Impacto:**
  Se um operador subir o serviço via `uvicorn interface.telemetry_api:app`, o servidor sobe mas **100% das rotas de dados quebram com HTTP 500** (`RuntimeError: ConciergeDatabaseManager not configured`).

---

### Achado #3: Falso Stream Contínuo: SSE Aborta após 5 Segundos por Trava de Teste Codificada em Produção (`max_checks = 5`)
- **Severidade:** 🟠 **GRAVE**
- **Arquivo:** [`interface/telemetry_api.py:556–572`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L556)
- **Mecanismo:**
  O endpoint `GET /api/telemetry/stream` utiliza o gerador `_telemetry_event_generator`:
  ```python
  # Continuous monitoring loop
  check_count = 0
  max_checks = 5  # Limit to prevent infinite loop in tests

  while check_count < max_checks:
      await asyncio.sleep(1.0)
      check_count += 1
      ...
  ```
  Uma trava provisória criada para testes de unidade (`max_checks = 5`) foi incorporada diretamente na lógica de produção.
- **Impacto:**
  O streaming SSE encerra forçadamente a transmissão após 5 iterações (~5 segundos). Clientes como o hook `useTelemetryStream.ts` do Next.js sofrem desconexão permanente e entram em reconnect loop agressivo, gerando tempestade de requisições de reconexão a cada 5 segundos.

---

### Achado #4: Invalidação Perpétua do SHA-256 no SSE por Timestamp Dinâmico (`datetime.now()`)
- **Severidade:** 🟠 **GRAVE**
- **Arquivo:** [`interface/telemetry_api.py:226, 234–237, 563–570`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L226)
- **Mecanismo:**
  O gerador SSE implementa verificação de hash para retransmitir dados apenas em caso de mutação:
  `if current_hash != last_hash: yield ...`
  Contudo, dentro de `_build_telemetry_payload`:
  ```python
  janitor_status=JanitorStatusSchema(
      is_running=False,
      last_run=None,
      next_scheduled_run=datetime.now(tz=timezone.utc),
  )
  ```
  O campo `next_scheduled_run` é recalculado dinamicamente com o timestamp atual a cada chamada.
- **Impacto:**
  O SHA-256 do payload **nunca se repete** (`h1 != h2`), mesmo em bancos totalmente ociosos. O servidor dispara o payload JSON completo para todos os clientes conectados a cada 1 segundo, anulando o propósito de economia de banda do design.

---

### Achado #5: Insegurança Total de CORS e Ausência Completa de Autenticação em Endpoints Mutantes
- **Severidade:** 🟠 **GRAVE**
- **Arquivo:** [`interface/telemetry_api.py:98–105, 357–369, 431–447, 325–347, 398–408`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L98)
- **Mecanismo:**
  O middleware CORS foi configurado com permissividade máxima:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  Ao mesmo tempo, **nenhum** endpoint REST exige autenticação (API Key, Bearer Token ou validação de Origin).
- **Impacto:**
  Qualquer site acessado no navegador do desenvolvedor pode executar requisições AJAX maliciosas contra `http://localhost:8000`:
  - `POST /api/mcp/state`: altera o estado da sessão de agentes para `MAINTENANCE` ou `EXECUTION`, viabilizando o bypass do governor demonstrado em `bypass-governanca-por-session-id`.
  - `POST /api/gating/config`: altera o regime do monorepo para `auto-approve`.
  - `POST /api/checkpoints/time-travel`: reverte checkpoints e apaga histórico de agentes.
  - `POST /api/governor/report`: injeta consumo de tokens forjado para provocar o congelamento imediato de filas.

---

### Achado #6: Dessincronização de Esquema e Crash de Tipagem em Timestamps (`NoneType` e `str`)
- **Severidade:** 🟡 **MÉDIA**
- **Arquivo:** [`interface/telemetry_api.py:166, 199, 304–319`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L166)
- **Mecanismo:**
  1. `_build_telemetry_payload` executa `datetime.fromtimestamp(ts, tz=timezone.utc)` assumindo que `ts` é sempre um float numérico.
  2. Se uma linha possuir `timestamp` como `NULL`, o código quebra com `TypeError: argument must be int or float, not NoneType`.
  3. Se o banco armazenar timestamps no formato padrão de texto ISO 8601 do SQLite (`CURRENT_TIMESTAMP`), `fromtimestamp` quebra com `TypeError: argument must be int or float, not str`.
  4. Há contradição interna de tabelas: `_build_telemetry_payload` lê de `agent_checkpoints (timestamp)`, enquanto `list_session_checkpoints` lê de `fsm_checkpoints (created_at)`.

---

### Achado #7: Thread Daemônica Órfã e Singletons Desconectados no Import do Módulo
- **Severidade:** 🟡 **MÉDIA**
- **Arquivo:** [`interface/telemetry_api.py:56–68`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L56)
- **Mecanismo:**
  Na inicialização de nível de módulo:
  ```python
  rate_governor_service = RateGovernor(rpm_limit=60, tpm_limit=40000)
  rate_governor_service.start()
  ```
  Quando `interface/mcp_server.py:151` faz `from interface.telemetry_api import mcp_governor`, essa linha é avaliada e a thread do daemon do `RateGovernor` inicia em segundo plano.
- **Impacto:**
  Uma thread adicional fica consumindo ciclos de CPU e recursos do sistema indefinidamente, mesmo que o `RateGovernor` não seja utilizado pelas ferramentas do servidor MCP em produção.

---

## 4. Saída Bruta da Reprodução Empírica

Execução do script de verificação [`scratch/reproduce_telemetry_findings.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_telemetry_findings.py):

```text
======================================================================
TESTE 1: Falha Fatal em Produção por Suposição de Tabelas Inexistentes
======================================================================
Status retornado por GET /api/telemetry/snapshot em produção: 500
Corpo do erro: Internal Server Error
-> [CONFIRMADO] API crashou com HTTP 500 em produção: True

======================================================================
TESTE 2: Inoperância Fora da Caixa (RuntimeError: db_manager not configured)
======================================================================
Status retornado sem set_db_manager(): 500
Resposta: Internal Server Error
-> [CONFIRMADO] API inacessível sem injeção manual externa: True

======================================================================
TESTE 3: Stream SSE Aborta após 5 Segundos (max_checks = 5)
======================================================================
Duração total do stream SSE: 5.19s
Total de eventos emitidos antes do encerramento forçado da conexão: 6
-> [CONFIRMADO] Conexão persistente SSE morre prematuramente em ~5s: True

======================================================================
TESTE 4: Invalidação Perpétua do SHA-256 por datetime.now() Dinâmico
======================================================================
Hash 1 (t=0.00s): 629ca8bb5c64d82a48526947fe2c8beeaa21e8e2771352ad8beaa4c99a8af0b4
Hash 2 (t=0.05s): 7d1f2aafa6c3081f16a6f7dd49589f09cb3b28f328c0b85110db74a1faaf212e
p1['janitor_status']['next_scheduled_run']: 2026-09-25T00:23:41.619430Z
p2['janitor_status']['next_scheduled_run']: 2026-09-25T00:23:41.686955Z
Hashes são idênticos em banco ocioso? False
-> [CONFIRMADO] Detecção de mudanças 100% inoperante (re-emissão perpétua): True

======================================================================
TESTE 5: CORS Permissivo e Mutações de Estado Sem Autenticação
======================================================================
CORS allow-origin retornado para site arbitrário: http://evil-attacker-site.com
CORS allow-credentials: true
Mutações de estado de sessão sem token/auth: status=200, state=MAINTENANCE
Alteração de regime monorepo para auto-approve sem auth: status=200, mode=auto-approve
Injeção de consumo de tokens no governor: status=200, new_tpm=999999
-> [CONFIRMADO] Controle total da governança acessível a terceiros sem credenciais: True

======================================================================
TESTE 6: Crash em Timestamps (NoneType e ISO String)
======================================================================
6.1 Crash com timestamp=None: argument must be int or float, not NoneType
6.2 Crash com timestamp ISO string: argument must be int or float, not str
-> [CONFIRMADO] Fragilidade fatal de tipagem em datas SQLite: True

======================================================================
RESUMO DE REPRODUÇÃO (interface/telemetry_api.py):
Achado 1 (Tabelas Inexistentes / Crash 500 em Produção): REPRODUZIDO
Achado 2 (Inoperância Out-of-the-Box / db_manager None): REPRODUZIDO
Achado 3 (Stream SSE Morre após 5s / max_checks=5): REPRODUZIDO
Achado 4 (Invalidação Perpétua de Hash por datetime.now): REPRODUZIDO
Achado 5 (CORS Permissivo e Mutações Desprotegidas): REPRODUZIDO
Achado 6 (Crash de Tipagem em Timestamps None e String): REPRODUZIDO
======================================================================
```

---

## 5. Recomendações Estruturais para a Fase 3 (Backlog Consolidado)

1. **Alinhamento Obrigatório com o Esquema Real do Grafo Concierge:**
   - Remover as dependências das tabelas fantasmas `files` e `agent_checkpoints`. A telemetria de nós indexados deve consultar `nodes` (`SELECT COUNT(*) FROM nodes`) e projetos (`projects`), ou essas tabelas devem ser formalmente incorporadas e migradas no [`SchemaManager`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py).
2. **Ciclo de Vida (Lifespan) e Bootstrap Automático:**
   - Adicionar manipulador `lifespan` ao FastAPI para ler `GRAFO_DB_PATH` do ambiente e instanciar `ConciergeDatabaseManager` automaticamente se não for injetado externamente, evitando `RuntimeError` na inicialização independente.
3. **Remoção de Travas de Teste em Código de Produção:**
   - Eliminar `max_checks = 5` em `_telemetry_event_generator`. Em ambiente de produção o loop deve ser contínuo (`while True:` com tratamento de desconexão do cliente via `request.is_disconnected()`). O limite para testes deve ser injetado via parâmetro ou fixture.
4. **Cálculo Determinístico de Hash no SSE:**
   - Excluir campos dinâmicos de tempo volátil (como `next_scheduled_run` instanciado a cada segundo) do cálculo do SHA-256, ou usar um contador de versão/sequência no SQLite (`PRAGMA data_version`) para detectar mutações reais no banco sem serializar payloads repetidamente.
5. **Endurecimento de Segurança e CORS:**
   - Restringir CORS estritamente à URL do frontend configurada via variável de ambiente (ex.: `http://localhost:3000`).
   - Implementar autenticação via API Key compartilhada ou Bearer Token em todos os endpoints mutantes (`/api/mcp/state`, `/api/gating/config`, `/api/checkpoints/time-travel`, etc.).
6. **Robustez na Deserialização de Timestamps:**
   - Criar parser tolerante a múltiplos formatos de data (`float`, `int`, string ISO 8601 ou fallback para `datetime.now(tz=timezone.utc)` se `None`).
7. **Lazy Initialization de Daemons e Background Workers:**
   - Iniciar o `RateGovernor` apenas quando o servidor web for de fato inicializado via evento de inicialização do lifespan, nunca na importação do módulo.
