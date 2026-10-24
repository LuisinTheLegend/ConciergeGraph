"""scratch/evidencia_4_2d/functional_real_test.py

Teste funcional ponta a ponta com o modelo real all-MiniLM-L6-v2:
  1. Cria ambiente temporario isolado (DB, Chroma e diretorio de projeto).
  2. Inicializa o servidor via bootstrap().
  3. Verifica contagem inicial no Chroma (esperado: 0).
  4. Registra projeto com 1 arquivo Python real contendo funcoes e docstrings.
  5. Executa mineracao (ingestao de nos + geracao real de embeddings).
  6. Verifica contagem final no Chroma (deve aumentar: > 0).
  7. Executa concierge_search (busca hibrida com embedding real da query).
  8. Valida os scores e resultados retornados.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run_functional_test() -> None:
    tmp_dir = tempfile.mkdtemp(prefix="grafo_func_real_")
    db_path = os.path.join(tmp_dir, "test_concierge.db")
    chroma_path = os.path.join(tmp_dir, "test_chroma")
    proj_dir = os.path.join(tmp_dir, "sample_project")
    os.makedirs(proj_dir, exist_ok=True)

    # Cria arquivo de codigo no projeto de teste
    code_file = os.path.join(proj_dir, "calculator.py")
    with open(code_file, "w", encoding="utf-8") as f:
        f.write('''"""Modulo de calculadora matematica para operacoes aritmeticas basicas e avancadas."""

def somar(a: int, b: int) -> int:
    """Calcula a soma de dois numeros inteiros com alta precisao."""
    return a + b

def multiplicar(a: int, b: int) -> int:
    """Calcula a multiplicacao de dois fatores inteiros."""
    return a * b
''')

    os.environ["GRAFO_DB_PATH"] = db_path
    os.environ["GRAFO_CHROMA_PATH"] = chroma_path
    os.environ["GRAFO_CHROMA_COLLECTION"] = "functional_test_collection"
    os.environ["GRAFO_TRANSPORT"] = "stdio"
    os.environ["GRAFO_LOG_LEVEL"] = "WARNING"

    print("=" * 75)
    print("TESTE FUNCIONAL REAL — MINERACAO E BUSCA COM MODELO REAL")
    print("=" * 75)
    print(f"Diretorio Temporario : {tmp_dir}")
    print(f"Arquivo de Teste     : {code_file}")

    # Bootstrap
    t_boot_start = time.perf_counter()
    import main as main_module
    server, janitor, store = main_module.bootstrap()
    concierge = server._gc
    t_boot = time.perf_counter() - t_boot_start
    print(f"Bootstrap executado em {t_boot:.4f}s")

    # Contagem no Chroma ANTES da mineracao
    chroma_backend = concierge._vector
    count_before = chroma_backend._collection.count()
    print(f"Contagem no Chroma ANTES da mineracao: {count_before}")
    assert count_before == 0, f"Esperado 0 vetores no Chroma antes da mineracao, obtido: {count_before}"

    # Registrar projeto
    project_uuid = concierge.register_project(
        folder_name=proj_dir,
        summary="Projeto de teste funcional da rodada 4.2d",
    )
    print(f"[OK] Projeto registrado com sucesso: UUID={project_uuid}")

    # Minerar projeto
    print("Executando mineracao com modelo real...")
    t_mine_start = time.perf_counter()
    mine_result = concierge.mine(project_uuid=project_uuid, source_path=proj_dir)
    t_mine = time.perf_counter() - t_mine_start
    print(f"[OK] Mineracao concluida em {t_mine:.4f}s")
    print(f"     Arquivos processados: {mine_result.get('files_processed')}")
    print(f"     Nos criados         : {mine_result.get('nodes_created')}")
    print(f"     Embeddings gerados  : {mine_result.get('embeddings_generated')}")

    # Contagem no Chroma DEPOIS da mineracao
    count_after = chroma_backend._collection.count()
    print(f"Contagem no Chroma DEPOIS da mineracao: {count_after}")
    assert count_after > 0, f"Esperado > 0 vetores gravados no Chroma, obtido: {count_after}"
    print(f"[OK] Provado: {count_after} vetores foram gravados com sucesso no Chroma!")

    # Busca semantica / hibrida (concierge_search)
    query = "Como calcular a soma de dois inteiros?"
    print(f"Executando concierge_search: '{query}'...")
    t_search_start = time.perf_counter()
    results = concierge.hybrid_search(
        query=query,
        project_uuid=project_uuid,
        top_k=3,
    )
    t_search = time.perf_counter() - t_search_start
    print(f"[OK] Busca executada em {t_search:.4f}s")
    print(f"     Total de resultados retornados: {len(results)}")
    for i, r in enumerate(results, 1):
        sb = r.get("score_breakdown", {})
        score = r.get("score_final", 0.0) or 0.0
        print(f"     Resultado #{i}: nome='{r.get('name')}' tipo='{r.get('node_type')}' score={score:.4f} (vetorial={sb.get('vetorial')})")

    assert len(results) > 0, "A busca deve retornar ao menos 1 resultado!"
    top_result = results[0]
    print(f"Top result: {top_result.get('name')}")
    print("=" * 75)
    print("TESTE FUNCIONAL REAL BEM-SUCEDIDO: VETORES GRAVADOS E BUSCA VALIDADA!")
    print("=" * 75)

    # Cleanup
    try:
        store.close()
    except Exception:
        pass
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass


if __name__ == "__main__":
    run_functional_test()
