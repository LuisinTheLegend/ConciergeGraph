"""
check_brain.py — Diagnosticador de Saúde de Memória v3.8.2
Sincronizado com os parâmetros reais: persistence_path e EmbeddingManager.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
# Imports das camadas sólidas
from storage import SqliteStore, ChromaVectorStore, EmbeddingManager
from ingestion import IngestionManager, ZoomSummarizer
from ingestion.summarizer import LLMAdapter
from core.middleware import GrafoConcierge
from services import JanitorService

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("brain-check")

def run_diagnostic():
    PROJECT_UUID = "test-uuid-001"
    
    logger.info("🧪 [1/4] Inicializando Motores...")
    
    # Âncora dinâmica: tests/ → raiz do projeto
    _project_root = Path(__file__).parent.parent.resolve()
    
    TEST_DIR = _project_root / "_test_brain_tmp"
    TEST_DIR.mkdir(exist_ok=True)
    TEST_FILE = TEST_DIR / "brain_sample.py"

    # 1. SqliteStore (path ancorado na raiz do projeto)
    store = SqliteStore(str(_project_root / "data" / "concierge.db"))
    
    # Garante que o projeto de teste exista no banco de dados
    try:
        store.get_project(PROJECT_UUID)
    except Exception:
        store.create_project(PROJECT_UUID, "brain-check-temp", "teste")
    
    # 2. EmbeddingManager (v3.8.0 - inicializa com tier padrão 'flash')
    embedder = EmbeddingManager() 
    
    # 3. ChromaVectorStore
    vector = ChromaVectorStore(persist_dir=str(_project_root / "data" / "chroma"), embedding_manager=embedder)
    
    # 4. ZoomSummarizer (inicializa com adapter interno padrão)
    llm_model = os.environ.get("GRAFO_LLM_MODEL", "gemini-2.0-flash")
    llm_api_key = os.environ.get("GRAFO_LLM_API_KEY", "")
    llm_base_url = os.environ.get("GRAFO_LLM_BASE_URL", "")
    llm_adapter = LLMAdapter(
        model_name=llm_model,
        api_key=llm_api_key or None,
        base_url=llm_base_url or None,
    )
    summarizer = ZoomSummarizer(llm_adapter=llm_adapter, sqlite_store=store)
    
    # 5. Ingestion & Janitor
    manager = IngestionManager(store, vector, embedder, summarizer)
    janitor = JanitorService(store, vector, manager)

    # Fachada Central GrafoConcierge
    gc = GrafoConcierge(
        sqlite_store=store,
        vector_store=vector,
        embedding_manager=embedder,
        ingestion_manager=manager,
    )

    # --- TESTE 2: PRECISÃO ---
    logger.info("🧪 [2/4] Testando Precisão e Ingestão...")
    content = """
def security_protocol_alpha():
    # Este é um sistema de proteção contra injeção de prompts
    # Utilizamos tags XML para isolar dados brutos
    pass
    """
    TEST_FILE.write_text(content)
    
    # Ingestão do arquivo de teste
    manager.mine(PROJECT_UUID, str(TEST_DIR), auto_tag=True)
    
    # Busca híbrida (Semântica + FTS5)
    query = "Como o sistema se protege contra injeção de prompts?"
    results = gc.hybrid_search(query=query, project_uuid=PROJECT_UUID, top_k=5)
    
    # Enriquece os resultados com dados do SQLite para verificação
    enriched = []
    for r in results:
        try:
            node = store.get_node(r["node_id"])
            enriched.append(node)
        except Exception:
            pass

    found = any("security_protocol_alpha" in str(node.get("label", "")) or 
                "security_protocol_alpha" in str(node.get("summary", "")) 
                for node in enriched)
    if found:
        logger.info("✅ PASS: O sistema localizou a lógica de segurança por conceito!")
    else:
        logger.error("❌ FAIL: O sistema não associou o conceito de segurança ao código.")

    # --- TESTE 3: ZOOM GEAR ---
    logger.info("🧪 [3/4] Gerando Bússola L2 (Zoom Gear)...")
    context = manager.generate_project_context(PROJECT_UUID)
    if context.get("l2_summary"):
        logger.info(f"✅ PASS: Bússola L2 gerada com sucesso.")
        logger.info(f"   Conteúdo: {context['l2_summary'][:100]}...")
    else:
        logger.warning("⚠️ WARN: O resumo L2 não retornou conteúdo (pode ser o limite de tokens).")

    # --- TESTE 4: GC & SINCRONIZAÇÃO ---
    logger.info("🧪 [4/4] Testando Sincronização e Limpeza (GC)...")
    if TEST_FILE.exists(): 
        TEST_FILE.unlink() # Deleta o arquivo físico
    
    # Roda mine para detectar o delta e janitor para limpar
    manager.mine(PROJECT_UUID, str(TEST_DIR))
    report = janitor.run_maintenance(PROJECT_UUID)
    
    # A busca agora deve retornar vazio para este símbolo
    check = gc.hybrid_search(query="security_protocol_alpha", project_uuid=PROJECT_UUID)
    if len(check) == 0:
        logger.info(f"✅ PASS: Arquivo fantasma removido. Órfãos limpos: {report.orphan_vectors_removed}")
    else:
        logger.error("❌ FAIL: O vetor ainda existe no ChromaDB após a exclusão.")
        
    try:
        TEST_DIR.rmdir()
    except Exception:
        pass

    logger.info("\n" + "="*40 + "\nDIAGNÓSTICO v3.8.2 CONCLUÍDO\n" + "="*40)

if __name__ == "__main__":
    if not os.getenv("GRAFO_LLM_API_KEY"):
        logger.error("ERRO: Defina a variável GRAFO_LLM_API_KEY no terminal.")
    else:
        run_diagnostic()