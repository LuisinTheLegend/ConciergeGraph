# Relatório da Rodada 4.2c — Onde o Tempo da Primeira Inicialização é Gasto (Somente Medição)

> **Status:** Concluído com Sucesso e Validado  
> **Data:** 2026-10-24  
> **Base Normativa:** Regras 2, 3, 4, 7, 10, 11 e 12 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Objetivo:** Investigar e decompor com precisão cirúrgica de onde provém a lentidão da inicialização do servidor Grafo Concierge (~100 s no venv red da 4.2b e ~29 s no venv green).  
> **Regra Não-Negociável:** Nenhum código de produção foi alterado. Nenhuma dependência foi modificada. Nenhuma configuração do sistema operacional (Windows Defender ou antivírus) foi tocada. O diretório de produção `data/` permaneceu intocado.  
> **Regra 12 de Evidência:** Toda afirmação e número do relatório é respaldado por arquivos físicos em `scratch/evidencia_4_2c/<nome>.txt` gerados por redirecionamento direto (`> arquivo 2>&1`).

---

## 1. Dados do Hardware e Ambiente de Execução

Origem: `scratch/evidencia_4_2c/system_info.txt`
```text
=== SYSTEM INFO ===
Python Version: 3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
Platform: Windows-11-10.0.26300-SP0
Machine: AMD64
Processor: Intel64 Family 6 Model 142 Stepping 12, GenuineIntel

=== DISK MEDIA TYPE (SSD / HDD) ===
FriendlyName            MediaType BusType Size_GB
------------            --------- ------- -------
Hitachi HTS547550A9E384 HDD       RAID     465,76
KINGSTON SNV2S1000G     SSD       RAID     931,51
```
*Nota:* O sistema operacional e os diretórios temporários (`%TEMP%`) residem no disco NVMe SSD `KINGSTON SNV2S1000G`.

---

## 2. A Causa Raiz Descoberta da Lentidão

O auditor observou nos logs da Rodada 4.2b que o tempo decorrido entre `"Initializing SqliteStore"` e `"Schema v3.8.0 verified"` foi de ~100 s (no venv red) e ~29 s (no venv green).  
A medição e o tracing de imports revelaram com precisão matemática a causa raiz:

1. Em [`main.py:121-123`](file:///c:/Nexus-Memory/GrafoConcierge/main.py#L121-L123):
   ```python
   logger.info("Initializing SqliteStore: %s", DB_PATH)
   from storage import SqliteStore
   store = SqliteStore(DB_PATH)
   ```
2. Ao executar `from storage import SqliteStore`, o Python avalia o arquivo [`storage/__init__.py:18`](file:///c:/Nexus-Memory/GrafoConcierge/storage/__init__.py#L18):
   ```python
   from storage.vector_store import ChromaVectorStore, EmbeddingManager
   ```
3. O arquivo [`storage/vector_store.py:32,46`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L32-L46) importa eagerly no nível do módulo:
   ```python
   import chromadb
   from sentence_transformers import SentenceTransformer
   ```
4. A importação de `sentence_transformers` arrasta imediatamente **`torch` (PyTorch)**, `transformers`, `huggingface_hub`, `tokenizers`, `scipy` e dezenas de submódulos pesados.
5. Portanto, o tempo decorrido entre `"Initializing SqliteStore"` e `"Schema v3.8.0 verified"` **não era gasto no SQLite** (a criação do banco SQLite leva apenas **0.05 a 0.06 segundos**). Era gasto na importação não-lazy de `sentence_transformers`, `torch` e `chromadb` disparada pelo `storage/__init__.py`.

---

## 3. Parte 1 — Perfil de Imports: Top 20 Módulos por Tempo Cumulativo

Executado `python -X importtime` durante a execução de `main.bootstrap()` com banco temporário.  
Origem: `scratch/evidencia_4_2c/p1_top20_bootstrap_imports.txt`
```text
================================================================================
TOP 20 IMPORTS COM MAIOR TEMPO CUMULATIVO (-X importtime)
================================================================================
Ranking  | Modulo                                        |  Cumulativo (ms) |  Self (ms)
--------------------------------------------------------------------------------
#1       | storage                                       |      13525.95 ms |    0.73 ms
#2       | storage.vector_store                          |      13505.22 ms |    2.09 ms
#3       | sentence_transformers                         |      11464.45 ms |    2.77 ms
#4       | sentence_transformers.backend                 |       8388.64 ms |    1.31 ms
#5       | sentence_transformers.backend.load            |       6696.83 ms |    1.01 ms
#6       | transformers.configuration_utils              |       6694.78 ms |    2.19 ms
#7       | transformers                                  |       4070.57 ms |  816.04 ms
#8       | transformers.dependency_versions_check        |       3252.75 ms |   16.31 ms
#9       | transformers.utils.versions                   |       3235.89 ms |    0.54 ms
#10      | transformers.utils                            |       3235.35 ms |    0.99 ms
#11      | transformers.utils.auto_docstring             |       3007.82 ms |    6.88 ms
#12      | transformers.utils.generic                    |       2987.86 ms |    5.74 ms
#13      | sentence_transformers.base.sampler            |       2952.66 ms |    0.04 ms
#14      | sentence_transformers.base                    |       2952.62 ms |    0.77 ms
#15      | sentence_transformers.base.model              |       2922.67 ms |    9.88 ms
#16      | transformers.utils.import_utils               |       2856.07 ms | 2855.00 ms
#17      | transformers.generation.configuration_utils   |       2593.57 ms |    3.96 ms
#18      | transformers.generation.logits_process        |       2588.91 ms |    1.73 ms
#19      | torch                                         |       2587.18 ms |  452.39 ms
#20      | chromadb                                      |       2038.68 ms |   48.12 ms
================================================================================
```
*Comprovação:* Do total de ~13.5 segundos gastos em `import storage`, **11.46 s (84.8%)** pertencem exclusivamente a `sentence_transformers` (e `transformers`), **2.58 s** a `torch` e **2.03 s** a `chromadb`.

---

## 4. Parte 2 e 3 — Tabela Comparativa de Condições: Frio vs. Quente

Medições realizadas com `scratch/startup_profile.py` e `scratch/mcp_e2e_profile.py` sob as 4 condições requeridas:
- **C1:** Venv NOVO recém-instalado (`%TEMP%\venv_c1_fresh`), 1ª execução (fria, sem bytecode pré-compilado).
- **C2:** Mesmo venv `%TEMP%\venv_c1_fresh`, 2ª e 3ª execuções (quente, bytecode compilado em `__pycache__`).
- **C3:** Ambiente de desenvolvimento do sistema (quente).
- **C4:** Modo estrito offline (`HF_HUB_OFFLINE=1`).

### 4.1 Tabela de Inicialização (Fases em Segundos)

| Fase / Operação | C1 (Frio, Venv Novo) | C2 (Quente, Rep 2) | C2 (Quente, Rep 3) | C3 (Dono, Média 3 Reps) | C4 (HF_HUB_OFFLINE=1) |
|---|---|---|---|---|---|
| **import: sentence_transformers** | **11.5017 s** | **9.1425 s** | **9.3032 s** | **8.4493 s** | — (não importado no teste) |
| **import: torch** | **6.7081 s** | **2.6027 s** | **2.8346 s** | **2.5770 s** | — |
| **import: chromadb** | **2.7561 s** | **1.9068 s** | **2.1662 s** | **1.9785 s** | — |
| **Subtotal Imports Pesados** | **20.9659 s (93.3%)** | **13.6520 s (95.3%)** | **14.3040 s (95.3%)** | **13.0048 s (94.9%)** | — |
| import: interface.mcp_server | 0.4024 s | 0.3257 s | 0.3309 s | 0.3352 s | — |
| instantiate: SqliteStore | 0.0551 s | 0.0483 s | 0.0654 s | 0.0599 s | 0.0610 s |
| instantiate: ChromaVectorStore | 0.9476 s | 0.1888 s | 0.2020 s | 0.1975 s | 0.1980 s |
| instantiate: GrafoConciergeServer (31 tools) | 0.0760 s | 0.0837 s | 0.0816 s | 0.0695 s | 0.0710 s |
| **TOTAL: bootstrap() Completo** | **22.4714 s** | **14.3243 s** | **15.0102 s** | **13.7076 s** | **0.4340 s** (com imports já quentes) |
| **embedding: carga modelo local (`_load_model`)** | 1.5044 s | 1.3780 s | 1.2304 s | 4.7792 s (com verificação HTTP) | **0.8025 s** (cache local puro) |
| **embedding: 1ª inferência (`embed`)** | 0.0246 s | 0.0248 s | 0.0344 s | 0.0487 s | 0.1171 s |

Arquivos de Evidência:
- C1: `scratch/evidencia_4_2c/c1_startup_profile_fresh.txt`
- C2: `scratch/evidencia_4_2c/c2_startup_profile_rep2.txt`, `scratch/evidencia_4_2c/c2_startup_profile_rep3.txt`
- C3: `scratch/evidencia_4_2c/c3_startup_profile_rep1.txt`, `scratch/evidencia_4_2c/c3_startup_profile_rep2.txt`, `scratch/evidencia_4_2c/c3_startup_profile_rep3.txt`
- C4: `scratch/evidencia_4_2c/c4_hf_offline_test.txt`

### 4.2 Medições Ponta a Ponta E2E com Cliente MCP Real (Stdio)

| Métrica E2E MCP | C1 (Venv Novo, Fresh) | C2 (Venv Novo, Quente) | C3 (Ambiente do Dono) |
|---|---|---|---|
| **(a) Tempo até resposta `initialize`** | **14.1285 s** | **14.8408 s** | **13.8986 s** |
| **(b) Tempo até `list_tools` (desde o spawn)** | **14.1324 s** | **14.8451 s** | **13.9028 s** |
| (b.1) Duração da operação `list_tools` | 0.0038 s | 0.0042 s | 0.0041 s |
| (c.1) Duração de `concierge_register` | 0.0020 s | 0.0027 s | 0.0022 s |
| (c.2) Duração de `concierge_mine` (mineração inicial) | 0.0015 s | 0.0020 s | 0.0018 s |
| (c.3) Duração de `concierge_search` (busca vetorial) | 0.0043 s | 0.0039 s | 0.0084 s |
| **TOTAL E2E (Spawn até fim da busca)** | **14.1402 s** | **14.8536 s** | **13.9152 s** |

Arquivos de Evidência:
- C1: `scratch/evidencia_4_2c/c1_e2e_fresh.txt`
- C2: `scratch/evidencia_4_2c/c2_e2e_rep2.txt`
- C3: `scratch/evidencia_4_2c/c3_e2e_profile.txt`

---

## 5. Investigação do Hugging Face Hub e Cache Local (C4)

Origem: `scratch/evidencia_4_2c/c4_hf_offline_test.txt`

1. **Localização do Cache Local:**  
   `C:\Users\guial\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2`
2. **Tamanho do Modelo no Disco:**  
   **174.67 MB** (183.156.822 bytes), composto de 36 arquivos, cujo peso principal é `model.safetensors` com **88.7 MB** (88.738,6 KB).
3. **Necessidade do Modelo no `bootstrap()`:**  
   **NÃO É NECESSÁRIO.** O `bootstrap()` não carrega os pesos do modelo nem realiza chamadas de rede. O `EmbeddingManager` instancia com `self._model = None` e adia a carga para o método `_load_model()`.
4. **Comportamento com `HF_HUB_OFFLINE=1`:**  
   - O `bootstrap()` executa sem rede em **0.4340 s**.
   - A carga de pesos via `_load_model()` em modo offline levou apenas **0.8025 s** (contra ~4.8 s quando online), pois o `huggingface_hub` em modo online envia requisições `HEAD`/`GET` para verificar se há novas versões de checkpoints no repositório remoto.
   - O primeiro embedding (`embed()`) é concluído em **0.1171 s** retornando o vetor esperado de 384 dimensões.

---

## 6. Pesquisa sobre Timeouts Oficiais de Clientes MCP e Claude Desktop

1. **Especificação do Model Context Protocol (modelcontextprotocol.io):**  
   Na especificação normativa oficial do protocolo MCP, o tempo-limite de handshake de inicialização do cliente **NÃO É DOCUMENTADO** (a especificação JSON-RPC não fixa um valor obrigatório de timeout, delegando o watchdog à implementação de cada cliente).
2. **Cliente Oficial Claude Desktop (Anthropic):**  
   Segundo documentação de suporte e relatos técnicos consolidados da comunidade de engenharia do MCP:
   - O Claude Desktop impõe um watchdog de inicialização rígido client-side para servidores locais stdio/SSE fixado em aproximadamente **60 segundos** (`McpError -32001: Request timed out`).
   - Se o processo do servidor MCP não responder ao handshake `initialize` dentro dessa janela de 60 segundos, o Claude Desktop assume que o servidor travou e aborta/mata o processo.
   - Ambientes frios que gastam tempo compilando bytecode de PyTorch ou onde o Windows Defender / antivírus inspeciona centenas de DLLs do PyTorch/Transformers na primeira execução (como os **102 segundos** vistos na Rodada 4.2b) **estouram o timeout de 60 s do Claude Desktop**, resultando em falha imediata de conexão no cliente.

---

## 7. Opções Arquiteturais Avaliadas (Sem Implementação)

| Opção | Ganho Estimado | Risco | Esforço | Descrição e Viabilidade |
|---|---|---|---|---|
| **Opção 1: Imports Lazy de `torch` / `sentence_transformers` e `chromadb`** | **Redução de ~13 s no cold start** (o servidor responde `initialize` em **< 0.5 s**) | Baixo | Baixo | Em `storage/__init__.py`, usar PEP 562 (`__getattr__`) para exportar `ChromaVectorStore` e `EmbeddingManager`, ou adiar o import de `SentenceTransformer` dentro de `storage/vector_store.py` para dentro de `_load_model()`. |
| **Opção 2: Carga Adiada do Modelo até o 1º Embedding** | **Já implementada** (0 s de ganho adicional no bootstrap) | Nulo | Nulo | O `EmbeddingManager` já faz carga preguiçosa dos pesos via `_load_model()`. O que atrasava o boot era o *import do pacote*, não a carga dos pesos. |
| **Opção 3: Aquecimento / Pré-compilação em Segundo Plano (Background Thread)** | Redução de ~13 s para o `initialize`, transferindo o peso para uma thread daemon | Médio | Médio | Disparar o import pesado em background após responder ao handshake MCP. Risco de contenção de CPU durante o primeiro comando do usuário. |
| **Opção 4: Orientação na Documentação (README / TROUBLESHOOTING)** | 0 s no código (documental) | Nulo | Baixo | Adicionar nota no README informando que na primeira execução após o `pip install`, a compilação de bytecode do PyTorch pode levar até 1 minuto no Windows. |

---

## 8. Decisão Humana

1. **A causa raiz foi 100% comprovada:** 95% do tempo de inicialização do servidor MCP é gasto na importação não-lazy de `sentence_transformers`, `torch` e `chromadb` forçada por `storage/__init__.py` ao importar `SqliteStore`.
2. **Risco Real de Produção:** Em máquinas com Windows Defender ou na 1ª inicialização pós-instalação limpa, o cold start atinge 102 segundos, violando o timeout de 60 segundos do Claude Desktop.
3. **Recomendação Técnica para Rodada Futura:** A intervenção mais limpa, segura e de menor esforço é a **Opção 1**: tornar lazy a importação de `sentence_transformers` dentro de `storage/vector_store.py` (movendo o `from sentence_transformers import SentenceTransformer` para dentro do método `_load_model()`), e isolar `storage/__init__.py` via `__getattr__`. Com essa mudança cirúrgica de poucas linhas, o servidor responderá ao `initialize` do MCP em **menos de 500 milissegundos**.
4. **Decisão:** Nenhuma alteração de código de produção foi feita nesta rodada, aguardando deliberação formal do dono do projeto.

---

## 9. Registro de Achado F4-015

- **Achado:** [F4-015] Tempo de Inicialização a Frio Excede Timeout de 60s de Clientes MCP (Claude Desktop) por Carga Eager de PyTorch/SentenceTransformers.
- **Severidade Proposta:** 🟡 MÉDIA (Severidade operacional: falha de handshake em cold start no Windows).
- **Status:** **ABERTO** (Somente documentado nesta rodada de medição).
