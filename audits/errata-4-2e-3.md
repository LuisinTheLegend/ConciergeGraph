# ERRATA E ESCLARECIMENTOS — RELATÓRIO 4.2e-3

Este documento registra retificações, esclarecimentos metodológicos e notas de precisão técnica referentes à Rodada 4.2e-3 e seus relatórios prévios.

---

### 1. Origem dos Dados da "Opção B" na Matriz Comparativa
A coluna **"Opção B"** da matriz comparativa em `relatorio_4_2e_3.md` **não** foi obtida a partir do experimento E10 (o qual validou exclusivamente `decouple_fd0` e `preimport` completo de `sentence_transformers`), mas sim interpolada a partir do experimento **E9 (Conjunto S3)**. Os tempos registrados no E9 (ex.: pré-import de S6 levando de 33 a 43 s) indicam contaminação decorrente de concorrência com o experimento E7, não devendo ser interpretados como medições isoladas de regime estável de produção.

---

### 2. Concorrência vs Execução Sequencial dos Experimentos E7, E8, E9 e E10
A verificação dos timestamps de geração dos arquivos e logs confirma:
- **E8 (`run_e8_pipe.py`):** Executado de forma sequencial às **23:37** de 28/10/2026.
- **E7 (`run_e7_decouple.py`) e E9 (`run_e9_preimport_matrix.py`):** **Rodaram simultaneamente em segundo plano.**
  - E7 iniciou às **23:53** de 28/10/2026 e finalizou às **00:43** de 29/10/2026.
  - E9 iniciou às **00:20** de 29/10/2026 e finalizou às **01:39** de 29/10/2026.
  - Portanto, entre 00:20 e 00:43 houve contenção ativa de CPU/disco e concorrência no carregamento de DLLs entre E7 (controle `control_fd0`) e E9 (conjuntos S6, S5, S4), explicando os tempos elevados de pré-importação.
- **E10 (`run_e10_validation.py`):** Executado de forma estritamente sequencial e isolada na tarde de 29/10/2026 (14:54 às 15:11), sem nenhum outro experimento ativo no sistema.

---

### 3. Discrepância de Tempo de Mineração (78s em 7db9f7d vs 21-25s em E10)
A causa da discrepância foi investigada e comprovada por análise dos logs de execução:
- No commit `7db9f7d` (Passo 2 da 4.2e), a variável `GRAFO_LLM_MODEL` estava configurada como `none`. O cliente legado de sumarização tentava conectar ao endpoint do Gemini sem URL válida, gerando **6 tentativas de conexão com timeout de socket de ~12 s cada** (totalizando ~72 s apenas em espera de timeout de rede na fase `[3/8] SUMMARIZE`).
- No experimento E10 (commit `dd92d35`), a requisição HTTP recebeu resposta imediata de erro (`404 Model no longer available` no Gemini e `401 Unauthorized` no fallback OpenAI), falhando rapidamente em fração de segundo e acionando o fallback local (Dumb Summary) em ~22 s no total.
- A diferença de ~55 s decorre, portanto, de timeouts de socket na camada de LLM do summarizer, e não de variação no motor de embedding ou de armazenamento.

---

### 4. Fragilidade Teórica e Prática da Opção B (Pré-import Parcial S3)
Os dados empíricos do experimento E9 revelam uma inconsistência estrutural:
- **S2** `{numpy, scipy.special}`: **100% TRAVOU** (5/5).
- **S3** `{numpy, scipy.special, sklearn.utils._array_api}`: **100% OK** (5/5).
- **S4** `{torch}`: **100% TRAVOU** (5/5).
- **S5** `{numpy, scipy.special, torch}`: **100% TRAVOU** (5/5).
Isso comprova que a Opção B depende criticamente de "adivinhar" a cadeia interna e transitiva exata de DLLs que a biblioteca `sentence_transformers` carrega dinamicamente. Qualquer atualização ou refatoração interna de dependências que introduza uma nova importação de DLL sob o leitor bloqueado reintroduzirá o deadlock silenciosamente.

---

### 5. Mecanismo Interno do Windows Classificado como HIPÓTESE
Embora os experimentos E1, E2, E7, E8 e E10 sejam inteiramente compatíveis com a hipótese de um conflito de sincronização da C-Runtime (CRT / `RtlEnterCriticalSection`) ao inicializar DLLs numéricas (OpenBLAS/MKL/OpenMP) enquanto uma thread está bloqueada em `ReadFile` no `STD_INPUT_HANDLE` (fd 0), o mecanismo exato no código-fonte fechado do Windows e das bibliotecas C **permanece formalmente classificado como [HIPÓTESE NÃO DEMONSTRADA]**. Os fatos comprovados são restritos ao comportamento observável registrado nos arquivos de teste.
