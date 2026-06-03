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
from services import JanitorService

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("brain-check")

def run_diagnostic():
    PROJECT_UUID = "test-uuid-001"
    TEST_FILE = Path("brain_sample.py")
    
    logger.info("🧪 [1/4] Inicializando Motores...")
    
    # 1. SqliteStore (usa path padrão se omitido, mas passamos para ser explícitos)
    store = SqliteStore("data/concierge.db")
    
    # 2. EmbeddingManager (v3.8.0 - inicializa com tier padrão 'flash')
    embedder = EmbeddingManager() 
    
    # 3. ChromaVectorStore (O parâmetro correto é persistence_path)
    vector = ChromaVectorStore(persistence_path="data/chroma", embedding_manager=embedder)
    
    # 4. ZoomSummarizer (inicializa com adapter interno padrão)
    summarizer = ZoomSummarizer()
    
    # 5. Ingestion & Janitor
    manager = IngestionManager(store, vector, embedder, summarizer)
    janitor = JanitorService(store, vector, manager)

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
    manager.mine(PROJECT_UUID, ".", auto_tag=True)
    
    # Busca híbrida (Semântica + FTS5)
    query = "Como o sistema se protege contra injeção de prompts?"
    results = vector.hybrid_search(query, PROJECT_UUID, limit=5)
    
    found = any("security_protocol_alpha" in str(r.get('metadata', '')) for r in results)
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
    manager.mine(PROJECT_UUID, ".")
    report = janitor.run_maintenance(PROJECT_UUID)
    
    # A busca agora deve retornar vazio para este símbolo
    check = vector.hybrid_search("security_protocol_alpha", PROJECT_UUID)
    if len(check) == 0:
        logger.info(f"✅ PASS: Arquivo fantasma removido. Órfãos limpos: {report.orphans_removed}")
    else:
        logger.error("❌ FAIL: O vetor ainda existe no ChromaDB após a exclusão.")

    logger.info("\n" + "="*40 + "\nDIAGNÓSTICO v3.8.2 CONCLUÍDO\n" + "="*40)

if __name__ == "__main__":
    if not os.getenv("GRAFO_LLM_API_KEY"):
        logger.error("ERRO: Defina a variável GRAFO_LLM_API_KEY no terminal.")
    else:
        run_diagnostic()