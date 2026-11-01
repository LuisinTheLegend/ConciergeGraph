# Errata da Rodada 4.2h

> **Data:** 2026-11-01  
> **Referência:** Auditoria independente do commit `c5e1c2c177896b81eacf821321a2086628f46f61` (Rodada `4.2h`), tratada na Rodada `4.2h-2`.

---

## (a) A prova E2E por Tripwire Proxy (`p6_tripwire_summary.txt`) não reproduz o `F4-020`; a prova de `F4-020` são os testes `S6` e `S7`

- **Fato observado na evidência da 4.2h (`scratch/evidencia_4_2h/p6_tripwire_summary.txt`):** Em todas as repetições de `old_96ba4d0` (`E1`, `E2`, `E3`), a coluna `LoopCl` (`"Event loop is closed"`) e a coluna `TaskEx` (`"Task exception was never retrieved"`) registraram **`0`**.
- **Causa técnica:** O `TripwireProxyServer` recusa o método `CONNECT api.openai.com:443` imediatamente com `HTTP 403 Forbidden` antes que um túnel TLS/HTTP seja estabelecido. Sem conexão HTTP/TLS ativa estabelecida pelo `httpx.AsyncClient`, não resta transporte aberto pendente de fechamento assíncrono (`aclose()`) quando `asyncio.run(...)` encerra o event loop.
- **Retificação:** A prova E2E por Tripwire Proxy comprova exclusivamente o **`F4-019`** (egress de rede bloqueado em `E1`/`E2` com `0` conexões no código novo vs `27 CONNECT` no código antigo, e `27 CONNECT` quando `GRAFO_LLM_PROVIDER=openai` é definido explicitamente em `E3`). Ela **não** reproduz o **`F4-020`**. A prova executável e determinística do **`F4-020`** reside nos testes **`S6`** (verificação direta de `__enter__`/`__exit__` e `__aenter__`/`__aexit__` mesmo sob exceção) e **`S7`** (`test_s7_orchestrator_asyncio_run_closes_clients_no_unraisable_loop_closed` em [`tests/test_llm_egress_guard.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_llm_egress_guard.py), que utiliza um servidor HTTP local respondendo `HTTP 401` sem túnel `CONNECT`, reproduzindo o `RuntimeError: Event loop is closed` no código sem `async with` e provando `0` ocorrências com `async with`).

---

## (b) Redação em `audits/bypass-governanca-por-session-id.md` (linhas 249 e 256)

- **Fato observado:** No commit `498f995` da Rodada `4.2h`, o script de redação de evidências modificou as linhas `249` e `256` de [`audits/bypass-governanca-por-session-id.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/bypass-governanca-por-session-id.md#L249-L256) (relatório da Fase 2).
- **Retificação:** Os valores presentes naquelas duas linhas eram chaves falsas de mock de teste (`sk-proj-...` fictício criado pelo script de PoC da Fase 2), e não chaves reais. A substituição por `[REDACTED]` é inócua para o conteúdo técnico do relatório, mas alterou um arquivo histórico da Fase 2 fora dos 3 arquivos de evidência da Fase 4 listados originalmente em `F4-021`.

---

## (c) Link incorreto para a Regra 13 do `AUDIT_PROTOCOL.md` no resumo da 4.2h

- **Fato observado:** A resposta/resumo da Rodada `4.2h` referenciou a Regra 13 com o link `AUDIT_PROTOCOL.md#L131-L142`.
- **Retificação:** No arquivo [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md#L46), a **Regra 13** está localizada na **linha 46** (uma única linha):
  > `13. Nenhuma evidência é commitada sem passar por scratch/tools/scan_secrets.py (zero achados em scratch/ e audits/); chaves reais nunca entram em testes.`

---

## (d) Omissão dos itens (a) e (b) no resumo de chat da Rodada 4.2h

- **Fato observado:** O resumo apresentado no chat ao final da Rodada `4.2h` não destacou espontaneamente que `p6_tripwire_summary.txt` mostrava `"Event loop is closed" = 0` no código antigo (item `a`) nem que o quarto arquivo redigido (`audits/bypass-governanca-por-session-id.md`) continha apenas mock de teste da Fase 2 (item `b`).
- **Retificação:** Ambos os pontos ficam formalmente registrados nesta errata como parte da documentação auditável do repositório.

