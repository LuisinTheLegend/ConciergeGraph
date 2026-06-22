### 🧭 ACTIVE BLUEPRINT: QDRANT NO-OP SILENT FAILURE PATCH
#### 🟢 STATUS: EM EXECUÇÃO

#### OBJETIVO TÉCNICO
Erradicar a falha silenciosa no mecanismo de fallback do banco vetorial. O sistema deve emitir um log de alerta severo caso a biblioteca `qdrant-client` não esteja instalada, avisando inequivocamente ao usuário e ao MCP que as operações de memória episódica estão operando em modo NO-OP (retornando vazio).

#### 🛠️ ESPECIFICAÇÕES DE CONTRATO (PATCH DE TELEMETRIA)

**1. Injeção de Alerta Severo na Inicialização**
*   **Arquivo Alvo:** `vector_backend.py` (Classe `QdrantVectorStore`) [1].
*   **Ação:** Fazer um `[MODIFY]` no bloco `try-except` que tenta importar o `qdrant-client`.
*   **Lógica:** Onde atualmente o `ImportError` é capturado de forma silenciosa para definir `QDRANT_AVAILABLE = False` [1], injetar uma chamada de log severo (ex: `logger.warning` ou `logger.error`).
*   **Mensagem Sugerida:** `"[CRITICAL] qdrant-client não encontrado. QdrantVectorStore operando em modo NO-OP. Buscas semânticas retornarão vazias!"`

**2. Alerta Opcional em Tempo de Execução**
*   **Ação:** Adicionar um log de nível `debug` ou `warning` com throttle (para não floodar o terminal) nos métodos de gravação, busca e deleção, avisando: `"Operação ignorada: Qdrant em modo NO-OP"`. 

**3. Manutenção de Testes**
*   Garantir que a injeção dos logs não quebre a suíte de testes.
