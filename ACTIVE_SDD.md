### 🧭 ACTIVE BLUEPRINT: OPERATION SECURITY & UX (WAVE 5)
#### 🟢 STATUS: EM EXECUÇÃO

#### OBJETIVO TÉCNICO
Erradicar riscos críticos de segurança (vazamento de chaves de API), prevenir deadlocks permanentes em serviços de background (Janitor), aplicar validação estrita de schema (fail-fast) nas entradas do servidor MCP e criar o bootstrap da memória central do usuário, atingindo a maturidade de produção.

#### 🛠️ ESPECIFICAÇÕES DE CONTRATO (PATCHES DE SANEAMENTO)

**1. Blindagem de Segredos (Fix Ponto 1)**
*   **Arquivo Alvo:** `opencode.json` (ou `.config/opencode/opencode.json` do usuário), `.env` e `.gitignore`.
*   **Ação:** A chave `GRAFO_LLM_API_KEY` está hardcoded em texto plano no JSON [1, 2].
*   **Contrato:** Remover a chave de API do bloco "environment" do arquivo de configuração do opencode [2]. Criar ou atualizar o arquivo `.env` na raiz do projeto com esta chave [2]. Garantir que `.env` esteja no `.gitignore` para evitar vazamentos em commits futuros [2].

**2. Imunidade a Deadlocks no Janitor (Fix Ponto 14)**
*   **Arquivo Alvo:** `services/janitor.py`.
*   **Ação:** O Idle-Lock depende de um `threading.Event()`. Se o processo travou, o Janitor fica bloqueado para sempre esperando a flag [3, 4].
*   **Contrato:** Implementar um timeout absoluto de 5 minutos (300 segundos). Adicionar `self._mine_timestamp = time.monotonic()` no start. No método `is_system_active()`, se o tempo passado for maior que 5 minutos, limpar ativamente a flag (`self._mine_active.clear()`) e logar o resgate, garantindo que o Janitor sempre volte a rodar [4].

**3. Validação Fail-Fast nas Tools MCP (Fix Ponto 15)**
*   **Arquivos Alvo:** `interface/mcp_server.py`.
*   **Ação:** Tools delegam a validação (como checar `scope_type`) para o banco de dados, falhando tarde e silenciosamente [5, 6].
*   **Contrato:** Injetar validação inicial nas funções de handler (ex: `_handle_store_fact`, `_handle_set_memory`). Verificar se o `scope_type` está dentro do grupo válido (`user`, `session`, `agent`, `org`) e se as strings não estão vazias ANTES de chamar a Fachada, retornando mensagens de erro claras se a requisição for inválida [6].

**4. Bootstrap da Core Memory (Fix Ponto 3)**
*   **Arquivo Alvo:** `scripts/bootstrap_core_memory.py` (novo arquivo).
*   **Ação:** A tabela `user_core_memory` foi ativada na Wave 2, mas continua vazia pois precisa de um preenchimento inicial [7, 8].
*   **Contrato:** Criar o script de bootstrap que insere automaticamente blocos de memória padrão (ex: `block_label="context_rules"` e `block_label="persona"`) com escopo de "agent" para que o sistema saia do zero e tenha uma base de personalização operacional [9].
