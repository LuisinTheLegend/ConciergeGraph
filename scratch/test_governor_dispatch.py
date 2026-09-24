import asyncio
import os
import sys
import tempfile
sys.path.insert(0, os.path.abspath("."))

from core.mcp_governor import MCPToolGovernor, SecurityException
from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore
class MockEmbedder:
    def embed_text(self, text):
        return [0.1] * 384
    def embed_batch(self, texts):
        return [[0.1] * 384 for _ in texts]
    def get_dimension(self):
        return 384
from interface.mcp_server import GrafoConciergeServer
from core.middleware import GrafoConcierge

async def run_investigation():
    tmp_dir = tempfile.mkdtemp(prefix="test_gov_")
    db_path = os.path.join(tmp_dir, "test.db")
    chroma_dir = os.path.join(tmp_dir, "chroma")
    
    store = SqliteStore(db_path)
    vector = ChromaVectorStore(chroma_dir)
    embedder = MockEmbedder()
    
    from ingestion.orchestrator import IngestionManager
    im = IngestionManager(sqlite_store=store, vector_store=vector, embedding_manager=embedder)
    
    gc = GrafoConcierge(
        sqlite_store=store,
        vector_store=vector,
        embedding_manager=embedder,
        ingestion_manager=im,
    )
    
    # 1. Initialize Server
    server = GrafoConciergeServer(concierge=gc, janitor=None)
    
    print("=" * 70)
    print("1. ESTADO INICIAL DO GOVERNOR NO SERVIDOR")
    print("=" * 70)
    print(f"Default state configurado: {server._governor.default_state}")
    print(f"Estado da sessao 'default': {server._governor.get_session_state('default')}")
    print(f"Sessoes ativas no governor: {server._governor.sessions_state}")
    
    print("\n" + "=" * 70)
    print("2. LISTAGEM DE FERRAMENTAS (list_tools)")
    print("=" * 70)
    # Como cliente MCP real (que chama list_tools sem argumentos)
    all_tools = await server._mcp.list_tools()
    print(f"Total de ferramentas retornadas por list_tools() sem session_id: {len(all_tools)}")
    
    # Se passasse session_id="default" (com estado default EXECUTION)
    gov_tools_exec = await server._mcp.list_tools(session_id="default")
    print(f"Ferramentas retornadas por list_tools(session_id='default') em EXECUTION: {len(gov_tools_exec)}")
    
    print("\n" + "=" * 70)
    print("3. TESTE DE DISPATCH REAL: ESTADO 'EXECUTION' (DEFAULT)")
    print("=" * 70)
    # No estado EXECUTION, ferramentas DANGEROUS devem ser bloqueadas se o governor funcionar?
    # Classification de reset_collection: DANGEROUS
    # Execution allowed_categories: ['READ_ONLY', 'LOCAL_MUTATION']
    print(f"Categoria de 'reset_collection': {server._governor.TOOL_CLASSIFICATION.get('reset_collection')}")
    print(f"Permitido em EXECUTION? {'DANGEROUS' in server._governor.TOOL_DISCLOSURE_MATRIX['EXECUTION']['allowed_categories']}")
    
    try:
        # Chamada via mcp.call_tool (o dispatcher interno do FastMCP)
        res = await server._mcp.call_tool("reset_collection", {})
        print("RESULTADO de reset_collection em EXECUTION: EXECUTOU NORMALMENTE! (Nao bloqueou!)")
        print(f"Retorno: {res}")
    except SecurityException as e:
        print(f"RESULTADO: BLOQUEADO pelo SecurityException: {e}")
    except Exception as e:
        print(f"RESULTADO: Outra excecao: {type(e).__name__}: {e}")
        
    print("\n" + "=" * 70)
    print("4. MUDANCA DE ESTADO VIA concierge_set_state('PLANNING')")
    print("=" * 70)
    # Chama a ferramenta concierge_set_state
    set_res = await server._mcp.call_tool("concierge_set_state", {"state_name": "PLANNING"})
    print(f"Retorno de concierge_set_state: {set_res}")
    print(f"Estado de 'default' apos set_state: {server._governor.get_session_state('default')}")
    
    print("\n" + "=" * 70)
    print("5. TESTE DE DISPATCH REAL: ESTADO 'PLANNING'")
    print("=" * 70)
    # Em PLANNING, categorias permitidas: ['READ_ONLY']
    # concierge_mine é LOCAL_MUTATION. Deve ser bloqueado?
    print(f"Categoria de 'concierge_mine': {server._governor.TOOL_CLASSIFICATION.get('concierge_mine')}")
    try:
        res = await server._mcp.call_tool("concierge_mine", {"project_uuid": "p1", "source_path": "."})
        print("RESULTADO de concierge_mine em PLANNING: EXECUTOU! (Nao bloqueou!)")
    except SecurityException as e:
        print(f"RESULTADO: BLOQUEADO pelo SecurityException: {e}")
    except Exception as e:
        print(f"RESULTADO: Outra excecao: {type(e).__name__}: {e}")

    # reset_collection é DANGEROUS. Deve ser bloqueado?
    try:
        res = await server._mcp.call_tool("reset_collection", {})
        print("RESULTADO de reset_collection em PLANNING: EXECUTOU! (Nao bloqueou!)")
    except SecurityException as e:
        print(f"RESULTADO: BLOQUEADO pelo SecurityException: {e}")
    except Exception as e:
        print(f"RESULTADO: Outra excecao: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("6. BYPASS DE SESSION_ID: SESSAO CUSTOMIZADA VS DEFAULT")
    print("=" * 70)
    # Se o agente seta estado em session_id="agente_1"
    set_res2 = await server._mcp.call_tool("concierge_set_state", {"state_name": "PLANNING", "session_id": "agente_1"})
    print(f"Estado de 'agente_1': {server._governor.get_session_state('agente_1')}")
    print(f"Estado de 'default': {server._governor.get_session_state('default')}")
    
    # Agora chama uma ferramenta que NAO tem session_id na assinatura (ex: reset_collection)
    # O agente mandou arguments sem session_id
    try:
        res = await server._mcp.call_tool("reset_collection", {})
        print("Chamada a reset_collection({{}}) -> consultou session_id: 'default'!")
    except SecurityException as e:
        print(f"Chamada a reset_collection({{}}) -> BLOQUEADA: {e}")
    except Exception as e:
        print(f"Excecao: {e}")

    print("\n" + "=" * 70)
    print("8. DEMONSTRACAO DE BYPASS REAL: AGENTE EM PLANNING DESTROI BASE VETORIAL")
    print("=" * 70)
    # Suponha que o agente atua em 'agent_session_1' cujo estado é restrito a PLANNING:
    await server._mcp.call_tool("concierge_set_state", {"state_name": "PLANNING", "session_id": "agent_session_1"})
    print(f"Estado de 'agent_session_1': {server._governor.get_session_state('agent_session_1')}")
    
    # 1. Tentativa legitima do agente em sua sessao: bloqueada
    try:
        await server._mcp.call_tool("reset_collection", {"session_id": "agent_session_1"})
        print("FALHA: reset_collection deveria ter sido bloqueado!")
    except SecurityException as e:
        print(f"Chamada com session_id='agent_session_1' -> Bloqueada corretamente: {e}")
        
    # 2. Bypass: O agente invoca concierge_set_state para uma session_id efêmera 'bypass_token'
    await server._mcp.call_tool("concierge_set_state", {"state_name": "MAINTENANCE", "session_id": "bypass_token"})
    print("Agente registrou 'bypass_token' como MAINTENANCE via concierge_set_state (READ_ONLY).")
    
    # 3. O agente invoca reset_collection injetando 'bypass_token' nos argumentos JSON-RPC:
    res_bypass = await server._mcp.call_tool("reset_collection", {"session_id": "bypass_token"})
    print(f"RESULTADO DO BYPASS: reset_collection EXECUTADA COM SUCESSO! -> {res_bypass}")
    print("Vulnerabilidade comprovada: FastMCP descartou session_id e executou a operacao DANGEROUS!")

if __name__ == "__main__":
    asyncio.run(run_investigation())
