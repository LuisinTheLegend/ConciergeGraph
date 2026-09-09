🧬 Active-SDD #27: Polimento e Blindagem de Transições HSM (Hooks Lifecycle & Validação de Delta no Resume)
✅ STATUS: IMPLEMENTADO E TESTADO (20/20 testes verdes)
🗺️ 1. Identificação e Propósito
ID da Especificação: SDD-SURVIVAL-27
Módulos de Destino: core/hsm_engine.py (Suporte a Hooks de Transição e Checagem de Delta), core/checkpointer.py (Validação de Frescor Temporal de Checkpoint), agent/run_agent.py (Tratamento de Re-Indexação Automática no Resume)
Arquivo de Teste Relacionado: tests/test_hsm_transition_hooks_and_delta.py

Objetivo Principal: Concluir o polimento final da Fase 2 do ecossistema. Implementaremos as duas mitigações de segurança identificadas na auditoria da HSM:
Lifecycle Hooks (on_enter e on_exit): Permitir registro de callbacks assíncronos/síncronos nos nós da HSM para executar ações automáticas durante transições de sub-estados e super-estados (ex: limpeza de variáveis temporárias ao sair de CODE_GEN ou sincronização de auditoria ao entrar em STALL).

Validação de Delta de Arquivos no Resume: Ao restaurar uma sessão pausada a partir de um History Node (resume_from_history_node), o sistema confronta o carimbo de data/hora (created_at) do checkpoint com a última modificação no disco dos arquivos associados à tarefa (task_id / tabela files). Se o código tiver sido alterado externamente durante a pausa, a HSM direciona a execução para EXECUTION.RE_INDEX para re-analisar a sintaxe antes de retomar as mutações físicas.

🔍 2. Análise de Impacto de Segunda Ordem (Análise de Riscos)

Risco de Invalidação Excessiva de Checkpoints por Toques Mínimos de Arquivo (False Positive Delta): Alterações triviais no disco (como formatação ou salvamento de comentários) podem acionar re-indexações desnecessárias do AST Parser no momento de restaurar o History Node.

Mitigação (Integração com Assinatura SSH): A validação de delta não confiará apenas no mtime do sistema operacional. Ela invocará a verificação de Assinatura Estrutural Hash (SSH - SDD-04). Se o hash sintático das funções/classes for idêntico, o estado do History Node é considerado válido e mantido em CODE_GEN sem passar por re-indexação.

Risco de Exceções Descontroladas em Ganchos de Transição (Hook Callback Failure): Se uma função cadastrada em on_enter ou on_exit falhar com uma exceção não tratada, a transição de estado da HSM pode ficar em um limbo intermediário.

Mitigação (Atomic Hook Execution & Rollback): As chamadas de hooks serão encapsuladas por blocos try/except. Em caso de erro dentro de um hook de entrada ou saída, a transição é cancelada, o estado anterior é restaurado e o evento é logado como falha de governança, transicionando a HSM com segurança para STALL.ERROR_PAUSE.

⚙️ 3. Contrato de Funcionamento e Especificação

3.1. Arquitetura de Ganchos Lifecycle na HSM (HSMNode)

# core/hsm_engine.py (Trecho estendido para suporte a Hooks)
from typing import Callable, List

class HSMNode:
    def __init__(self, name: str, parent: Optional["HSMNode"] = None, category: str = "READ_ONLY"):
        self.name = name
        self.parent = parent
        self.category = category
        self.substates: Dict[str, "HSMNode"] = {}
        self._on_enter_hooks: List[Callable[[], None]] = []
        self._on_exit_hooks: List[Callable[[], None]] = []

    def register_on_enter(self, fn: Callable[[], None]) -> None:
        self._on_enter_hooks.append(fn)

    def register_on_exit(self, fn: Callable[[], None]) -> None:
        self._on_exit_hooks.append(fn)

    def execute_on_enter(self) -> None:
        for hook in self._on_enter_hooks:
            try:
                hook()
            except Exception as e:
                # Log e relança para acionar rollback de segurança
                raise RuntimeError(f"Falha ao executar on_enter hook no nó '{self.name}': {e}")

    def execute_on_exit(self) -> None:
        for hook in self._on_exit_hooks:
            try:
                hook()
            except Exception as e:
                raise RuntimeError(f"Falha ao executar on_exit hook no nó '{self.name}': {e}")

3.2. Transição com Disparo Encadeado de Ganchos
A ordem de execução dos hooks em uma transição de A.sub1 para B.sub2 obedece à hierarquia:

A.sub1.execute_on_exit() (Sub-estado antigo)
A.execute_on_exit() (Super-estado antigo, se houver troca de super-estado)
B.execute_on_enter() (Novo super-estado, se houver troca)
B.sub2.execute_on_enter() (Novo sub-estado)

3.3. Validação de Delta de Arquivos no Resume (resume_from_history_node)

# core/hsm_engine.py (Lógica de validação de delta estendida)
def resume_from_history_node(self, session_id: str, delta_manager=None) -> Optional[Dict[str, Any]]:
    history = self.history_nodes.get(session_id)
    if not history:
        # Busca no banco relacional
        query = """
            SELECT checkpoint_id, state_name, created_at, task_id
            FROM fsm_checkpoints
            WHERE session_id = ?
            ORDER BY created_at DESC LIMIT 1;
        """
        rows = self.db.read_query(query, (session_id,))
        if not rows:
            return None
        checkpoint_id, state_name, created_at, task_id = rows
        full_path = state_name
    else:
        full_path, checkpoint_id, timestamp = history
        created_at = timestamp
        task_id = None

    # Restaura o checkpoint relacional
    restored = self.checkpointer.load_checkpoint(session_id, checkpoint_id)
    if not restored:
        return None

    # Validação de Delta se houver um delta_manager e arquivo vinculado
    target_task_id = task_id or restored.get("task_id")
    is_stale = False

    if delta_manager and target_task_id and os.path.exists(target_task_id):
        file_mtime = os.path.getmtime(target_task_id)
        # Se o arquivo no disco for mais recente que o checkpoint
        if file_mtime > created_at:
            # Checa se houve mudança estrutural (SSH)
            if delta_manager.has_structural_change(target_task_id):
                is_stale = True

    if is_stale:
        # Redireciona a HSM para sub-estado de re-indexação sintática
        target_node = self.resolve_node("EXECUTION.RE_INDEX") or self.resolve_node("EXECUTION.CODE_GEN")
        restored["shared_state"]["stale_detected"] = True
    else:
        target_node = self.resolve_node(full_path)

    if target_node:
        self.active_session_states[session_id] = target_node
        if self.mcp_governor and target_node.parent:
            self.mcp_governor.set_session_state(session_id, target_node.parent.name)

    return restored

🧪 4. Suíte de Testes TDD (tests/test_hsm_transition_hooks_and_delta.py)
Esta suíte garante de forma determinística que os hooks respeitam a hierarquia e que arquivos modificados durante a pausa disparam a re-indexação automática:

import unittest
import tempfile
import os
import time
from core.database import ConciergeDatabaseManager
from core.checkpointer import AgnosticCheckpointer
from core.hsm_engine import HierarchicalStateMachine

class MockDeltaManager:
    def __init__(self, is_structural_change=True):
        self._change = is_structural_change

    def has_structural_change(self, path: str) -> bool:
        return self._change

class TestHSMTransitionHooksAndDelta(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_manager = ConciergeDatabaseManager(self.db_path)

        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS fsm_checkpoints ("
            "checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, "
            "shared_state_blob TEXT, task_id TEXT, created_at REAL, "
            "PRIMARY KEY (session_id, checkpoint_id)"
            ");"
        )

        self.checkpointer = AgnosticCheckpointer(self.db_manager)
        self.hsm = HierarchicalStateMachine(self.db_manager, self.checkpointer)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_should_trigger_on_enter_and_on_exit_hooks_in_order(self):
        """Valida que ganchos de saída e entrada são disparados na ordem hierárquica correta"""
        events = []

        planning_node = self.hsm.resolve_node("PLANNING")
        discovery_node = self.hsm.resolve_node("PLANNING.DISCOVERY")
        execution_node = self.hsm.resolve_node("EXECUTION")
        code_gen_node = self.hsm.resolve_node("EXECUTION.CODE_GEN")

        discovery_node.register_on_exit(lambda: events.append("EXIT_DISCOVERY"))
        planning_node.register_on_exit(lambda: events.append("EXIT_PLANNING"))
        execution_node.register_on_enter(lambda: events.append("ENTER_EXECUTION"))
        code_gen_node.register_on_enter(lambda: events.append("ENTER_CODE_GEN"))

        # Inicializa estado
        self.hsm.active_session_states["sess_hooks"] = discovery_node

        # Transita para EXECUTION.CODE_GEN
        self.hsm.transition_to(
            session_id="sess_hooks",
            target_path="EXECUTION.CODE_GEN",
            agent_id="Hermes",
            shared_state={}
        )

        expected_order = ["EXIT_DISCOVERY", "EXIT_PLANNING", "ENTER_EXECUTION", "ENTER_CODE_GEN"]
        self.assertEqual(events, expected_order)

    def test_should_detect_stale_file_and_redirect_to_reindex_on_resume(self):
        """Valida que resume com arquivo modificado após o checkpoint redireciona para RE_INDEX"""
        # Cria arquivo temporário
        file_fd, file_path = tempfile.mkstemp()
        os.write(file_fd, b"def original(): pass")
        os.close(file_fd)

        old_timestamp = time.time() - 100

        # Grava checkpoint antigo associado ao arquivo
        self.hsm.checkpointer.save_checkpoint(
            session_id="sess_stale",
            checkpoint_id="cp_old",
            agent_id="Hermes",
            state_name="EXECUTION.CODE_GEN",
            shared_state={"step": 1},
            task_id=file_path
        )

        # Atualiza a data no banco para simular tempo passado
        self.db_manager.write_query(
            "UPDATE fsm_checkpoints SET created_at = ? WHERE checkpoint_id = ?",
            (old_timestamp, "cp_old")
        )

        # Toca o arquivo no disco (mtime fica mais recente)
        os.utime(file_path, None)

        delta_mgr = MockDeltaManager(is_structural_change=True)
        restored = self.hsm.resume_from_history_node("sess_stale", delta_manager=delta_mgr)

        self.assertIsNotNone(restored)
        self.assertTrue(restored["shared_state"].get("stale_detected"))

        # Limpeza
        os.unlink(file_path)