"""
scratch/reproduce_agent_findings.py

Empirical reproduction of findings in:
- agent/run_agent.py (CognitiveAgentRunner)
- agent/agent_prompts.py (DynamicPromptBuilder)
- agents/revisor_critico.py (RevisorCritico)
"""

import asyncio
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath("."))

from core.database import ConciergeDatabaseManager
from core.checkpointer import AgnosticCheckpointer
from core.mcp_governor import MCPToolGovernor
from core.hsm_engine import HierarchicalStateMachine
from agent.run_agent import CognitiveAgentRunner
from agent.agent_prompts import DynamicPromptBuilder
from agents.revisor_critico import RevisorCritico, AuditResult
from core.config import DEFAULT_CONFIG

def setup_hsm_and_runner():
    tmp = tempfile.mktemp(suffix=".db")
    db_mgr = ConciergeDatabaseManager(tmp)
    db_mgr.write_query(
        "CREATE TABLE IF NOT EXISTS files ("
        "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
        ");"
    )
    db_mgr.write_query(
        "CREATE TABLE IF NOT EXISTS fsm_checkpoints ("
        "checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, "
        "shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "PRIMARY KEY (session_id, checkpoint_id)"
        ");"
    )
    cp = AgnosticCheckpointer(db_mgr)
    gov = MCPToolGovernor(default_state="PLANNING")
    hsm = HierarchicalStateMachine(db_mgr, cp, gov)
    runner = CognitiveAgentRunner(hsm_engine=hsm, max_substate_turns=5)
    return hsm, runner

async def test_finding_1_cross_session_turn_pollution():
    print("=" * 70)
    print("TESTE 1: Contaminação de Turnos Multi-Sessão no Circuit Breaker")
    print("=" * 70)
    hsm, runner = setup_hsm_and_runner()
    
    # Sessão 1 inicia e executa 3 passos
    runner.initialize_session("session_1")
    await runner.step("session_1", "step 1")
    await runner.step("session_1", "step 2")
    await runner.step("session_1", "step 3")
    print(f"Sessão 1 executou 3 passos. current_substate_turn_count = {runner.current_substate_turn_count}")

    # Sessão 2 inicia no mesmo runner
    # BUG PARTE A: initialize_session zera o contador global de substate turn count!
    runner.initialize_session("session_2")
    print(f"Sessão 2 foi inicializada. current_substate_turn_count = {runner.current_substate_turn_count} (RESET INDEVIDO!)")

    # Agora Sessão 2 executa 4 passos
    await runner.step("session_2", "step 1")
    await runner.step("session_2", "step 2")
    await runner.step("session_2", "step 3")
    await runner.step("session_2", "step 4")
    print(f"Sessão 2 executou 4 passos. current_substate_turn_count = {runner.current_substate_turn_count}")

    # Sessão 1 executa seu 4º passo real na vida dela.
    # Mas como o contador é compartilhado, 4 + 1 = 5.
    await runner.step("session_1", "step 4")
    print(f"Sessão 1 executou mais 1 passo. current_substate_turn_count = {runner.current_substate_turn_count}")

    # Próximo passo da Sessão 1 (seria o 5º passo) dispara Circuit Breaker porque contador chegou a 6!
    res = await runner.step("session_1", "step 5")
    print(f"Sessão 1 resultado no 5º turno: status='{res.get('status')}', state='{res.get('state')}'")
    
    is_polluted = (res.get("status") == "stalled")
    print(f"-> [CONFIRMADO] Bloqueio indevido por contaminação entre sessões: {is_polluted}\n")
    return is_polluted

async def test_finding_2_prompt_state_desync():
    print("=" * 70)
    print("TESTE 2: Dessincronização entre Prompt e Estado Ativo em step()")
    print("=" * 70)
    hsm, runner = setup_hsm_and_runner()
    runner.initialize_session("sess_trans")
    
    # Chama step com target_transition="EXECUTION.CODE_GEN"
    res = await runner.step(
        "sess_trans",
        user_input="Inicie a codificação",
        target_transition="EXECUTION.CODE_GEN"
    )
    
    active_state = res.get("active_state")
    prompt = res.get("prompt")
    
    print(f"Retorno do step: active_state = '{active_state}'")
    prompt_contains_planning = "[ESTADO ATIVO: PLANNING.DISCOVERY]" in prompt
    prompt_contains_execution = "[ESTADO ATIVO: EXECUTION.CODE_GEN]" in prompt
    print(f"Prompt contém '[ESTADO ATIVO: PLANNING.DISCOVERY]': {prompt_contains_planning}")
    print(f"Prompt contém '[ESTADO ATIVO: EXECUTION.CODE_GEN]': {prompt_contains_execution}")
    
    is_desynced = (active_state == "EXECUTION.CODE_GEN" and prompt_contains_planning and not prompt_contains_execution)
    print(f"-> [CONFIRMADO] Prompt e estado ativo fora de sincronia: {is_desynced}\n")
    return is_desynced

def test_finding_3_contamination_bypass():
    print("=" * 70)
    print("TESTE 3: Bypass na Barreira de Contaminação por Fallback Inseguro")
    print("=" * 70)
    revisor = RevisorCritico(llm_adapter=None)
    
    # Caso 1: privacy_level em minúsculo
    source_lower = {"folder_name": "segredo_corp", "privacy_level": "restricted"}
    target_public = {"folder_name": "repo_aberto", "privacy_level": "PUBLIC"}
    is_safe_lower, reason_lower = revisor.check_contamination(source_lower, target_public)
    print(f"Origem='restricted' (minúsculo) -> Destino='PUBLIC':")
    print(f"   is_safe = {is_safe_lower} (Deveria ser False!)")
    print(f"   reason  = {reason_lower}")
    
    # Caso 2: privacy_level='CONFIDENTIAL'
    source_conf = {"folder_name": "banco_dados_rh", "privacy_level": "CONFIDENTIAL"}
    is_safe_conf, reason_conf = revisor.check_contamination(source_conf, target_public)
    print(f"Origem='CONFIDENTIAL' -> Destino='PUBLIC':")
    print(f"   is_safe = {is_safe_conf} (Deveria ser False!)")
    print(f"   reason  = {reason_conf}")

    is_leaking = (is_safe_lower is True and is_safe_conf is True)
    print(f"-> [CONFIRMADO] Vazamento de dados confidenciais aprovado como seguro: {is_leaking}\n")
    return is_leaking

def test_finding_4_fake_approval_on_crash():
    print("=" * 70)
    print("TESTE 4: Falsa Aprovação de Commit Inválido quando generate_fn Falha")
    print("=" * 70)
    revisor = RevisorCritico(llm_adapter=None)
    
    bad_draft = {
        "phase": "build",
        "technical_changes": "bad",
        "updated_pointers": []
    }
    
    # generate_fn que falha (ex: erro de conexão, modelo indisponível ou assinatura incompatível)
    def broken_generator(reason):
        raise ConnectionError("API do LLM fora do ar durante regeneração!")
    
    result = revisor.audit_with_retry(bad_draft, generate_fn=broken_generator)
    print(f"Commit inválido com generate_fn quebrando na tentativa 1:")
    print(f"   approved      = {result.approved} (Deveria ser False!)")
    print(f"   partial_audit = {result.partial_audit}")
    print(f"   loop_count    = {result.loop_count}")
    print(f"   reason        = {result.reason}")
    
    is_fake_approval = (result.approved is True and result.loop_count == revisor._max_loops)
    print(f"-> [CONFIRMADO] Commit inválido aprovado automaticamente após crash: {is_fake_approval}\n")
    return is_fake_approval

def test_finding_5_rerank_type_mismatch_and_crash():
    print("=" * 70)
    print("TESTE 5: Falha em Rerank (NoneType crash e Type Mismatch)")
    print("=" * 70)
    revisor = RevisorCritico(llm_adapter=None)
    
    # 5.1 Heuristic rerank com score_final: None
    candidates_with_none = [
        {"node_id": 1, "score_final": 0.8},
        {"node_id": 2, "score_final": None}
    ]
    crash_heuristic = False
    try:
        revisor._heuristic_rerank(candidates_with_none)
    except TypeError as e:
        crash_heuristic = True
        print(f"5.1 Crash em _heuristic_rerank quando score_final=None: {e}")

    # 5.2 LLM rerank com node_id string vs int no relevance_map
    class MockLLM:
        def generate(self, prompt, max_tokens=400):
            return '{"evaluations": [{"node_id": 42, "relevance": 0.95}]}'

    revisor_llm = RevisorCritico(llm_adapter=MockLLM())
    candidates_str_id = [
        {"node_id": "42", "score_final": 0.8}  # ID como string
    ]
    res_str = revisor_llm.rerank(candidates_str_id, task_context="test task")
    print(f"5.2 LLM Rerank com candidato node_id='42' (str) e LLM avaliando 42 (int):")
    print(f"    Candidatos aprovados: {res_str}")
    
    dropped_all = (len(res_str) == 0)
    print(f"    Candidato legítimo descartado por incompatibilidade de tipo: {dropped_all}")

    success = crash_heuristic and dropped_all
    print(f"-> [CONFIRMADO] Defeitos em Reranking confirmados: {success}\n")
    return success

async def main():
    f1 = await test_finding_1_cross_session_turn_pollution()
    f2 = await test_finding_2_prompt_state_desync()
    f3 = test_finding_3_contamination_bypass()
    f4 = test_finding_4_fake_approval_on_crash()
    f5 = test_finding_5_rerank_type_mismatch_and_crash()
    
    print("=" * 70)
    print("RESUMO DE REPRODUÇÃO (agent/ e agents/):")
    print(f"Achado 1 (Contaminação Turnos Circuit Breaker): {'REPRODUZIDO' if f1 else 'FALHOU'}")
    print(f"Achado 2 (Dessincronização Prompt-Estado em step): {'REPRODUZIDO' if f2 else 'FALHOU'}")
    print(f"Achado 3 (Bypass Barreira Contaminação): {'REPRODUZIDO' if f3 else 'FALHOU'}")
    print(f"Achado 4 (Aprovação Espúria Commit Inválido): {'REPRODUZIDO' if f4 else 'FALHOU'}")
    print(f"Achado 5 (Defeitos de Tipo e Crash em Reranking): {'REPRODUZIDO' if f5 else 'FALHOU'}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
