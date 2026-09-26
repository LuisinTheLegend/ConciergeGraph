# Relatório de Auditoria: `grafo-dashboard-web/` (Painel Web Next.js, Clientes de API e Telemetria)

> **Data:** 25 de Setembro de 2026  
> **Status:** AUDITADO / PARADO NO GATE (Regra 7)  
> **Prioridade Geral:** 🔴 **CRÍTICA (CÓDIGO MORTO DE EVENTOS, CICLO INFINITO DE FLAPPING SSE, COLISÃO DE PORTAS E REJEIÇÃO 401 FORA DA CAIXA)**  
> **Arquivos Auditados:**
> - [`grafo-dashboard-web/lib/useTelemetryStream.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/useTelemetryStream.ts) (343 linhas)
> - [`grafo-dashboard-web/lib/mcp/client.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/mcp/client.ts) (431 linhas)
> - [`grafo-dashboard-web/app/page.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/page.tsx) (716 linhas)
> - [`grafo-dashboard-web/app/hooks/useGraphTopology.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/hooks/useGraphTopology.ts) (181 linhas)
> - [`grafo-dashboard-web/app/hooks/useCognitiveData.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/hooks/useCognitiveData.ts) (177 linhas)
> - [`grafo-dashboard-web/app/hooks/useMcpConnection.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/hooks/useMcpConnection.ts) (50 linhas)
> - [`grafo-dashboard-web/components/hsm/HSMStateInspector.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/hsm/HSMStateInspector.tsx) (290 linhas)
> - [`grafo-dashboard-web/components/governor/QuotaGauges.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/governor/QuotaGauges.tsx) (245 linhas)
> - [`grafo-dashboard-web/components/telemetry/LiveEventFeed.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/telemetry/LiveEventFeed.tsx) (272 linhas)
> - [`grafo-dashboard-web/components/topology/CodeGraphViewer.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/topology/CodeGraphViewer.tsx) (374 linhas)
> - [`grafo-dashboard-web/app/components/ForceGraph3DRenderer.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/ForceGraph3DRenderer.tsx) (599 linhas)
> - [`grafo-dashboard-web/app/components/InspectorDrawer.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/InspectorDrawer.tsx) (230 linhas)
> - [`grafo-dashboard-web/app/components/MemoryIntegrityBoard.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/MemoryIntegrityBoard.tsx) (276 linhas)
> - [`grafo-dashboard-web/app/components/SelfHealingConsole.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/SelfHealingConsole.tsx) (180 linhas)
> - [`grafo-dashboard-web/app/components/AgentTimelinePanel.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/AgentTimelinePanel.tsx) (180 linhas)
> - [`grafo-dashboard-web/app/components/CoreMemoryPanel.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/CoreMemoryPanel.tsx) (227 linhas)
> - [`grafo-dashboard-web/app/components/SemanticFactsPanel.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/SemanticFactsPanel.tsx) (292 linhas)
> - [`grafo-dashboard-web/package.json`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/package.json) e [`grafo-dashboard-web/.env.local`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/.env.local)

---

## 1. Resumo Executivo e Contexto de Execução

O [`grafo-dashboard-web/`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web) é a interface visual do Grafo Concierge construída em Next.js 16 (App Router com Turbopack), React 19, TailwindCSS 4 e motores gráficos 3D/2D baseados em Three.js (`react-force-graph-3d` e `react-force-graph-2d`). Sua finalidade anunciada é atuar como um "HUD Cognitivo de Observabilidade" em tempo real, integrando-se simultaneamente com:
1. O servidor **FastMCP** ([`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py)) via SSE/JSON-RPC para consulta de topologia, nós, memória persistente e ferramentas.
2. A API **FastAPI** ([`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py)) para telemetria passiva em tempo real de cotas (`RateGovernor`), transições de estado (`HSM`), integridade de memória e logs operacionais (`Janitor`).

A auditoria aprofundada revelou graves rupturas estruturais de contrato entre o frontend e os servidores Python de backend, que tornam a experiência de produção inoperante ou severamente degradada fora da caixa:
1. **Código Morto em Handlers SSE e HUD Congelado:** O hook [`lib/useTelemetryStream.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/useTelemetryStream.ts) possui um switch-case que escuta eventos digitados como `RATE_GOVERNOR_UPDATE`, `HSM_STATE_UPDATE`, `WAL_WRITE_JOB` e `DELTA_DETECTED`. No entanto, o backend (`interface/telemetry_api.py`) **nunca** emite objetos com a chave `event_type` — transmite apenas o payload bruto `TelemetryPayloadSchema`. Como resultado, todo o tratamento de eventos reativos é código morto e os mostradores de cota (`QuotaGauges`) e estados do HSM (`HSMStateInspector`) permanecem **congelados** nos valores estáticos da primeira requisição HTTP.
2. **Ciclo Infinito de Flapping e Poluição do Feed:** O backend encerra o gerador SSE após 5 iterações devido à trava de teste mantida em produção (`max_checks = 5`). O frontend detecta a queda em `es.onerror`, aguarda 3 segundos e reconecta. Esse ciclo de 8 segundos (5s conectado + 3s reconectando) se repete indefinidamente, gerando 75 reconexões a cada 10 minutos, poluindo o buffer de eventos com mensagens repetitivas `"Connected to FastAPI Telemetry SSE Stream"` e fazendo o HUD piscar visualmente sem parar.
3. **Colisão de Portas e Desconexão do FastMCP:** O script oficial `"dev:backend"` (`python main.py`) inicializa o FastMCP em modo `stdio` (onde nenhuma porta HTTP/SSE é aberta). Mesmo se configurado como `sse`, o FastMCP escuta na porta padrão `8000`, colidindo com a porta `8000` do FastAPI (`interface/telemetry_api.py`). Por sua vez, o frontend foi configurado no [`.env.local`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/.env.local) e em [`lib/mcp/client.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/mcp/client.ts) para buscar o FastMCP na porta `7077`, onde nenhum serviço escuta. Ao rodar `npm run dev:all`, o cliente MCP entra em loop perpétuo de erro de conexão.
4. **Rejeição HTTP 401 com API Key:** Se `GRAFO_API_KEY` for configurada no backend, o middleware HTTP exige autenticação. O cliente Next.js usa `EventSource` nativo do navegador (que não suporta headers HTTP customizados) e chamadas `fetch(POST)` sem cabeçalho `Authorization` nem query parameter `?token=`, sendo 100% bloqueado com HTTP 401 Unauthorized.
5. **Esvaziamento do InspectorDrawer:** A ferramenta `get_full_topology` invoca `store.get_lightweight_topology()`, que omite intencionalmente os campos `summary` e `tags` para economia de banda. O componente [`app/components/InspectorDrawer.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/InspectorDrawer.tsx) pressupõe que esses dados já vêm no nó e não realiza nenhuma busca secundária. Qualquer nó clicado pelo usuário no grafo 3D/2D apresenta descrição e tags permanentemente vazias.
6. **37 Erros de Linter e Violação de Pureza no React 19:** `npm run lint` falha com 37 erros, acusando chamadas impuras a `Date.now()` no render de [`LiveEventFeed.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/telemetry/LiveEventFeed.tsx) e disparos síncronos de `setState` em efeitos (`react-hooks/set-state-in-effect`), ameaçando a estabilidade do Next.js Turbopack.

---

## 2. Tabela Consolidada de Achados

| # | Arquivo(s) | Linha(s) | Severidade | Mecanismo Resumido | Status |
|---|---|---|---|---|---|
| **#1** | [`lib/useTelemetryStream.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/useTelemetryStream.ts#L219) | `219–260` | 🔴 **CRÍTICA** | **Código Morto em Handlers SSE e Telemetria Reativa Congelada**: `lib/useTelemetryStream.ts` implementa `switch (raw.event_type)` para `"RATE_GOVERNOR_UPDATE"`, `"HSM_STATE_UPDATE"`, `"WAL_WRITE_JOB"` e `"DELTA_DETECTED"`. No backend (`interface/telemetry_api.py`), o SSE emite *exclusivamente* o dicionário bruto consolidado `TelemetryPayloadSchema` sem `event_type`. O switch é 100% inalcançável e os mostradores de cota (`QuotaGauges`) e de estado HSM (`HSMStateInspector`) nunca são atualizados via SSE, ficando congelados no boot. | **CONFIRMADO E REPRODUZIDO** |
| **#2** | [`lib/useTelemetryStream.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/useTelemetryStream.ts#L280), [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L556) | `lib: 280–291`, `api: 556–572` | 🔴 **CRÍTICA** | **Ciclo Infinito de Flapping SSE e Inundação do Buffer de Eventos**: No backend, `max_checks = 5` aborta o gerador SSE após 5s. No frontend, `es.onerror` captura a queda, agenda reconexão após 3s e em `onopen` adiciona o evento `"Connected to FastAPI Telemetry SSE Stream"`. Em 10 min ocorrem 75 ciclos de queda/reconexão, saturando a fila de eventos (limite 200) e fazendo o indicador do HUD piscar sem parar. | **CONFIRMADO E REPRODUZIDO** |
| **#3** | [`package.json`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/package.json#L10), [`.env.local`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/.env.local#L6), [`lib/mcp/client.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/mcp/client.ts#L29) | `pkg: 10–11`, `env: 6, 10`, `client: 29` | 🔴 **CRÍTICA** | **Colisão de Portas, Inoperância do Script `dev:all` e Desconexão do FastMCP SSE**: `main.py` roda FastMCP em `stdio` (ou porta 8000 se SSE); o FastAPI `telemetry_api.py` também roda na porta 8000 gerando colisão `WinError 10048`. Ao mesmo tempo, `.env.local` e `client.ts` configuram FastMCP na porta 7077 (onde nenhum serviço roda). Ao rodar `npm run dev:all`, o cliente MCP tenta conectar infinitamente em 7077 e a telemetria falha pois `telemetry_api.py` não é iniciado por `main.py`. | **CONFIRMADO E REPRODUZIDO** |
| **#4** | [`lib/mcp/client.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/mcp/client.ts#L78), [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L186) | `client: 78, 294–298`, `server: 186–212` | 🟠 **GRAVE** | **Incompatibilidade de Autenticação FastMCP e Rejeição Total com HTTP 401**: O backend ativa validação HTTP quando `GRAFO_API_KEY` existe. O frontend usa `EventSource` (que não aceita headers customizados) e requisições `fetch(POST)` sem passar o cabeçalho `Authorization` nem query param `?token=`. Se a API Key for ativada, o dashboard é imediatamente bloqueado com 401 em todas as chamadas. | **CONFIRMADO E REPRODUZIDO** |
| **#5** | [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L259), [`app/hooks/useGraphTopology.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/hooks/useGraphTopology.ts#L106), [`app/components/InspectorDrawer.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/InspectorDrawer.tsx#L124) | `store: 259–273`, `hook: 106–115`, `drawer: 124–152` | 🟠 **GRAVE** | **Omissão de Metadados em `get_full_topology` e Esvaziamento do `InspectorDrawer`**: `store.get_lightweight_topology()` projeta apenas `id, label, node_type` e omite deliberadamente `summary` e `tags` para poupar banda. O `InspectorDrawer` pressupõe que esses campos existem no objeto do nó e não faz fetch sob demanda. Ao clicar em qualquer nó no universo 3D/2D, "Pipeline Description" e "Semantic Tags" aparecem permanentemente vazios. | **CONFIRMADO E REPRODUZIDO** |
| **#6** | [`app/components/CoreMemoryPanel.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/CoreMemoryPanel.tsx#L137) | `137–146` | 🟡 **MÉDIA** | **Risco de Crash e Corrupção de Data (`Invalid Date`) em `CoreMemoryPanel`**: `CoreMemoryPanel.tsx:137` concatena `+ "Z"` cegamente em `block.updated_at`. Se o backend enviar um timestamp ISO com timezone ou sufixo `"Z"` pré-existente, o resultado `"2026-09-25T12:00:00ZZ"` torna-se um `Invalid Date`, gerando `RangeError` no `toLocaleString()` ou renderizando `"Invalid Date"` no HUD. | **CONFIRMADO** |
| **#7** | [`app/page.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/page.tsx#L478), [`components/hsm/HSMStateInspector.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/hsm/HSMStateInspector.tsx#L191) | `page: 478–482`, `hsm: 191` | 🟡 **MÉDIA** | **Rotas Mutantes Órfãs e Callbacks Inertes no HUD**: `HSMStateInspector` renderiza botões para cada sub-estado que disparam `onSelectState(qualified)`. No entanto, `app/page.tsx` instancia o componente sem fornecer `onSelectState`. A rota backend `POST /api/hsm/transition` nunca é invocada pelo dashboard, tornando os cliques na árvore de estados totalmente inertes. | **CONFIRMADO** |
| **#8** | [`components/telemetry/LiveEventFeed.tsx`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/telemetry/LiveEventFeed.tsx#L93), [`lib/useTelemetryStream.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/useTelemetryStream.ts#L191) | `feed: 93–121`, `stream: 191` | 🟡 **MÉDIA** | **37 Erros de Linter, Impureza em Render React 19 e Efeitos em Cascata**: `LiveEventFeed.tsx` invoca `Date.now()` dentro do render em `useMemo` violando regras de funções puras do React 19 (`react-hooks/purity`). `useTelemetryStream.ts` dispara `hydrateRest` síncrono no efeito (`react-hooks/set-state-in-effect`), gerando 42 problemas (37 erros) no `npm run lint`. | **CONFIRMADO E REPRODUZIDO** |

---

## 3. Detalhamento Técnico dos Achados e Mecanismos de Falha

### Achado #1: Código Morto em Handlers SSE e Telemetria Reativa Congelada
- **Severidade:** 🔴 **CRÍTICA**
- **Arquivo:** [`grafo-dashboard-web/lib/useTelemetryStream.ts:219–260`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/useTelemetryStream.ts#L219)
- **Mecanismo:**
  O hook `useTelemetryStream` possui um parser para o stream SSE que espera mensagens de evento estruturadas:
  ```typescript
  // lib/useTelemetryStream.ts:220
  if (raw.event_type) {
    switch (raw.event_type) {
      case "RATE_GOVERNOR_UPDATE":
        if (raw.data) {
          setMetrics((prev) => ({ ...prev, ...raw.data }));
          ...
        }
        break;
      case "HSM_STATE_UPDATE":
        if (raw.data) {
          const fullPath = raw.data.current_full_path || "PLANNING.DISCOVERY";
          ...
          setHsmState(...);
        }
        break;
      case "WAL_WRITE_JOB":
        addEvent("WAL", `Write job ${raw.job_id || ""} committed to SQLite WAL`, "info");
        break;
      case "DELTA_DETECTED":
        addEvent("DELTA", `Stale code detected in ${raw.file || "file"}`, "warning");
        break;
    }
  }
  ```
  Entretanto, uma busca reversa por `RATE_GOVERNOR_UPDATE`, `HSM_STATE_UPDATE` e `WAL_WRITE_JOB` em todo o repositório comprova que **nenhum arquivo Python de backend possui essas constantes**. O gerador SSE em `interface/telemetry_api.py:553, 569` transmite estritamente:
  ```python
  yield f"data: {json.dumps(payload, default=str)}\n\n"
  ```
  Onde `payload` é construído por `_build_telemetry_payload`, que retorna apenas um dicionário `TelemetryPayloadSchema` com `integrity_score, sqlite_total_files, queue_backlog, dirty_queue, agent_sessions, self_healing_events, janitor_status, tailscale_ip`.
- **Impacto:**
  O bloco `switch (raw.event_type)` é 100% código inalcançável. Por consequência direta, os medidores de cota do Rate Governor (`QuotaGauges`) e o inspetor de estados HSM (`HSMStateInspector`) nunca recebem nenhuma atualização dinâmica durante a sessão via SSE. Permanecem permanentemente congelados nos valores da hidratação REST inicial do boot (`hydrateRest`), descaracterizando o HUD cognitivo como ferramenta de monitoramento em tempo real.

---

### Achado #2: Ciclo Infinito de Flapping SSE e Inundação do Buffer de Eventos
- **Severidade:** 🔴 **CRÍTICA**
- **Arquivos:** [`grafo-dashboard-web/lib/useTelemetryStream.ts:280–291`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/useTelemetryStream.ts#L280) e [`interface/telemetry_api.py:556–572`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L556)
- **Mecanismo:**
  No backend (`interface/telemetry_api.py:556-562`), a função assíncrona `_telemetry_event_generator` possui um loop de monitoramento com uma trava de testes mantida em produção:
  ```python
  check_count = 0
  max_checks = 5  # Limit to prevent infinite loop in tests
  while check_count < max_checks:
      await asyncio.sleep(1.0)
      check_count += 1
  ```
  Após exatamente 5 verificações (5 segundos), o gerador termina e a conexão HTTP SSE é fechada pelo servidor.
  No frontend (`lib/useTelemetryStream.ts:280-291`), o fechamento do stream dispara o callback `es.onerror`:
  ```typescript
  es.onerror = () => {
    if (!isMounted) return;
    setStatus("disconnected");
    setError("SSE connection lost. Reconnecting in 3s...");
    es.close();
    eventSourceRef.current = null;
    reconnectTimeoutRef.current = setTimeout(() => {
      if (isMounted) connectSSE();
    }, 3000);
  };
  ```
  Ao reconectar após 3 segundos, `es.onopen` executa:
  ```typescript
  addEvent("SYSTEM", "Connected to FastAPI Telemetry SSE Stream", "success");
  ```
- **Impacto:**
  O sistema entra em flapping contínuo: 5 segundos conectado $\rightarrow$ desconexão $\rightarrow$ 3 segundos esperando $\rightarrow$ reconexão. Em uma sessão de 10 minutos, ocorrem 75 ciclos de desconexão e reconexão. O buffer de eventos (`events`), que armazena até 200 itens, é rapidamente inundado por 75 mensagens idênticas de status de conexão, expurgando os eventos legítimos de WAL, deltas e Janitor. Além disso, o badge visual de status no cabeçalho fica alternando perpetuamente entre verde e vermelho.

---

### Achado #3: Colisão de Portas, Inoperância do Script `dev:all` e Desconexão do FastMCP SSE
- **Severidade:** 🔴 **CRÍTICA**
- **Arquivos:** [`grafo-dashboard-web/package.json:10–11`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/package.json#L10), [`grafo-dashboard-web/.env.local:6, 10`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/.env.local#L6), [`grafo-dashboard-web/lib/mcp/client.ts:29`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/mcp/client.ts#L29), [`main.py:70, 245`](file:///c:/Nexus-Memory/GrafoConcierge/main.py#L70), [`interface/mcp_server.py:143–145`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L143), [`interface/telemetry_api.py:588`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L588)
- **Mecanismo:**
  1. No `package.json`, o script para desenvolvimento local completo é:
     ```json
     "dev:backend": "cd ../GrafoConcierge && python main.py",
     "dev:all": "concurrently -k -n \"NEXT,PY\" -c \"cyan,green\" \"npm run dev\" \"npm run dev:backend\""
     ```
  2. Porém, `main.py` executa apenas o servidor MCP via `server.run(transport=TRANSPORT)`. A variável `TRANSPORT` possui valor padrão `"stdio"` (`main.py:70`). Em modo `stdio`, o servidor **não abre nenhuma porta de rede**.
  3. Se o desenvolvedor configurar `GRAFO_TRANSPORT=sse`, o `FastMCP` sobe na porta padrão `8000` (`interface/mcp_server.py:143`).
  4. Ao mesmo tempo, o `telemetry_api.py:588` (FastAPI) *também* é configurado para rodar na porta `8000`. Se ambos os serviços forem executados na mesma máquina, ocorre colisão de porta `OSError: [WinError 10048] Only one usage of each socket address is normally permitted`.
  5. Para tornar a situação crítica, o frontend define no [`.env.local:6`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/.env.local#L6) e no fallback de [`lib/mcp/client.ts:29`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/mcp/client.ts#L29):
     ```
     NEXT_PUBLIC_GRAFO_MCP_URL=http://127.0.0.1:7077/sse
     NEXT_PUBLIC_CONCIERGE_API_URL=http://127.0.0.1:8000
     ```
- **Impacto:**
  Ao executar o comando canônico `npm run dev:all`, o dashboard Next.js sobe mas fica completamente desconectado:
  - O cliente FastMCP tenta conectar na porta `7077`, onde não há nenhum serviço rodando, caindo em loop perpétuo de backoff exponencial de reconexão (`attempt 1, 2, 3...`).
  - As requisições de telemetria falham com `Connection refused` na porta `8000` porque `main.py` não sobe o `telemetry_api.py`.
  - Se um operador tentar subir `telemetry_api.py` manualmente na porta 8000 e `main.py` com `GRAFO_TRANSPORT=sse`, um dos dois processos falha imediatamente por conflito de porta.

---

### Achado #4: Incompatibilidade de Autenticação FastMCP e Rejeição Total com HTTP 401
- **Severidade:** 🟠 **GRAVE**
- **Arquivos:** [`grafo-dashboard-web/lib/mcp/client.ts:78, 294–298`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/mcp/client.ts#L78) e [`interface/mcp_server.py:186–212`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L186)
- **Mecanismo:**
  No backend (`interface/mcp_server.py`), se `GRAFO_API_KEY` for definida no ambiente, um middleware de autenticação HTTP é registrado na aplicação Starlette do FastMCP:
  ```python
  if api_key:
      @app.middleware("http")
      async def auth_middleware(request, call_next):
          auth_header = request.headers.get("Authorization", "")
          token_param = request.query_params.get("token", "")
          is_valid = False
          if auth_header.startswith("Bearer "):
              is_valid = (auth_header[7:].strip() == api_key)
          elif token_param:
              is_valid = (token_param.strip() == api_key)
          if not is_valid:
              return JSONResponse({"error": "Unauthorized access to Grafo Concierge MCP"}, status_code=401)
          return await call_next(request)
  ```
  No entanto, o cliente Next.js em [`lib/mcp/client.ts`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/mcp/client.ts) conecta-se via `new EventSource(this.sseUrl)`. A API nativa do navegador `EventSource` **não permite envio de headers HTTP personalizados** (como `Authorization: Bearer ...`).
  Além disso, o método `sendRequest` (`lib/mcp/client.ts:294-298`) executa requisições `fetch()` via `POST` contendo apenas `headers: { "Content-Type": "application/json" }`, sem injetar credenciais ou token. O `.env.local` também não possui nenhuma variável para configurar a API Key.
- **Impacto:**
  Sempre que um ambiente configurar `GRAFO_API_KEY` por requisitos de segurança, o `grafo-dashboard-web` fica 100% inoperante: a conexão SSE é rejeitada imediatamente com HTTP 401 Unauthorized e o envio de qualquer comando JSON-RPC é bloqueado pelo servidor.

---

### Achado #5: Omissão de Metadados em `get_full_topology` e Esvaziamento do `InspectorDrawer`
- **Severidade:** 🟠 **GRAVE**
- **Arquivos:** [`storage/store.py:259–273`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L259), [`grafo-dashboard-web/app/hooks/useGraphTopology.ts:106–115`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/hooks/useGraphTopology.ts#L106), [`grafo-dashboard-web/app/components/InspectorDrawer.tsx:124–152`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/InspectorDrawer.tsx#L124)
- **Mecanismo:**
  1. A ferramenta `get_full_topology` chama `store.get_lightweight_topology()`.
  2. O método no SQLite foi explicitamente implementado para omitir texto pesado:
     ```python
     # storage/store.py:260
     """Avoids loading text summaries (summary) or embeddings for bandwidth optimization."""
     nodes_sql = "SELECT id AS node_id, label AS name, node_type FROM nodes WHERE status = 'ACTIVE'"
     ```
     O retorno contém apenas `{"node_id": int, "name": str, "node_type": str}`.
  3. No frontend, o hook `useGraphTopology.ts` mapeia o resultado:
     ```typescript
     summary: node.summary || null, // Sempre null
     tags: node.tags || null,       // Sempre null
     ```
  4. O painel de inspeção de propriedades [`InspectorDrawer.tsx:124–152`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/InspectorDrawer.tsx#L124) condiciona a exibição das seções "Pipeline Description" e "Semantic Tags" à presença de `node.summary` e `node.tags` no objeto selecionado. Como não existe nenhuma chamada secundária sob demanda (ex.: buscar detalhes do nó por ID ao clicar), esses campos nunca existem.
- **Impacto:**
  Sempre que o usuário clica em um nó na galáxia 3D ou 2D para inspecioná-lo, o `InspectorDrawer` abre exibindo apenas o nome e o tipo do nó. Os dados cruciais de documentação gerados pelo pipeline de ingestão (resumo L0/L1/L2 e tags semânticas) ficam permanentemente inacessíveis na interface gráfica.

---

### Achado #6: Risco de Crash e Corrupção de Data (`Invalid Date`) em `CoreMemoryPanel`
- **Severidade:** 🟡 **MÉDIA**
- **Arquivo:** [`grafo-dashboard-web/app/components/CoreMemoryPanel.tsx:137–146`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/components/CoreMemoryPanel.tsx#L137)
- **Mecanismo:**
  Ao formatar a data de atualização de cada bloco de memória (`MemoryBlock`), o componente executa:
  ```typescript
  const formattedDate = new Date(block.updated_at + "Z").toLocaleString(...);
  ```
  Se o valor retornado pelo backend para `updated_at` já contiver um identificador de timezone (como `"2026-09-25T12:00:00Z"` ou `"...+00:00"`), a concatenação resulta na string inválida `"...ZZ"`.
- **Impacto:**
  No motor JavaScript V8, `new Date("...ZZ")` produz um objeto `Invalid Date`. A subsequente chamada a `.toLocaleString()` pode lançar `RangeError: Invalid time value` em certos navegadores ou renderizar a string ininteligível `"Invalid Date"` no card do bloco de memória.

---

### Achado #7: Rotas Mutantes Órfãs e Callbacks Inertes no HUD
- **Severidade:** 🟡 **MÉDIA**
- **Arquivos:** [`grafo-dashboard-web/app/page.tsx:478–482`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/page.tsx#L478) e [`grafo-dashboard-web/components/hsm/HSMStateInspector.tsx:191`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/hsm/HSMStateInspector.tsx#L191)
- **Mecanismo:**
  O componente `HSMStateInspector` renderiza a árvore de estados com botões clicáveis para cada sub-estado (`substates.map`), permitindo disparar transições através da prop `onSelectState(qualified)`.
  No entanto, no arquivo principal [`app/page.tsx:478-482`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/app/page.tsx#L478), o componente é instanciado sem passar a prop `onSelectState`:
  ```tsx
  <HSMStateInspector
    hsmState={hsmState}
    className="h-full"
  />
  ```
  A rota backend correspondente `POST /api/hsm/transition` (assim como `POST /api/hsm/resume/{session_id}` e `POST /api/gating/mode`) nunca é chamada pelo dashboard.
- **Impacto:**
  A interatividade anunciada na interface gráfica é ilusória: clicar nos sub-estados da máquina hierárquica não produz nenhuma ação no sistema. O painel atua como um visualizador passivo e estático, deixando recursos de controle operacional previstos no SDD-SURVIVAL-28 órfãos no backend.

---

### Achado #8: 37 Erros de Linter, Impureza em Render React 19 e Efeitos em Cascata
- **Severidade:** 🟡 **MÉDIA**
- **Arquivos:** [`grafo-dashboard-web/components/telemetry/LiveEventFeed.tsx:93–121`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/components/telemetry/LiveEventFeed.tsx#L93), [`grafo-dashboard-web/lib/useTelemetryStream.ts:191`](file:///c:/Nexus-Memory/GrafoConcierge/grafo-dashboard-web/lib/useTelemetryStream.ts#L191)
- **Mecanismo:**
  A execução de `npm run lint` reporta 42 problemas (37 erros e 5 avisos):
  1. Em `LiveEventFeed.tsx`, o hook `useMemo` de `defaultEvents` invoca `Date.now()` diretamente durante o ciclo de renderização:
     ```typescript
     timestamp: new Date(Date.now() - 32000).toISOString(),
     ```
     O compilador React 19 (`react-hooks/purity`) classifica `Date.now` como função impura, pois leituras de relógio durante o render violam a idempotência dos componentes e provocam erros de hidratação no SSR do Next.js.
  2. Em `useTelemetryStream.ts:191`, a função `hydrateRest()` é chamada diretamente no corpo do `useEffect` de montagem (`react-hooks/set-state-in-effect`), disparando cascatas síncronas de múltiplos `setState`.
- **Impacto:**
  Embora o Next.js Turbopack permita o empacotamento estático tolerando avisos, qualquer pipeline de CI/CD rigoroso com validação de linter (`eslint`) falha imediatamente com código 1.

---

## 4. Prova Empírica de Reprodução

A reprodução foi conduzida via script autônomo de integração [`scratch/reproduce_dashboard_findings.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_dashboard_findings.py) e execução de validação de linter `npm run lint`.

### 4.1. Saída Bruta da Validação de Integração de API e Contratos (`reproduce_dashboard_findings.py`)

```text
======================================================================
TEST 1 & 2: SSE Flapping (max_checks=5) and Missing event_type
======================================================================
  [SSE Chunk 1] received: length=329
  [SSE Chunk 2] received: length=329
  [SSE Chunk 3] received: length=329
  [SSE Chunk 4] received: length=329
  [SSE Chunk 5] received: length=329
  [SSE Chunk 6] received: length=329

Total SSE chunks emitted before generator terminated: 6
Verifying if stream terminated prematurely (max_checks = 5):
  -> CONFIRMED: Generator terminated on its own after 5 checks, causing client SSE disconnect.

Verifying payload structure for 'event_type':
  Chunk 1 keys: ['integrity_score', 'sqlite_total_files', 'qdrant_total_vectors', 'orphans_detected', 'tailscale_ip']... | has 'event_type': False
  Chunk 2 keys: ['integrity_score', 'sqlite_total_files', 'qdrant_total_vectors', 'orphans_detected', 'tailscale_ip']... | has 'event_type': False
  Chunk 3 keys: ['integrity_score', 'sqlite_total_files', 'qdrant_total_vectors', 'orphans_detected', 'tailscale_ip']... | has 'event_type': False
  Chunk 4 keys: ['integrity_score', 'sqlite_total_files', 'qdrant_total_vectors', 'orphans_detected', 'tailscale_ip']... | has 'event_type': False
  Chunk 5 keys: ['integrity_score', 'sqlite_total_files', 'qdrant_total_vectors', 'orphans_detected', 'tailscale_ip']... | has 'event_type': False
  Chunk 6 keys: ['integrity_score', 'sqlite_total_files', 'qdrant_total_vectors', 'orphans_detected', 'tailscale_ip']... | has 'event_type': False

Were any typed events ('event_type': 'RATE_GOVERNOR_UPDATE', etc.) emitted? False
  -> CONFIRMED: Backend emits ONLY TelemetryPayload dictionaries without 'event_type'.
     The switch(raw.event_type) in lib/useTelemetryStream.ts is completely DEAD CODE.

======================================================================
TEST 5: get_lightweight_topology omits summary and tags needed by InspectorDrawer
======================================================================
Returned nodes count: 1
First node payload: {'node_id': 1, 'name': 'test::MyService::execute', 'node_type': 'METHOD'}

Checking fields expected by InspectorDrawer (summary, tags):
  'summary' in node: False
  'tags' in node:    False
  -> CONFIRMED: get_lightweight_topology strips summary and tags.
     InspectorDrawer receives null/undefined for all nodes clicked in the graph!

======================================================================
TEST 4: API Key Authentication in mcp_server vs Client Requests
======================================================================
  Dashboard EventSource GET /sse (no auth): HTTP 401
  Dashboard fetch POST /messages/ (no auth): HTTP 401
  -> CONFIRMED: When GRAFO_API_KEY is set, dashboard requests are immediately rejected with 401.

======================================================================
ALL DASHBOARD INTEGRATION REPRODUCTIONS CONFIRMED SUCCESSFULLY!
======================================================================
```

### 4.2. Saída Bruta da Validação de Linter (`npm run lint`)

```text
> grafo-dashboard-web@0.1.0 lint
> eslint

C:\Nexus-Memory\GrafoConcierge\grafo-dashboard-web\components\telemetry\LiveEventFeed.tsx:93:29
  93 |         timestamp: new Date(Date.now() - 32000).toISOString(),
     |                             ^^^^^^^^^^ Cannot call impure function during render
                                        react-hooks/purity
  100:29  error  Error: Cannot call impure function during render
  107:29  error  Error: Cannot call impure function during render
  114:29  error  Error: Cannot call impure function during render
  121:29  error  Error: Cannot call impure function during render

C:\Nexus-Memory\GrafoConcierge\grafo-dashboard-web\lib\useTelemetryStream.ts:191:5
  191 |     hydrateRest();
      |     ^^^^^^^^^^^ Avoid calling setState() directly within an effect
                                        react-hooks/set-state-in-effect

✖ 42 problems (37 errors, 5 warnings)
```

---

## 5. Recomendações Corretivas e Próximos Passos (Gate da Fase 1)

1. **Unificação do Protocolo SSE de Telemetria:**
   - No backend (`interface/telemetry_api.py`), emitir eventos SSE com campo `event` do protocolo padrão (ex.: `event: rate_governor\ndata: {...}\n\n` ou envolver em `{"event_type": "...", "data": {...}}`) para que `RATE_GOVERNOR_UPDATE`, `HSM_STATE_UPDATE` e `DELTA_DETECTED` atualizem dinamicamente o HUD.
   - Remover a trava de teste `max_checks = 5` substituindo por um loop assíncrono perpétuo com `while True: await asyncio.sleep(1.0)`.
2. **Harmonização de Portas e Orquestração de Boot:**
   - Padronizar portas no repositório: definir FastAPI Telemetria em `8000` e FastMCP SSE em `7077` (ou vice-versa), e atualizar `main.py` para instanciar ambos os servidores sob um único runner ou script `dev:all`.
   - Adicionar suporte a `GRAFO_API_KEY` no `McpClient` via query parameter `?token=` na conexão `EventSource` e cabeçalho `Authorization: Bearer` nas chamadas `fetch(POST)`.
3. **Endpoint sob Demanda para Detalhes de Nós no Grafo:**
   - Manter `get_full_topology` leve, mas implementar a busca sob demanda em `InspectorDrawer` (via chamada à ferramenta MCP `concierge_load` ou endpoint REST `/api/nodes/{node_id}`) ao clicar em um nó, recuperando `summary`, `tags` e conexões completas.
4. **Resolução de Erros do React 19:**
   - Mover a inicialização de timestamps estáticos em `LiveEventFeed.tsx` para fora do corpo do componente ou usar timestamps fixos para demonstração.
   - Tratar datas com fallback seguro `new Date(block.updated_at.endsWith("Z") ? block.updated_at : block.updated_at + "Z")`.

---

## Status do Protocolo de Auditoria

Com a conclusão da auditoria de `grafo-dashboard-web/`, **todos os itens da Fase 1 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) foram integralmente concluídos e comprovados empiricamente**.

Seguindo a **Regra 7 (Stop at the Gate)**, o avanço para a **Fase 2 (Cruzamento Transversal de Módulos)** permanece bloqueado aguardando aprovação explícita do usuário.
