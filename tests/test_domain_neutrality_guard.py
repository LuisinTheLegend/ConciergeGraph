"""
tests/test_domain_neutrality_guard.py - Testes-guarda de Neutralidade de Domínio

Garantem que:
- G1: ConciergeConfig não possui o campo `wing_keywords`.
- G2: Varredura por AST em todo código de produto não contém constantes de string
      iguais aos 5 domínios fixos aposentados.
- G3: Mineração real nunca altera primary_wing definida no cadastro, mesmo com arquivos
      contendo palavras como marketing e trade.
- G4: Validação de que alas continuam como texto livre (update_project aceita qualquer valor).
"""

import ast
import dataclasses
import os
import shutil
import sqlite3
import tempfile
import pytest

from core.config import ConciergeConfig, DEFAULT_CONFIG
from core.middleware import GrafoConcierge
from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingManager
from ingestion.orchestrator import IngestionManager
from storage.schema import SchemaManager


# ---------------------------------------------------------------------------
# G1: ConciergeConfig não tem campo wing_keywords
# ---------------------------------------------------------------------------

def test_g1_concierge_config_has_no_wing_keywords():
    """G1: Garante que ConciergeConfig não possui o campo wing_keywords."""
    field_names = [f.name for f in dataclasses.fields(ConciergeConfig)]
    assert "wing_keywords" not in field_names, "ConciergeConfig não deve conter o campo wing_keywords"
    cfg = ConciergeConfig()
    assert not hasattr(cfg, "wing_keywords"), "Instância de ConciergeConfig não deve ter atributo wing_keywords"
    assert not hasattr(DEFAULT_CONFIG, "wing_keywords"), "DEFAULT_CONFIG não deve ter atributo wing_keywords"


# ---------------------------------------------------------------------------
# G2: Varredura por AST em todo código de produto
# ---------------------------------------------------------------------------

def test_g2_no_retired_domain_strings_in_product_code():
    """G2: Varredura por AST em todo código de produto (core, storage, ingestion, services, interface, agent, agents).

    Nenhuma constante de string, incluindo docstring, pode ser igual a um dos 5 nomes
    aposentados (comparação exata, com ou sem acentos).
    A lista proibida reside estritamente dentro deste teste.
    """
    forbidden_exact = {
        "marketing/vendas",
        "finanças/quant",
        "financas/quant",
        "gestão/saas",
        "gestao/saas",
        "automação/rh",
        "automacao/rh",
        "estatística",
        "estatistica",
    }

    # Diretórios de código de produto
    product_dirs = ["core", "storage", "ingestion", "services", "interface", "agent", "agents"]
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    violations = []

    for p_dir in product_dirs:
        dir_path = os.path.join(repo_root, p_dir)
        if not os.path.isdir(dir_path):
            continue

        for root, dirs, files in os.walk(dir_path):
            # Ignora caches e diretórios ocultos
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for file in files:
                if not file.endswith(".py"):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/")

                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    source = f.read()

                try:
                    tree = ast.parse(source, filename=rel_path)
                except SyntaxError as e:
                    violations.append(f"Erro de sintaxe ao analisar {rel_path}: {e}")
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        val_normalized = node.value.strip().lower()
                        if val_normalized in forbidden_exact:
                            lineno = getattr(node, "lineno", "?")
                            violations.append(f"{rel_path}:{lineno} contém string proibida '{node.value}'")

    assert not violations, (
        f"Violação de Neutralidade de Domínio detectada no código de produto:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# G3: Mineração real nunca altera primary_wing
# ---------------------------------------------------------------------------

def test_g3_real_mining_never_alters_primary_wing():
    """G3: Mineração real nunca muda primary_wing, nem com arquivos contendo marketing, trade, etc."""
    temp_dir = tempfile.mkdtemp(prefix="g3_mining_guard_")
    db_path = os.path.join(temp_dir, "test.db")
    chroma_dir = os.path.join(temp_dir, "chroma")
    src_dir = os.path.join(temp_dir, "src")
    os.makedirs(src_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        SchemaManager(conn).apply_full_schema()
    finally:
        conn.close()

    store = SqliteStore(db_path)
    embedder = EmbeddingManager()
    vector_store = ChromaVectorStore(
        persist_dir=chroma_dir,
        collection_name="g3_guard_coll",
        embedding_manager=embedder,
    )
    ingestion_mgr = IngestionManager(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        summarizer=None,
    )
    gc = GrafoConcierge(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        ingestion_manager=ingestion_mgr,
    )

    old_llm_model = os.environ.get("GRAFO_LLM_MODEL")
    old_hf_offline = os.environ.get("HF_HUB_OFFLINE")
    os.environ["GRAFO_LLM_MODEL"] = "none"
    os.environ["HF_HUB_OFFLINE"] = "1"

    try:
        # 1. Registra com ala explícita do usuário
        p_uuid = gc.register_project(folder_name="meu-projeto", wing="infra/core", summary="Projeto com ala infra")
        before_proj = store.get_project(p_uuid)
        assert before_proj["primary_wing"] == "infra/core"

        # 2. Cria arquivos com termos que antes disparariam auto_categorize
        with open(os.path.join(src_dir, "marketing_and_trade.py"), "w", encoding="utf-8") as f:
            f.write("def run_campaign_and_trade():\n    print('venda conversao funil trade bolsa saas')\n")

        # 3. Minera
        res = gc.mine(p_uuid, src_dir)
        assert res.get("nodes_created", 0) > 0, "Deveria ter criado nós na mineração"
        assert "auto_categorized_wing" not in res, "Resultado da mineração não deve conter auto_categorized_wing"

        # 4. Verifica que primary_wing permanece estritamente inalterada
        after_proj = store.get_project(p_uuid)
        assert after_proj["primary_wing"] == "infra/core", (
            f"primary_wing foi alterada na mineração! Esperado 'infra/core', obtido '{after_proj['primary_wing']}'"
        )
    finally:
        if old_llm_model is not None:
            os.environ["GRAFO_LLM_MODEL"] = old_llm_model
        else:
            os.environ.pop("GRAFO_LLM_MODEL", None)
        if old_hf_offline is not None:
            os.environ["HF_HUB_OFFLINE"] = old_hf_offline
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)
        try:
            store.close()
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# G4: Alas como texto livre e update_project preservado
# ---------------------------------------------------------------------------

def test_g4_free_text_wings_and_update_project():
    """G4: Prova que alas são texto livre e update_project funciona normalmente."""
    temp_dir = tempfile.mkdtemp(prefix="g4_free_wings_")
    db_path = os.path.join(temp_dir, "test.db")
    conn = sqlite3.connect(db_path)
    try:
        SchemaManager(conn).apply_full_schema()
    finally:
        conn.close()

    store = SqliteStore(db_path)
    try:
        p_uuid = "proj-legacy-wing-test"
        # Registra com valor arbitrário
        store.create_project(uuid=p_uuid, folder_name="legacy_proj", primary_wing="marketing/vendas")
        proj = store.get_project(p_uuid)
        assert proj["primary_wing"] == "marketing/vendas"

        # Atualiza para outro valor arbitrário
        store.update_project(p_uuid, primary_wing="finanças/quant")
        proj_updated = store.get_project(p_uuid)
        assert proj_updated["primary_wing"] == "finanças/quant"
    finally:
        try:
            store.close()
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)

