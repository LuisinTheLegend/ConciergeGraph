🧬 Conteúdo para o Antigravity: Active-SDD #12
# 🧬 Active-SDD #12: Smart Checkpoint Pruning (Auto-Poda de Checkpoints)

## 🗺️ 1. Identificação e Propósito
* **ID da Especificação:** `SDD-SURVIVAL-12`
* **Módulo de Destino:** `core/janitor.py` (ou classe `BackgroundJanitor` correspondente) e `core/database.py` (ou `AgnosticCheckpointer`)
* **Arquivo de Teste Relacionado:** `tests/test_checkpoint_pruning.py`
* **Objetivo Principal:** Prevenir o crescimento indefinido e inflacionado do banco de dados `state.db` devido ao acúmulo contínuo de blobs JSON de checkpoints de enxames de agentes em sessões de longa duração. Implementaremos um algoritmo de **Auto-Poda Inteligente (Smart LRU per Session)** que limita o histórico de cada sessão de agente ativa estritamente aos últimos \\(N\\) passos (ex: 10), garantindo a preservação inviolável do "ponto zero" (o checkpoint inicial da sessão, fundamental para rollbacks totais) e realizando a expurgação física dos checkpoints intermediários obsoletos através de exclusões paginadas em lotes pequenos e concorrentes.

---

## 🔍 2. Análise de Impacto de Segunda Ordem (Análise de Riscos)

A arquitetura refinou as regras de limpeza para evitar efeitos colaterais catastróficos em produção:

*   **Risco de Perda de Pontos de Restauração Críticos (Rollback de Fábrica):** Se usarmos um LRU cego (apenas apagar os mais antigos), o sistema pode apagar o primeiro checkpoint registrado (o checkpoint de inicialização `init` de quando o agente foi criado). Sem ele, o agente perde a capacidade de realizar um "Hard Reset" para o estado original caso falhe terrivelmente no meio do caminho.
    *   *Mitigação:* O algoritmo de poda deve classificar os checkpoints por sessão de forma cronológica e **proteger o checkpoint de menor ID ou ID igual a 'init' / 'start'**, aplicando a regra de expurgo LRU apenas sobre os checkpoints intermediários subsequentes.
*   **Risco de Contenção de Banco (Locks do SQLite no Expurgo):** Tentar deletar milhares de registros obsoletos de uma só vez pode bloquear o banco de dados temporariamente, interrompendo as leituras em tempo real dos agentes ativos.
    *   *Mitigação:* O `BackgroundJanitor` deve enviar as exclusões para a nossa recém-turbinada `SerializedWriteQueue` de forma paginada (ex: deletar no máximo de 50 em 50 registros por ciclo de ociosidade) para manter o tráfego do SQLite WAL livre de latências.

---

## ⚙️ 3. Contrato de Funcionamento e Especificação

O método `prune_session_checkpoints` a ser exposto no `BackgroundJanitor` (ou integrado na classe `AgnosticCheckpointer`) deve seguir o seguinte fluxo lógico:

1.  **Parâmetros de Entrada:** Aceitar `session_id` (opcional: se omitido, processar todas as sessões), `keep_limit` (quantidade máxima de históricos recentes para manter, padrão = 10).
2.  **Identificação de Alvos de Expurgo:**
    Para cada sessão de agente ativa identificada na tabela `agent_checkpoints`:
    *   Selecionar todos os checkpoints ordenados cronologicamente por data de gravação ou ID incremental.
    *   **Proteger o Primeiro Checkpoint:** Identificar o primeiro registro da lista (o menor ID ou o checkpoint com tag especial `init` / `start`) e removê-lo da fila de exclusão. Ele é imutável.
    *   **Calcular Backlog:** Dos registros restantes, manter os mais recentes até o limite de `keep_limit`.
    *   Todos os registros intermediários que sobrarem antes do limite dos recentes são marcados como **Obsoletos**.
3.  **Execução em Lote Paginado:**
    *   Enviar o comando de deleção em lote para a `SerializedWriteQueue` usando o padrão:
    ```sql
    DELETE FROM agent_checkpoints 
    WHERE session_id = ? 
      AND checkpoint_id NOT IN (lista_de_ids_para_preservar);
    ```
    *   Onde a `lista_de_ids_para_preservar` inclui o checkpoint inicial protegido + os \\(N\\) checkpoints mais recentes.

---

## 🧪 4. Suíte de Testes TDD (`tests/test_checkpoint_pruning.py`)

Esta suíte de testes valida que a rotina de poda do Janitor limpa os dados sem violar o ponto de inicialização e o limite máximo de registros ativos:

```python
import unittest
import tempfile
import os
import sqlite3
import time
from interface.queue_writer import SerializedWriteQueue
from core.database import ConciergeDatabaseManager
# Adapte os imports conforme a localização real das suas classes de Checkpointer/Janitor
from core.database import AgnosticCheckpointer 
from core.janitor import BackgroundJanitor

class TestCheckpointPruning(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)
        
        # Garante a criação física da tabela de checkpoints para os testes
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS agent_checkpoints ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "agent_id TEXT, session_id TEXT, checkpoint_id TEXT, state_blob TEXT, timestamp REAL"
            ");"
        )
        self.checkpointer = AgnosticCheckpointer(self.db_manager)
        self.janitor = BackgroundJanitor(self.db_manager)
        time.sleep(0.1)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_smart_lru_pruning_preserves_init_and_recents(self):
        """Valida que a auto-poda remove checkpoints intermediários, mas protege o init e os mais recentes"""
        session_id = "test_session_99"
        agent_id = "test_agent_01"

        # 1. Grava o checkpoint inicial crítico (ID "init") que nunca deve ser apagado
        self.db_manager.write_query(
            "INSERT INTO agent_checkpoints (agent_id, session_id, checkpoint_id, state_blob, timestamp) "
            "VALUES (?, ?, 'init', '{\"step\": 0}', ?);",
            (agent_id, session_id, time.time())
        )
        time.sleep(0.01)

        # 2. Grava 15 checkpoints intermediários em sequência cronológica rápida
        for i in range(1, 16):
            self.db_manager.write_query(
                "INSERT INTO agent_checkpoints (agent_id, session_id, checkpoint_id, state_blob, timestamp) "
                "VALUES (?, ?, ?, ?, ?);",
                (agent_id, session_id, f"step_{i}", f"{{\"step\": {i}}}", time.time())
            )
            time.sleep(0.01)

        # 3. Dispara a limpeza do Janitor pedindo para manter no máximo os últimos 5 checkpoints por sessão
        self.janitor.prune_session_checkpoints(session_id=session_id, keep_limit=5)
        time.sleep(0.3)  # Pausa para o processamento assíncrono na fila de escrita

        # 4. Verifica o estado atual do banco físico
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT checkpoint_id FROM agent_checkpoints WHERE session_id = ? ORDER BY id ASC;",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        saved_checkpoint_ids = [r[0] for r in rows]

        # ASSERÇÃO 1: O checkpoint inicial "init" DEVE estar preservado intacto!
        self.assertIn("init", saved_checkpoint_ids)

        # ASSERÇÃO 2: Os 5 checkpoints mais recentes (step_11 a step_15) DEVEM estar preservados intactos!
        for i in range(11, 16):
            self.assertIn(f"step_{i}", saved_checkpoint_ids)

        # ASSERÇÃO 3: Checkpoints antigos intermediários (ex: step_1, step_2, step_10) DEVEM ter sido eliminados
        self.assertNotIn("step_1", saved_checkpoint_ids)
        self.assertNotIn("step_5", saved_checkpoint_ids)
        self.assertNotIn("step_10", saved_checkpoint_ids)

        # ASSERÇÃO 4: Placar final de registros mantidos no banco deve ser exatamente 6 (1 init + 5 recentes)
        self.assertEqual(len(saved_checkpoint_ids), 6)
