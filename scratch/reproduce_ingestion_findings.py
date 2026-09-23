"""
Reprodução empírica dos achados de auditoria em ingestion/
- crawler.py
- parser.py
- summarizer.py
- orchestrator.py
"""
import os
import sys
import shutil
import tempfile
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

from storage import SqliteStore, ChromaVectorStore, EmbeddingManager
from storage.vector_store import EmbeddingTier
from ingestion.crawler import ProjectCrawler, FileCategory
from ingestion.parser import FileParser, ParsedChunk, ChunkType
from ingestion.summarizer import ZoomSummarizer, SummaryResult, ZoomLevel, LLMAdapter
from ingestion.orchestrator import IngestionManager, IngestionResult

class MockEmbedder:
    tier = EmbeddingTier.FLASH
    dimensions = 384
    def embed_batch(self, texts):
        return [[0.1] * 384 for _ in texts]
    def embed(self, text):
        return [0.1] * 384

def test_achado_1_crawler_rename_vanishes():
    """
    Achado 1: find_node_by_hash ignora relative_path.
    Renomear um arquivo (mesmo hash) faz o novo arquivo ser considerado unchanged,
    e o GC apaga o nó antigo -> o arquivo SOME do grafo.
    """
    print("\n" + "="*70)
    print("TESTE ACHADO 1: Renomeação de arquivo causa perda total no grafo (GC False Purge)")
    print("="*70)
    
    tmp_dir = tempfile.mkdtemp(prefix="test_crawler_rename_")
    db_path = os.path.join(tmp_dir, "test.db")
    proj_dir = os.path.join(tmp_dir, "project")
    os.makedirs(proj_dir, exist_ok=True)
    
    store = SqliteStore(db_path)
    proj_uuid = store.create_project("test_rename_proj", "src", "GERAL")["uuid"]
    
    # Cria arquivo inicial a.py
    file_a = os.path.join(proj_dir, "a.py")
    with open(file_a, "w", encoding="utf-8") as f:
        f.write("def calculate_total():\n    return 42\n")
        
    embedder = MockEmbedder()
    vector = ChromaVectorStore(os.path.join(tmp_dir, "chroma"))
    manager = IngestionManager(store, vector, embedder)
    
    # 1. Primeira ingestão
    res1 = manager.mine(proj_uuid, proj_dir)
    nodes1 = store.get_nodes_by_project(proj_uuid)
    nodes1_labels = [n["label"] for n in nodes1 if n.get("type") != "directory"]
    print(f"1ª Ingestão: {len(nodes1_labels)} nós criados: {nodes1_labels}")
    
    # 2. Renomeia a.py para b.py (conteúdo idêntico)
    file_b = os.path.join(proj_dir, "b.py")
    os.rename(file_a, file_b)
    
    # 3. Segunda ingestão
    res2 = manager.mine(proj_uuid, proj_dir)
    nodes2 = store.get_nodes_by_project(proj_uuid)
    nodes2_labels = [n["label"] for n in nodes2 if n.get("type") != "directory"]
    print(f"2ª Ingestão (após rename a.py -> b.py):")
    print(f"  files_processed: {res2.files_processed}, files_skipped: {res2.files_skipped}, files_deleted: {res2.files_deleted}")
    print(f"  Nós sobreviventes no SQLite: {nodes2_labels}")
    
    confirmado = (len(nodes2_labels) == 0)
    print(f"  [CONFIRMADO ACHADO 1]: {confirmado} — O arquivo renomeado b.py NÃO foi ingerido e o nó de a.py foi DELETADO pelo GC!")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return confirmado


def test_achado_2_l0_summaries_discarded():
    """
    Achado 2: _step_summarize gera resumos L0, mas _step_store_sqlite lê chunk.cached_summary (que é None para new_chunks)
    e os resumos L0 retornados NUNCA são salvos nos nós criados no SQLite!
    """
    print("\n" + "="*70)
    print("TESTE ACHADO 2: Resumos L0 gerados pelo LLM são descartados e nodes.summary fica NULL")
    print("="*70)
    
    tmp_dir = tempfile.mkdtemp(prefix="test_l0_discard_")
    db_path = os.path.join(tmp_dir, "test.db")
    proj_dir = os.path.join(tmp_dir, "project")
    os.makedirs(proj_dir, exist_ok=True)
    
    store = SqliteStore(db_path)
    proj_uuid = store.create_project("test_l0_proj", "src", "GERAL")["uuid"]
    
    with open(os.path.join(proj_dir, "math_utils.py"), "w", encoding="utf-8") as f:
        f.write("def add(x, y):\n    return x + y\n")
        
    embedder = MockEmbedder()
    vector = ChromaVectorStore(os.path.join(tmp_dir, "chroma"))
    
    # Mock LLM que devolve JSON com summary
    call_count = 0
    def mock_llm_call(prompt, max_tokens):
        nonlocal call_count
        call_count += 1
        return '{"summary": "Funcao que soma dois valores matematicos", "tags": ["math", "calc"]}'
        
    adapter = LLMAdapter(model_name="mock-flash", call_fn=mock_llm_call)
    summarizer = ZoomSummarizer(llm_adapter=adapter, sqlite_store=store)
    manager = IngestionManager(store, vector, embedder, summarizer=summarizer)
    
    res = manager.mine(proj_uuid, proj_dir)
    print(f"Resumos reportados como gerados pelo IngestionResult: {res.summaries_generated}")
    print(f"Chamadas ao LLM realizadas: {call_count}")
    
    nodes = store.get_nodes_by_project(proj_uuid)
    chunk_nodes = [n for n in nodes if n.get("type") not in ("directory", "project")]
    for cn in chunk_nodes:
        print(f"  Nó: {cn['label']} | summary: {cn.get('summary')}")
        
    all_summaries_none = all(cn.get("summary") is None for cn in chunk_nodes)
    print(f"  [CONFIRMADO ACHADO 2]: {all_summaries_none} — O LLM gerou o resumo, mas nodes.summary no SQLite foi gravado como NULL!")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return all_summaries_none


def test_achado_3_l2_persist_project_name_vs_uuid():
    """
    Achado 3: _persist_l2 chama store.update_project(project_name, summary=...)
    onde project_name é o folder_name e não o UUID, resultando em 0 linhas atualizadas.
    """
    print("\n" + "="*70)
    print("TESTE ACHADO 3: Falha ao persistir L2 Compass por passar folder_name como UUID")
    print("="*70)
    
    tmp_dir = tempfile.mkdtemp(prefix="test_l2_persist_")
    db_path = os.path.join(tmp_dir, "test.db")
    store = SqliteStore(db_path)
    proj_uuid = store.create_project("proj-uuid-real-12345", "MeuProjetoNome", "GERAL")["uuid"]
    
    def mock_llm(prompt, max_tokens):
        return '{"summary": "Visao global do projeto de teste", "tags": ["core"]}'
        
    adapter = LLMAdapter(model_name="mock-flash", call_fn=mock_llm)
    summarizer = ZoomSummarizer(llm_adapter=adapter, sqlite_store=store)
    
    l1_sample = [
        SummaryResult(level=ZoomLevel.L1, summary="Modulo math", source_label="math_mod", relevance_score=1.0)
    ]
    # Invocação como feita em orchestrator.py:883:
    # project_name = project.get("folder_name", project_uuid) -> "MeuProjetoNome"
    l2 = summarizer.summarize_l2(l1_sample, "MeuProjetoNome")
    print(f"L2 retornado pelo summarizer: {l2.summary}")
    
    # Verifica no SQLite se a tabela projects recebeu o summary
    proj_db = store.get_project(proj_uuid)
    print(f"projects.summary no banco para uuid={proj_uuid}: {proj_db.get('summary')}")
    
    confirmado = (proj_db.get("summary") is None)
    print(f"  [CONFIRMADO ACHADO 3]: {confirmado} — store.update_project('MeuProjetoNome') não atualizou a linha com uuid='{proj_uuid}'!")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return confirmado


def test_achado_4_zombie_vectors_on_file_modification():
    """
    Achado 4: cleanup_obsolete_nodes apaga nós no SQLite, mas não apaga vetores no ChromaDB.
    E o Step 7 (GC/verify_sync) só roda se crawl_report.deleted_node_ids não for vazio!
    """
    print("\n" + "="*70)
    print("TESTE ACHADO 4: Vetores zumbis no ChromaDB após modificação de arquivo")
    print("="*70)
    
    tmp_dir = tempfile.mkdtemp(prefix="test_zombie_vec_")
    db_path = os.path.join(tmp_dir, "test.db")
    chroma_dir = os.path.join(tmp_dir, "chroma")
    proj_dir = os.path.join(tmp_dir, "project")
    os.makedirs(proj_dir, exist_ok=True)
    
    store = SqliteStore(db_path)
    proj_uuid = store.create_project("test_zombie_proj", "src", "GERAL")["uuid"]
    
    # Versão 1: arquivo com 2 funções
    fpath = os.path.join(proj_dir, "code.py")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("def func_alpha():\n    pass\n\ndef func_beta():\n    pass\n")
        
    embedder = MockEmbedder()
    vector = ChromaVectorStore(chroma_dir)
    manager = IngestionManager(store, vector, embedder)
    
    manager.mine(proj_uuid, proj_dir)
    
    # Contagem inicial
    nodes_v1 = [n["id"] for n in store.get_nodes_by_project(proj_uuid) if n.get("type") not in ("directory", "project")]
    vec_count_v1 = vector.count()
    print(f"Versão 1: {len(nodes_v1)} nós no SQLite, {vec_count_v1} vetores no Chroma")
    
    # Versão 2: remove func_beta e altera func_alpha
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("def func_alpha_modificada():\n    return 123\n")
        
    res2 = manager.mine(proj_uuid, proj_dir)
    nodes_v2 = [n["id"] for n in store.get_nodes_by_project(proj_uuid) if n.get("type") not in ("directory", "project")]
    vec_count_v2 = vector.count()
    print(f"Versão 2:")
    print(f"  Nós vivos no SQLite: {len(nodes_v2)} (IDs: {nodes_v2})")
    print(f"  Vetores no Chroma: {vec_count_v2}")
    
    # O Chroma acumulou os vetores antigos que foram apagados do SQLite!
    zombies = vec_count_v2 - len(nodes_v2)
    print(f"  Diferença (vetores zumbis sem nó correspondente no SQLite): {zombies}")
    confirmado = (zombies > 0)
    print(f"  [CONFIRMADO ACHADO 4]: {confirmado} — Chroma manteve os vetores antigos de chunks obsoletos!")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return confirmado


def test_achado_5_attribute_error_when_no_summarizer():
    """
    Achado 5: _step_summarize na fase 3 não checa self._summarizer is None antes de chamar
    await self._summarizer.summarize_l0_async(chunk).
    """
    print("\n" + "="*70)
    print("TESTE ACHADO 5: AttributeError em _step_summarize quando self._summarizer is None")
    print("="*70)
    
    tmp_dir = tempfile.mkdtemp(prefix="test_attr_err_")
    db_path = os.path.join(tmp_dir, "test.db")
    store = SqliteStore(db_path)
    embedder = MockEmbedder()
    vector = ChromaVectorStore(os.path.join(tmp_dir, "chroma"))
    
    manager = IngestionManager(store, vector, embedder, summarizer=None)
    
    chunk = ParsedChunk(
        content="x = 1\ny = 2\n",
        armored_content="x = 1",
        chunk_type=ChunkType.FUNCTION,
        chunk_index=0,
        source_file="test.py",
        file_hash="h1",
        category=FileCategory.CODE,
        estimated_tokens=100  # regular chunk (> 50)
    )
    
    result = IngestionResult()
    manager._step_summarize([chunk], result)
    print(f"Erros registrados no result: {result.errors}")
    confirmado = any("NoneType" in str(err) or "AttributeError" in str(err) for err in result.errors)
        
    print(f"  [CONFIRMADO ACHADO 5]: {confirmado} — Falha ao verificar self._summarizer is None causou AttributeError interno!")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return confirmado


def test_achado_6_txt_ignored_by_default():
    """
    Achado 6: crawler ignora *.txt por padrao na camada 1 do GitignoreParser,
    ignorando requirements.txt e docs em .txt.
    """
    print("\n" + "="*70)
    print("TESTE ACHADO 6: Arquivos .txt (ex: requirements.txt) ignorados por padrão")
    print("="*70)
    
    tmp_dir = tempfile.mkdtemp(prefix="test_txt_ignore_")
    proj_dir = os.path.join(tmp_dir, "proj")
    os.makedirs(proj_dir, exist_ok=True)
    
    req_file = os.path.join(proj_dir, "requirements.txt")
    with open(req_file, "w", encoding="utf-8") as f:
        f.write("fastapi>=0.100\npytest\n")
        
    store = SqliteStore(os.path.join(tmp_dir, "test.db"))
    proj_uuid = store.create_project("test_txt", "src", "GERAL")["uuid"]
    crawler = ProjectCrawler(store)
    
    report = crawler.crawl(proj_dir, proj_uuid)
    scanned_rel_paths = [f.relative_path for f in report.new_files]
    print(f"Arquivos escaneados pelo crawler: {scanned_rel_paths}")
    
    ignored = "requirements.txt" not in scanned_rel_paths
    print(f"  [CONFIRMADO ACHADO 6]: {ignored} — requirements.txt foi ignorado por padrão sem haver .gitignore!")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return ignored


def test_achado_7_tag_substring_pollution():
    """
    Achado 7: Substring ingênua gera tags falsas como react para reaction e nextjs para next()
    """
    print("\n" + "="*70)
    print("TESTE ACHADO 7: Poluição de tags por substring ingênua (reaction -> react, next() -> nextjs)")
    print("="*70)
    
    parser = FileParser()
    code_python = """
def handle_reaction(event):
    # Processa reacao e consome iterador com next()
    first_item = next(iter(event.reactions))
    return first_item.total
"""
    tags = parser._detect_tags(code_python, FileCategory.CODE)
    print(f"Código Python com 'reaction' e 'next()':")
    print(f"Tags detectadas: {tags}")
    
    confirmado = ("react" in tags and "nextjs" in tags)
    print(f"  [CONFIRMADO ACHADO 7]: {confirmado} — Código Python puro recebeu tags 'react' e 'nextjs'!")
    return confirmado


def test_achado_8_js_parser_brace_counter_cut():
    """
    Achado 8: _find_block_end_braces quebra em comentários ou strings com chaves,
    ou engole linhas em arrow functions sem chaves.
    """
    print("\n" + "="*70)
    print("TESTE ACHADO 8: Quebra de chunking em JS/TS por contador ingênuo de chaves")
    print("="*70)
    
    parser = FileParser()
    # Caso 1: string com chave fechando prematuramente a função
    js_code = """function getTemplate() {
    const html = "<div class='container'>}</div>";
    const status = "ok";
    return html + status;
}

function secondFunction() {
    return 100;
}
"""
    chunks = parser._parse_javascript(js_code, "app.js", "h_js")
    print(f"Chunks gerados para getTemplate com string contendo '}}':")
    for c in chunks:
        print(f"  - Chunk: {c.symbol_name} ({c.chunk_type.value}) linhas {c.start_line}-{c.end_line}:")
        print(f"    Conteúdo: {repr(c.content)}")
        
    # Verifica se a função foi truncada na linha da string
    chunk_func = next((c for c in chunks if c.symbol_name == "getTemplate"), None)
    truncated = False
    if chunk_func:
        truncated = "return html + status" not in chunk_func.content
        print(f"  Função getTemplate foi truncada antes do return? {truncated}")
        
    print(f"  [CONFIRMADO ACHADO 8]: {truncated} — A chave dentro da string literal '}}</div>' encerrou o bloco da função prematuramente!")
    return truncated


if __name__ == "__main__":
    f1 = test_achado_1_crawler_rename_vanishes()
    f2 = test_achado_2_l0_summaries_discarded()
    f3 = test_achado_3_l2_persist_project_name_vs_uuid()
    f4 = test_achado_4_zombie_vectors_on_file_modification()
    f5 = test_achado_5_attribute_error_when_no_summarizer()
    f6 = test_achado_6_txt_ignored_by_default()
    f7 = test_achado_7_tag_substring_pollution()
    f8 = test_achado_8_js_parser_brace_counter_cut()
    
    print("\n" + "="*70)
    print(f"RESUMO DOS ACHADOS: F1={f1}, F2={f2}, F3={f3}, F4={f4}, F5={f5}, F6={f6}, F7={f7}, F8={f8}")
    print("="*70)
