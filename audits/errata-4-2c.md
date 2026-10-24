# Errata da Rodada 4.2c — Correção das Tabelas de Medição e Notas de Calibração

> **Data:** 2026-10-24  
> **Origem dos Dados:** Extração mecânica direta dos arquivos em `scratch/evidencia_4_2c/` (Regra 12)  
> **Documento Corrigido:** [`audits/fase4-2c-medicao-inicializacao.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/fase4-2c-medicao-inicializacao.md)  

---

## 1. Motivação da Errata

Durante a auditoria e verificação cruzada com a Rodada 4.2d, identificaram-se discrepâncias entre os valores citados no texto do relatório original da 4.2c e os números reais gravados nos arquivos de evidência redirecionados (`scratch/evidencia_4_2c/`). Além disso, duas premissas analíticas requerem retificação técnica:
1. **Valores de Carga de Modelo (`_load_model`):** Citações informais em discussões e resumos mencionavam valores que divergiam dos arquivos brutos (ex.: citar 4,83 s para C1 quando o arquivo registra 1,5044 s; citar 0,86 s para C2 quando os arquivos registram 1,3780 s e 1,2304 s; e citar 0,80 s para C3 quando 0,8025 s é a medição estrita de C4 offline).
2. **Ausência de Medição de 1ª Carga no E2E da 4.2c:** O script `scratch/mcp_e2e_profile.py` executou `concierge_mine` em apenas 0,0018 s porque passou parâmetros que não dispararam a mineração nem o carregamento real do modelo de embedding. O teste E2E da 4.2c, portanto, **não mediu** a primeira carga do modelo.
3. **Superestimativa da Opção 1 (< 0,5 s):** A estimativa preliminar de que o bootstrap cairia para "< 0,5 s" apenas tornando lazy o `sentence_transformers` desconsiderou o tempo residual do ChromaDB (~1,85 s de import + ~0,20 s de instanciação). O valor real medido na 4.2d é de **~2,77 s**.

---

## 2. Tabela de Inicialização Retificada (Gerada por Script a partir dos Arquivos Brutos)

| Fase / Operação | C1 (Frio, Venv Novo) | C2 (Quente, Rep 2) | C2 (Quente, Rep 3) | C3 (Dono, Média 3 Reps) | C4 (HF_HUB_OFFLINE=1) |
|---|---|---|---|---|---|
| **import: sentence_transformers** | 11.5017 s | 9.1425 s | 9.3032 s | 8.4493 s | — |
| **import: torch** | 6.7081 s | 2.6027 s | 2.8346 s | 2.5937 s | — |
| **import: chromadb** | 2.7561 s | 1.9068 s | 2.1662 s | 1.9785 s | — |
| import: interface.mcp_server | 0.4024 s | 0.3257 s | 0.3309 s | — | — |
| instantiate: SqliteStore | 0.0551 s | 0.0483 s | 0.0654 s | — | — |
| instantiate: ChromaVectorStore | 0.9476 s | 0.1888 s | 0.2020 s | — | — |
| instantiate: GrafoConciergeServer | 0.0760 s | 0.0837 s | 0.0816 s | — | — |
| **TOTAL: bootstrap() Completo** | **22.4714 s** | **14.3243 s** | **15.0102 s** | **13.7076 s** | **0.4340 s** |
| **embedding: carga modelo (`_load_model`)** | **1.5044 s** | **1.3780 s** | **1.2304 s** | **4.7792 s** | **0.8025 s** |
| **embedding: 1ª inferência (`embed`)** | 0.0246 s | 0.0248 s | 0.0344 s | 0.0487 s | 0.1171 s |

### Detalhamento das 3 Repetições de C3 nos Arquivos Brutos:
- Repetição 1 (`scratch/evidencia_4_2c/c3_startup_profile_rep1.txt`): Bootstrap = 13.1966 s | `_load_model()` = 4.8300 s | Inferência = 0.0565 s
- Repetição 2 (`scratch/evidencia_4_2c/c3_startup_profile_rep2.txt`): Bootstrap = 13.9960 s | `_load_model()` = 4.7290 s | Inferência = 0.0396 s
- Repetição 3 (`scratch/evidencia_4_2c/c3_startup_profile_rep3.txt`): Bootstrap = 13.9302 s | `_load_model()` = 4.7787 s | Inferência = 0.0499 s

---

## 3. Retificação das Medições E2E MCP da 4.2c

| Métrica E2E MCP | C1 (`c1_e2e_fresh.txt`) | C2 (`c2_e2e_rep2.txt`) | C3 (`c3_e2e_profile.txt`) |
|---|---|---|---|
| **(a) Tempo até resposta `initialize`** | **14.1285 s** | **14.8408 s** | **13.8986 s** |
| **(b) Tempo até `list_tools` (desde spawn)** | 14.1324 s | 14.8451 s | 13.9028 s |
| (c.1) Duração de `concierge_register` | 0.0020 s | 0.0027 s | 0.0022 s |
| (c.2) Duração de `concierge_mine` (*) | 0.0015 s | 0.0020 s | 0.0018 s |
| (c.3) Duração de `concierge_search` | 0.0043 s | 0.0039 s | 0.0084 s |
| **TOTAL E2E** | 14.1402 s | 14.8536 s | 13.9152 s |

>(*) **Nota Crítica sobre `concierge_mine` no E2E da 4.2c:**  
> O tempo de ~0,0018 s indica que o comando não disparou a ingestão real nem a carga do modelo de embedding (o pipeline retornou imediatamente antes da inferência). Portanto, **o teste E2E da 4.2c NÃO mediu a latência da primeira inferência/carga de modelo**. A medição real e fidedigna dessa carga foi implementada e medida na Rodada 4.2d através de `scratch/evidencia_4_2d/first_embed_profile.py` e `functional_real_test.py`.

---

## 4. Retificação da Estimativa da Opção 1

- **Afirmação Original da 4.2c:** "o servidor responde initialize em < 0.5 s".
- **Retificação Pós-Medição 4.2d:** Esta estimativa estava superestimada. O import de `chromadb` consome ~1,83 s e a instanciação de `ChromaVectorStore` consome ~0,20 s. Com a remoção de `sentence_transformers` e `torch` no bootstrap, o tempo medido de `initialize` E2E caiu para **~3,03 s** (e bootstrap direto para **~2,77 s**). Para atingir tempos inferiores a 1 segundo no arranque, seria necessário também adiar o carregamento do `chromadb`, o que está fora do escopo da Rodada 4.2d.

