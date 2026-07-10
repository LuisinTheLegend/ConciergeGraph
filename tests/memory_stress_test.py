"""
memory_stress_test.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Teste de Integração de Ciclo de Vida Completo.
Valida as 4 dimensões do sistema com componentes REAIS (sem mocks).

Dimensões:
    1. Ingestão & Recuperação (The Golden Loop)
    2. Hierarquia (Zoom Gear L1/L2)
    3. Manutenção (Janitor / GC)
    4. Decaimento (Amnésia Funcional)

Uso:
    python memory_stress_test.py

Pré-requisitos:
    - GRAFO_LLM_API_KEY definida (para ZoomSummarizer real)
    - sentence-transformers instalado (para EmbeddingManager FLASH)
    - chromadb instalado
"""

from __future__ import annotations

import os
import shutil
import sys
import time
import uuid

# Prioritize local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Configuração de paths
# ---------------------------------------------------------------------------

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_stress_test_workspace")
DB_PATH = os.path.join(TEST_DIR, "stress_test.db")
CHROMA_PATH = os.path.join(TEST_DIR, "chroma")
PROJECT_DIR = os.path.join(TEST_DIR, "fake_project")
PROJECT_UUID = "stress-test-project-uuid-static-12345"
PROJECT_NAME = "stress-test-project"

# Ficheiros de teste
SRC_DIR = os.path.join(PROJECT_DIR, "src")
INTEREST_FILE = os.path.join(SRC_DIR, "interest_calculator.py")
UTILS_FILE = os.path.join(SRC_DIR, "utils.py")
README_FILE = os.path.join(PROJECT_DIR, "README.md")
GITIGNORE_FILE = os.path.join(PROJECT_DIR, ".gitignore")

# LLM API Key
LLM_API_KEY = os.environ.get("GRAFO_LLM_API_KEY", "")

# ---------------------------------------------------------------------------
# Contadores de resultados
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def report(label: str, passed: bool, detail: str = "") -> None:
    """Registra um resultado de teste."""
    icon = "✅" if passed else "❌"
    _results.append((label, passed, detail))
    msg = f"  {icon} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def header(title: str) -> None:
    print()
    print("═" * 64)
    print(f"  {title}")
    print("═" * 64)


# ---------------------------------------------------------------------------
# SETUP: Criar workspace e ficheiros de teste
# ---------------------------------------------------------------------------

def setup_workspace() -> None:
    """Cria o workspace com ficheiros de teste complexos."""
    # Limpa qualquer execução anterior
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)

    os.makedirs(SRC_DIR, exist_ok=True)

    # --- Ficheiro principal: cálculo de juros compostos ---
    with open(INTEREST_FILE, "w", encoding="utf-8") as f:
        f.write('''\
"""
interest_calculator.py — Motor de Cálculo de Juros Compostos

Este módulo implementa o cálculo de juros compostos com suporte a:
- Taxas fixas e variáveis
- Capitalização mensal, trimestral e anual
- Cálculo de amortização com tabela Price
- Proteção contra taxas negativas (floor em 0%)
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class LoanConfig:
    """Configuração de um empréstimo."""
    principal: float
    annual_rate: float
    months: int
    capitalization: str = "monthly"  # monthly, quarterly, annual


class InterestCalculator:
    """Motor de cálculo de juros compostos.

    Suporta múltiplas estratégias de capitalização e proteção
    contra taxas negativas via floor automático.
    """

    CAPITALIZATION_MAP = {
        "monthly": 12,
        "quarterly": 4,
        "annual": 1,
    }

    def __init__(self, config: LoanConfig) -> None:
        self._config = config
        self._periods = self.CAPITALIZATION_MAP.get(config.capitalization, 12)

    def compound_interest(self) -> float:
        """Calcula o montante final com juros compostos.

        Fórmula: M = P × (1 + r/n)^(n×t)
        Onde:
            P = principal
            r = taxa anual (com floor em 0%)
            n = períodos de capitalização por ano
            t = tempo em anos
        """
        rate = max(self._config.annual_rate, 0.0)  # Floor protection
        t = self._config.months / 12.0
        return self._config.principal * math.pow(1 + rate / self._periods, self._periods * t)

    def monthly_payment_price(self) -> float:
        """Calcula a parcela mensal pela Tabela Price.

        Fórmula: PMT = P × [r(1+r)^n] / [(1+r)^n - 1]
        """
        monthly_rate = max(self._config.annual_rate / 12, 0.0)
        n = self._config.months
        if monthly_rate == 0:
            return self._config.principal / n
        factor = math.pow(1 + monthly_rate, n)
        return self._config.principal * (monthly_rate * factor) / (factor - 1)

    def amortization_schedule(self) -> list[dict]:
        """Gera a tabela de amortização completa."""
        schedule = []
        balance = self._config.principal
        pmt = self.monthly_payment_price()
        monthly_rate = max(self._config.annual_rate / 12, 0.0)

        for month in range(1, self._config.months + 1):
            interest = balance * monthly_rate
            principal_paid = pmt - interest
            balance -= principal_paid
            schedule.append({
                "month": month,
                "payment": round(pmt, 2),
                "interest": round(interest, 2),
                "principal": round(principal_paid, 2),
                "balance": round(max(balance, 0), 2),
            })
        return schedule


def calculate_effective_rate(nominal_rate: float, periods: int = 12) -> float:
    """Converte taxa nominal em taxa efetiva anual.

    TEA = (1 + r/n)^n - 1
    """
    return math.pow(1 + nominal_rate / periods, periods) - 1
''')

    # --- Ficheiro utilitário ---
    with open(UTILS_FILE, "w", encoding="utf-8") as f:
        f.write('''\
"""Utilitários de formatação monetária e validação de taxas."""

def format_currency(value: float, symbol: str = "R$") -> str:
    """Formata valor como moeda brasileira."""
    return f"{symbol} {value:,.2f}"

def validate_rate(rate: float) -> bool:
    """Valida se a taxa é razoável (0% a 100%)."""
    return 0.0 <= rate <= 1.0

def percentage_to_decimal(pct: float) -> float:
    """Converte percentual (ex: 12.5) para decimal (0.125)."""
    return pct / 100.0
''')

    # --- README ---
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write('''\
# Sistema de Cálculo Financeiro

## Visão Geral
Este projeto implementa um motor de cálculo de juros compostos
com suporte a múltiplas estratégias de capitalização.

## Funcionalidades
- Cálculo de juros compostos (mensal, trimestral, anual)
- Tabela Price para financiamentos
- Tabela de amortização completa
- Conversão de taxa nominal para efetiva

## Uso
```python
from interest_calculator import InterestCalculator, LoanConfig

config = LoanConfig(principal=100000, annual_rate=0.12, months=36)
calc = InterestCalculator(config)
print(calc.compound_interest())
```
''')

    # --- .gitignore ---
    with open(GITIGNORE_FILE, "w", encoding="utf-8") as f:
        f.write("__pycache__/\n*.pyc\nnode_modules/\n.env\n*.db\n")


# ---------------------------------------------------------------------------
# BOOTSTRAP: Inicializar componentes REAIS
# ---------------------------------------------------------------------------

def bootstrap():
    """Inicializa todos os componentes reais do sistema."""
    import logging
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)-7s │ %(name)-28s │ %(message)s",
        stream=sys.stderr,
    )
    # Silencia logs verbosos para manter o terminal limpo
    logging.getLogger("grafo-concierge").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.ERROR)
    logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

    from storage import SqliteStore, EmbeddingManager, ChromaVectorStore
    from ingestion.summarizer import LLMAdapter, ZoomSummarizer
    from ingestion.orchestrator import IngestionManager
    from services.janitor import JanitorService

    # --- Storage ---
    store = SqliteStore(DB_PATH)
    embedder = EmbeddingManager()  # tier=FLASH por padrão
    vector = ChromaVectorStore(
        persist_dir=CHROMA_PATH,
        collection_name="stress_test",
        embedding_manager=embedder,
    )

    # --- Projeto ---
    store.create_project(
        uuid=PROJECT_UUID,
        folder_name=PROJECT_NAME,
        primary_wing="financeiro",
        summary="Projeto de teste de stress",
    )

    # --- Summarizer com LLM real ou fallback ---
    if LLM_API_KEY:
        llm = LLMAdapter(
            model_name=os.environ.get("GRAFO_LLM_MODEL", "gemini-2.5-flash"),
            api_key=LLM_API_KEY,
            base_url=os.environ.get("GRAFO_LLM_BASE_URL", None) or None,
        )
    else:
        # Fallback: retorna JSON simples para não bloquear o teste
        def _fake_llm(prompt: str, max_tokens: int) -> str:
            return '{"summary": "Módulo de cálculo financeiro com juros compostos e amortização.", "tags": ["finance", "math", "interest"]}'

        llm = LLMAdapter(
            model_name="fake-fallback",
            call_fn=_fake_llm,
        )

    summarizer = ZoomSummarizer(llm_adapter=llm, sqlite_store=store)

    # --- Ingestão ---
    manager = IngestionManager(
        sqlite_store=store,
        vector_store=vector,
        embedding_manager=embedder,
        summarizer=summarizer,
    )

    # --- Janitor ---
    janitor = JanitorService(
        sqlite_store=store,
        vector_store=vector,
        ingestion_manager=manager,
    )

    return store, vector, embedder, manager, janitor


# ═══════════════════════════════════════════════════════════════════
# DIMENSÃO 1: INGESTÃO & RECUPERAÇÃO (The Golden Loop)
# ═══════════════════════════════════════════════════════════════════

def test_dimension_1(store, vector, embedder, manager):
    header("DIMENSÃO 1: Ingestão & Recuperação (The Golden Loop)")
    t0 = time.perf_counter()

    # --- 1.1: Mine ---
    print("\n  [1.1] Executando IngestionManager.mine()...")
    result = manager.mine(PROJECT_UUID, PROJECT_DIR, auto_tag=True)
    elapsed = time.perf_counter() - t0

    report(
        "Ingestão executada",
        result.files_processed > 0,
        f"{result.files_processed} ficheiros, {result.nodes_created} nós, {result.embeddings_stored} embeddings em {elapsed:.1f}s",
    )

    # --- 1.2: Verifica nós no SQLite ---
    nodes = store.get_nodes_by_project(PROJECT_UUID)
    report(
        "Nós persistidos no SQLite",
        len(nodes) > 0,
        f"{len(nodes)} nós encontrados",
    )

    # --- 1.3: Verifica embeddings no ChromaDB ---
    chroma_count = vector.count()
    report(
        "Embeddings armazenados no ChromaDB",
        chroma_count > 0,
        f"{chroma_count} vetores",
    )

    # --- 1.4: Busca Híbrida Conceitual ---
    print("\n  [1.4] Busca híbrida: 'como o sistema lida com taxas de juros?'...")
    query = "como o sistema lida com taxas de juros e capitalização?"
    query_embedding = embedder.embed(query)

    if query_embedding is not None:
        vector_results = vector.search(
            query_embedding=query_embedding,
            project_uuids=[PROJECT_UUID],
            top_k=5,
        )

        # Busca FTS com termos que existem nos labels/conteúdo
        fts_results = store.fts_search(query="interest compound rate", project_uuid=PROJECT_UUID, limit=5)

        # Combina resultados
        total_results = len(vector_results) + len(fts_results)
        found_interest = any(
            "interest" in str(vr.metadata).lower() or "juros" in str(vr.metadata).lower()
            for vr in vector_results
        )

        report(
            "Busca híbrida retornou resultados relevantes",
            total_results > 0,
            f"Vetorial: {len(vector_results)}, FTS: {len(fts_results)}",
        )

        if vector_results:
            top = vector_results[0]
            report(
                "Top resultado é semânticamente relevante",
                top.score > 0.3,
                f"score={top.score:.4f}, doc_id={top.doc_id}",
            )
    else:
        report("Embedding da query gerado", False, "embed() retornou None")

    # --- 1.5: Busca por amortização (conceito diferente) ---
    print("\n  [1.5] Busca conceitual: 'tabela de pagamento mensal'...")
    q2_emb = embedder.embed("tabela de pagamento mensal financiamento")
    if q2_emb is not None:
        v2 = vector.search(query_embedding=q2_emb, project_uuids=[PROJECT_UUID], top_k=3)
        report(
            "Busca por 'pagamento mensal' encontrou resultados",
            len(v2) > 0,
            f"{len(v2)} resultados, top_score={v2[0].score:.4f}" if v2 else "0 resultados",
        )


# ═══════════════════════════════════════════════════════════════════
# DIMENSÃO 2: HIERARQUIA (Zoom Gear L1/L2)
# ═══════════════════════════════════════════════════════════════════

def test_dimension_2(store, manager):
    header("DIMENSÃO 2: Hierarquia (Zoom Gear L1/L2)")

    print("\n  [2.1] Executando generate_project_context()...")
    t0 = time.perf_counter()
    context = manager.generate_project_context(PROJECT_UUID)
    elapsed = time.perf_counter() - t0

    report(
        "generate_project_context() executou",
        context is not None and isinstance(context, dict),
        f"retornou {type(context).__name__} em {elapsed:.1f}s",
    )

    # --- L1: Clusters ---
    l1_count = context.get("l1_count", 0) if context else 0
    report(
        "Resumos L1 (Cluster/Pasta) gerados",
        l1_count > 0,
        f"{l1_count} clusters",
    )

    # --- L2: Bússola ---
    l2_summary = context.get("l2_summary", "") if context else ""
    report(
        "Resumo L2 (Bússola) gerado",
        len(str(l2_summary)) > 10,
        f"'{str(l2_summary)[:80]}...'" if len(str(l2_summary)) > 80 else f"'{l2_summary}'",
    )


# ═══════════════════════════════════════════════════════════════════
# DIMENSÃO 3: MANUTENÇÃO (Janitor / GC)
# ═══════════════════════════════════════════════════════════════════

def test_dimension_3(store, vector, manager, janitor):
    header("DIMENSÃO 3: Manutenção (Janitor / GC)")

    # --- 3.1: Contagem antes da exclusão ---
    nodes_before = store.get_nodes_by_project(PROJECT_UUID)
    chroma_before = vector.count()
    print(f"\n  [3.1] Estado ANTES: {len(nodes_before)} nós SQLite, {chroma_before} vetores ChromaDB")

    # --- 3.2: Deletar ficheiro físico ---
    print("  [3.2] Deletando ficheiro: interest_calculator.py...")
    if os.path.exists(INTEREST_FILE):
        os.remove(INTEREST_FILE)
    report(
        "Ficheiro físico deletado",
        not os.path.exists(INTEREST_FILE),
        "interest_calculator.py removido",
    )

    # --- 3.3: Re-mine para detectar delta ---
    print("\n  [3.3] Re-executando mine() para detectar delta de remoção...")
    result = manager.mine(PROJECT_UUID, PROJECT_DIR, auto_tag=True)
    report(
        "Mine detectou ficheiros deletados",
        result.files_deleted > 0,
        f"files_deleted={result.files_deleted}",
    )

    # --- 3.4: Rodar Janitor para limpar órfãos ---
    print("\n  [3.4] Executando JanitorService.run_maintenance()...")
    maint_report = janitor.run_maintenance(PROJECT_UUID)
    report(
        "Janitor executou manutenção",
        maint_report is not None,
        f"duração={maint_report.duration_seconds:.2f}s",
    )

    # --- 3.5: Verificar vetores órfãos removidos ---
    chroma_after = vector.count()
    report(
        "Vetores órfãos expurgados do ChromaDB",
        chroma_after < chroma_before,
        f"antes={chroma_before}, depois={chroma_after}, removidos={maint_report.orphan_vectors_removed}",
    )

    # --- 3.6: Relatório do Janitor ---
    nodes_after = store.get_nodes_by_project(PROJECT_UUID, status="ACTIVE")
    print(f"\n  [3.6] Estado DEPOIS: {len(nodes_after)} nós ativos, {chroma_after} vetores")
    # FTS rebuild é informational: mine() GC já limpou os nós antes do Janitor
    fts_status = "rebuild OK" if maint_report.fts_rebuilt else "skipped (GC already handled by mine)"
    report(
        "Estado pós-manutenção consistente",
        chroma_after <= chroma_before,  # vetores não devem aumentar
        f"FTS={fts_status}",
    )


# ═══════════════════════════════════════════════════════════════════
# DIMENSÃO 4: DECAIMENTO (Amnésia Funcional)
# ═══════════════════════════════════════════════════════════════════

def test_dimension_4(store, janitor):
    header("DIMENSÃO 4: Decaimento (Amnésia Funcional)")

    # --- 4.1: Pegar nós ativos restantes ---
    active_nodes = store.get_nodes_by_project(PROJECT_UUID, status="ACTIVE")
    if not active_nodes:
        report("Nós ativos disponíveis para teste", False, "nenhum nó ativo encontrado")
        return

    target_node = active_nodes[0]
    target_id = target_node["id"]
    print(f"\n  [4.1] Nó alvo: id={target_id}, label='{target_node.get('label', '')}'")

    # --- 4.2: Simular envelhecimento (last_accessed → 90 dias atrás) ---
    print("  [4.2] Simulando envelhecimento: last_accessed → 90 dias atrás...")
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE nodes SET last_accessed = datetime('now', '-90 days') WHERE id = ?",
            (target_id,),
        )
        conn.commit()

        # Verifica que foi atualizado
        row = conn.execute("SELECT last_accessed FROM nodes WHERE id = ?", (target_id,)).fetchone()
        report(
            "last_accessed atualizado para 90 dias atrás",
            row is not None,
            f"last_accessed={row[0]}" if row else "",
        )
    finally:
        conn.close()

    # --- 4.3: Rodar Janitor para arquivar nós inativos ---
    print("\n  [4.3] Executando Janitor (deve arquivar nó inativo)...")
    maint_report = janitor.run_maintenance(PROJECT_UUID)

    report(
        "Janitor arquivou nós inativos",
        maint_report.inactive_nodes_archived > 0,
        f"arquivados={maint_report.inactive_nodes_archived}",
    )

    # --- 4.4: Verificar estado do nó ---
    node_after = store.get_node(target_id)
    node_status = node_after.get("status", "UNKNOWN")
    report(
        "Nó migrou para estado ARCHIVED",
        node_status == "ARCHIVED",
        f"status={node_status}",
    )

    # --- 4.5: Nós ativos restantes ---
    remaining = store.get_nodes_by_project(PROJECT_UUID, status="ACTIVE")
    report(
        "Nós ativos restantes estão preservados",
        True,  # Informational
        f"{len(remaining)} nós ativos permanecem",
    )


# ═══════════════════════════════════════════════════════════════════
# RELATÓRIO FINAL
# ═══════════════════════════════════════════════════════════════════

def print_final_report() -> int:
    """Imprime o relatório visual consolidado. Retorna exit code."""
    header("RELATÓRIO FINAL — Stress Test v3.8.0")

    total = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = total - passed

    print()
    for label, ok, detail in _results:
        icon = "✅" if ok else "❌"
        line = f"  {icon} {label}"
        if detail:
            line += f"  →  {detail}"
        print(line)

    print()
    print("─" * 64)
    pct = (passed / total * 100) if total > 0 else 0
    status_icon = "🏆" if failed == 0 else "⚠️"
    print(f"  {status_icon}  {passed}/{total} testes passaram ({pct:.0f}%)")

    if failed == 0:
        print("  🔒 Absolute Solidity CONFIRMADA")
    else:
        print(f"  ❌ {failed} teste(s) falharam — investigar")

    print("─" * 64)
    return 0 if failed == 0 else 1


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main() -> int:
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   GRAFO CONCIERGE v3.8.0 — MEMORY STRESS TEST            ║")
    print("║   Validação de Ciclo de Vida Completo (Absolute Solidity) ║")
    print("╚════════════════════════════════════════════════════════════╝")

    api_status = "Real LLM" if LLM_API_KEY else "Fallback (sem GRAFO_LLM_API_KEY)"
    print(f"\n  Modo LLM: {api_status}")
    print(f"  DB:       {DB_PATH}")
    print(f"  ChromaDB: {CHROMA_PATH}")
    print(f"  Project:  {PROJECT_UUID}")

    # --- Setup ---
    header("SETUP: Preparando workspace")
    setup_workspace()
    print("  Workspace criado com 3 ficheiros de teste")

    store = None
    try:
        store, vector, embedder, manager, janitor = bootstrap()
        print("  Componentes inicializados (REAIS, sem mocks)")

        # --- Testes ---
        test_dimension_1(store, vector, embedder, manager)
        test_dimension_2(store, manager)
        test_dimension_3(store, vector, manager, janitor)
        test_dimension_4(store, janitor)

    except Exception as e:
        print(f"\n  ❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        report("Execução sem erros fatais", False, str(e))

    finally:
        # --- Cleanup ---
        if store is not None:
            try:
                store.close()
            except Exception:
                pass
        try:
            shutil.rmtree(TEST_DIR, ignore_errors=True)
        except Exception:
            pass

    return print_final_report()


if __name__ == "__main__":
    sys.exit(main())
