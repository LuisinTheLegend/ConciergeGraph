"""tests/test_ingestion_vector_repair.py

TDD tests for F4-008 and F4-009:
- Automatic repair of missing vectors during mining.
- Honest reporting of embedding results (embeddings_failed, embeddings_repaired).
- Integration with JanitorService._sync_vectors (delegating without logic duplication).
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional

import pytest

from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingTier
from ingestion.orchestrator import IngestionManager, IngestionResult
try:
    from ingestion.orchestrator import build_vector_metadata
except ImportError:
    build_vector_metadata = None
from services.janitor import JanitorService, MaintenanceReport


class StubDeterministicEmbedder:
    """Deterministic stub embedder implementing EmbeddingManager interface for tests."""

    def __init__(
        self,
        fail_all: bool = False,
        fail_indices: Optional[set[int]] = None,
        fail_batch_index: Optional[int] = None,
    ):
        self.fail_all = fail_all
        self.fail_indices = fail_indices or set()
        self.fail_batch_index = fail_batch_index
        self.batch_call_count = 0
        self.tier = EmbeddingTier.FLASH
        self.dimensions = 384

    def embed(self, text: str) -> Optional[list[float]]:
        if self.fail_all or not text or not text.strip():
            return None
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return [(b / 255.0) for b in (h * 12)[:384]]

    def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        if self.fail_all:
            return [None] * len(texts)
        if self.fail_batch_index is not None and self.batch_call_count == self.fail_batch_index:
            self.batch_call_count += 1
            return [None] * len(texts)
        self.batch_call_count += 1
        results = []
        for idx, t in enumerate(texts):
            if idx in self.fail_indices or not t or not t.strip():
                results.append(None)
            else:
                results.append(self.embed(t))
        return results


def _create_fixture_files(repo_path: Path):
    repo_path.mkdir(parents=True, exist_ok=True)
    file_a = repo_path / "module_a.py"
    file_a.write_text(
        "def hello_world():\n"
        "    \"\"\"Docstring hello.\"\"\"\n"
        "    return 'hello'\n\n"
        "class Greeter:\n"
        "    def greet(self):\n"
        "        return 'hi'\n",
        encoding="utf-8"
    )
    file_b = repo_path / "module_b.py"
    file_b.write_text(
        "def compute_sum(a, b):\n"
        "    \"\"\"Docstring compute.\"\"\"\n"
        "    return a + b\n",
        encoding="utf-8"
    )


class TestIngestionVectorRepair:
    """Test suite covering F4-008 and F4-009 requirements."""

    def test_scenario_a_model_unavailable_then_repaired(self, tmp_path: Path):
        """Cenário a: Modelo indisponível na 1ª mineração (retorna [None]*n),
        nós criados, 0 vetores, embeddings_failed > 0 e aviso em errors;
        2ª mineração com embedder são repara os vetores faltantes.
        """
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")
        repo_dir = tmp_path / "repo"
        _create_fixture_files(repo_dir)

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_a")

        # 1ª mineração: embedder offline
        failing_embedder = StubDeterministicEmbedder(fail_all=True)
        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=failing_embedder,
        )

        res1 = ingestion.mine(project_uuid, str(repo_dir))

        nodes = store.get_nodes_by_project(project_uuid, status="ACTIVE")
        nodes_with_content = [n for n in nodes if n.get("content") and n["content"].strip()]
        assert len(nodes_with_content) > 0, "Deveriam existir nós com conteúdo no SQLite"

        stored_ids_1 = vector_store.get_all_stored_node_ids()
        assert len(stored_ids_1) == 0, "Chroma não deve ter nenhum vetor quando o embedder falha"
        assert res1.embeddings_failed == len(nodes_with_content), f"Falhas duplicadas: esperava {len(nodes_with_content)}, obteve {res1.embeddings_failed}"
        assert res1.embeddings_repaired == 0, "Nenhum reparo imediato deve ocorrer no ciclo com falha de modelo"
        assert len(res1.errors) > 0, "errors deve conter aviso sobre chunks sem vetor"

        # 2ª mineração: troca para embedder são (arquivos inalterados)
        healthy_embedder = StubDeterministicEmbedder(fail_all=False)
        ingestion._embedder = healthy_embedder

        res2 = ingestion.mine(project_uuid, str(repo_dir))

        stored_ids_2 = vector_store.get_all_stored_node_ids()
        assert len(stored_ids_2) == len(nodes_with_content), "Todos os nós com conteúdo devem ter vetores"
        assert res2.embeddings_repaired == len(nodes_with_content)
        assert res2.embeddings_failed == 0
        store.close()

    def test_scenario_b_reset_collection_recomposed(self, tmp_path: Path):
        """Cenário b: reset_collection: mine, vector_store.reset_collection(),
        2ª mine recompõe todos os vetores.
        """
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")
        repo_dir = tmp_path / "repo"
        _create_fixture_files(repo_dir)

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_b")
        embedder = StubDeterministicEmbedder(fail_all=False)

        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
        )

        res1 = ingestion.mine(project_uuid, str(repo_dir))
        nodes = store.get_nodes_by_project(project_uuid, status="ACTIVE")
        nodes_with_content = [n for n in nodes if n.get("content") and n["content"].strip()]
        assert len(vector_store.get_all_stored_node_ids()) == len(nodes_with_content)

        # Reset da coleção Chroma
        vector_store.reset_collection()
        assert len(vector_store.get_all_stored_node_ids()) == 0

        # 2ª mineração deve recompor
        res2 = ingestion.mine(project_uuid, str(repo_dir))
        assert len(vector_store.get_all_stored_node_ids()) == len(nodes_with_content)
        assert res2.embeddings_repaired == len(nodes_with_content)
        store.close()

    def test_scenario_c_partial_batch_failure_recovery(self, tmp_path: Path):
        """Cenário c: Falha parcial de lote: alguns chunks falham na 1ª mineração;
        2ª mineração completa o que falta.
        """
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")
        repo_dir = tmp_path / "repo"
        _create_fixture_files(repo_dir)

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_c")

        # 1ª mineração com falha parcial (apenas índices 0 e 1 falham)
        partial_embedder = StubDeterministicEmbedder(fail_indices={0, 1})
        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=partial_embedder,
        )

        res1 = ingestion.mine(project_uuid, str(repo_dir))
        nodes = store.get_nodes_by_project(project_uuid, status="ACTIVE")
        nodes_with_content = [n for n in nodes if n.get("content") and n["content"].strip()]

        stored_ids_1 = vector_store.get_all_stored_node_ids()
        assert len(stored_ids_1) < len(nodes_with_content)
        assert res1.embeddings_failed >= 2

        # 2ª mineração com embedder saudável
        healthy_embedder = StubDeterministicEmbedder(fail_all=False)
        ingestion._embedder = healthy_embedder

        res2 = ingestion.mine(project_uuid, str(repo_dir))
        stored_ids_2 = vector_store.get_all_stored_node_ids()
        assert len(stored_ids_2) == len(nodes_with_content)
        assert res2.embeddings_repaired == (len(nodes_with_content) - len(stored_ids_1))
        store.close()

    def test_scenario_d_chroma_unavailable_no_exception_and_repaired(self, tmp_path: Path):
        """Cenário d: Chroma indisponível durante a mineração: nenhuma exceção,
        aviso explícito, e a mineração seguinte repara.
        """
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")
        repo_dir = tmp_path / "repo"
        _create_fixture_files(repo_dir)

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_d")
        embedder = StubDeterministicEmbedder(fail_all=False)

        # Simula Chroma indisponível
        vector_store._available = False

        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
        )

        # Não deve lançar exceção
        res1 = ingestion.mine(project_uuid, str(repo_dir))
        assert isinstance(res1, IngestionResult)
        assert len(vector_store.get_all_stored_node_ids()) == 0

        # Restaura Chroma
        vector_store._available = True

        res2 = ingestion.mine(project_uuid, str(repo_dir))
        nodes = store.get_nodes_by_project(project_uuid, status="ACTIVE")
        nodes_with_content = [n for n in nodes if n.get("content") and n["content"].strip()]
        assert len(vector_store.get_all_stored_node_ids()) == len(nodes_with_content)
        assert res2.embeddings_repaired == len(nodes_with_content)
        store.close()

    def test_scenario_e_empty_or_whitespace_nodes_ignored(self, tmp_path: Path):
        """Cenário e: Nós sem conteúdo (vazio ou só espaços): não são tratados
        como faltantes nem contam como falha.
        """
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_e")
        embedder = StubDeterministicEmbedder(fail_all=False)

        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
        )

        # Cria nós manuais: 1 com conteúdo, 1 vazio, 1 só espaços, 1 None
        nid1 = store.create_node(project_uuid, "file1.py::f1", content="def f1(): pass")
        nid2 = store.create_node(project_uuid, "dir1", content="")
        nid3 = store.create_node(project_uuid, "file2.py::blank", content="   \n\t  ")
        nid4 = store.create_node(project_uuid, "dir2", content=None)

        found_missing, repaired, failed = ingestion.repair_missing_vectors(project_uuid)
        assert found_missing == 1, "Apenas o nó com conteúdo válido deve ser considerado faltante"
        assert repaired == 1
        assert failed == 0
        assert vector_store.get_all_stored_node_ids() == {nid1}
        store.close()

    def test_scenario_f_idempotence_third_mine_no_reembed(self, tmp_path: Path):
        """Cenário f: Idempotência: uma 3ª mineração não reembedda nada (embeddings_repaired == 0)."""
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")
        repo_dir = tmp_path / "repo"
        _create_fixture_files(repo_dir)

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_f")
        embedder = StubDeterministicEmbedder(fail_all=False)

        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
        )

        res1 = ingestion.mine(project_uuid, str(repo_dir))
        res2 = ingestion.mine(project_uuid, str(repo_dir))
        res3 = ingestion.mine(project_uuid, str(repo_dir))

        assert res3.embeddings_repaired == 0
        assert res3.embeddings_failed == 0
        store.close()

    def test_scenario_g_metadata_keys_identical_between_ingestion_and_repair(self, tmp_path: Path):
        """Cenário g: Metadados: todos os vetores reparados têm exatamente as mesmas chaves e
        valores de metadados de vetores criados pela ingestão normal.
        """
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")
        repo_dir = tmp_path / "repo"
        _create_fixture_files(repo_dir)

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_g")
        embedder = StubDeterministicEmbedder(fail_all=False)

        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
        )

        # 1. Ingestão normal
        ingestion.mine(project_uuid, str(repo_dir))
        stored_ids = list(vector_store.get_all_stored_node_ids())
        assert len(stored_ids) > 0

        # Lê metadados originais de TODOS os vetores gerados na ingestão
        all_orig_data = vector_store._collection.get(
            ids=[f"node_{nid}" for nid in stored_ids],
            include=["metadatas"]
        )
        orig_meta_map = {
            int(doc_id.replace("node_", "")): meta
            for doc_id, meta in zip(all_orig_data["ids"], all_orig_data["metadatas"])
        }

        # Deleta TODOS os vetores do Chroma
        for nid in stored_ids:
            vector_store.delete(f"node_{nid}")
        assert len(vector_store.get_all_stored_node_ids()) == 0

        # Executa reparo completo
        found, rep, fail = ingestion.repair_missing_vectors(project_uuid)
        assert found == len(stored_ids)
        assert rep == len(stored_ids)
        assert fail == 0
        assert vector_store.get_all_stored_node_ids() == set(stored_ids)

        # Lê metadados de TODOS os vetores reparados
        all_rep_data = vector_store._collection.get(
            ids=[f"node_{nid}" for nid in stored_ids],
            include=["metadatas"]
        )
        rep_meta_map = {
            int(doc_id.replace("node_", "")): meta
            for doc_id, meta in zip(all_rep_data["ids"], all_rep_data["metadatas"])
        }

        # As chaves e valores de TODOS os nós devem ser exatamente iguais
        for nid in stored_ids:
            orig_meta = orig_meta_map[nid]
            rep_meta = rep_meta_map[nid]
            assert set(rep_meta.keys()) == set(orig_meta.keys()), f"Chaves divergiram no nó {nid}"
            for k in orig_meta:
                assert rep_meta[k] == orig_meta[k], f"Nó {nid} chave {k} divergiu: {rep_meta[k]} != {orig_meta[k]}"
        store.close()

    def test_scenario_h_janitor_delegates_to_repair_and_removes_orphans(self, tmp_path: Path):
        """Cenário h: Janitor: JanitorService._sync_vectors delega para a mesma rotina de
        reparo (sem lógica duplicada) e remove órfãos como antes.
        """
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_h")
        embedder = StubDeterministicEmbedder(fail_all=False)

        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
        )

        # Cria nó no SQLite sem vetor correspondente no Chroma
        valid_nid = store.create_node(project_uuid, "valid.py::func", content="def func(): return 1")

        # Insere um vetor órfão no Chroma (id de nó 99999 que não existe no SQLite)
        dummy_vec = embedder.embed("orphan")
        vector_store._collection.upsert(
            ids=["node_99999"],
            embeddings=[dummy_vec],
            metadatas=[{"node_id": 99999, "project_uuid": project_uuid, "source_file": "orphan.py", "chunk_type": "raw", "symbol_name": ""}],
        )
        assert 99999 in vector_store.get_all_stored_node_ids()
        assert valid_nid not in vector_store.get_all_stored_node_ids()

        janitor = JanitorService(sqlite_store=store, vector_store=vector_store, ingestion_manager=ingestion)
        report = MaintenanceReport()

        removed = janitor._sync_vectors(project_uuid, report)

        # 1. Órfão removido
        assert removed == 1
        assert 99999 not in vector_store.get_all_stored_node_ids()

        # Verifica que IngestionManager possui a rotina de reparo unificada
        assert hasattr(ingestion, "repair_missing_vectors"), "IngestionManager deve implementar repair_missing_vectors"

        # 2. Vetor faltante reparado via delegação com metadados padronizados
        assert valid_nid in vector_store.get_all_stored_node_ids()
        rep_meta = vector_store._collection.get(ids=[f"node_{valid_nid}"], include=["metadatas"])["metadatas"][0]
        assert "source_file" in rep_meta, "Deve conter source_file da padronização da ingestão"
        assert rep_meta["source_file"] == "valid.py"
        assert rep_meta["symbol_name"] == "func"
        assert "chunk_type" in rep_meta
        store.close()

    def test_scenario_i_backward_compatible_node_type_search_without_chroma_metadata(self, tmp_path: Path):
        """Cenário i (F4-011): Compatibilidade retroativa da busca por node_type.
        Coleções legadas ou reparadas sem 'node_type' nos metadados do Chroma
        não devem perder o sinal vetorial ao filtrar por node_type no hybrid_search.
        """
        from core.config import ConciergeConfig
        from core.project_index import ProjectIndex
        from core.hybrid_search import HybridSearchEngine

        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="repair_i")
        embedder = StubDeterministicEmbedder(fail_all=False)

        # Cria 2 nós no SQLite com tipos distintos: FACT e SKILL
        nid_fact = store.create_node(
            project_uuid, "fact_node",
            content="Authentication requires bearer token",
            node_type="FACT"
        )
        nid_skill = store.create_node(
            project_uuid, "skill_node",
            content="Authentication helper tool",
            node_type="SKILL"
        )

        # Insere vetores no Chroma SEM 'node_type' nos metadados (simulando base legada)
        vec_fact = embedder.embed("Authentication requires bearer token")
        vec_skill = embedder.embed("Authentication helper tool")
        vector_store._collection.upsert(
            ids=[f"node_{nid_fact}", f"node_{nid_skill}"],
            embeddings=[vec_fact, vec_skill],
            metadatas=[
                {"node_id": nid_fact, "project_uuid": project_uuid, "source_file": "fact.md"},
                {"node_id": nid_skill, "project_uuid": project_uuid, "source_file": "skill.md"},
            ],
        )

        # Valida que o metadado no Chroma realmente NÃO contém 'node_type'
        sample_meta = vector_store._collection.get(ids=[f"node_{nid_fact}"], include=["metadatas"])["metadatas"][0]
        assert "node_type" not in sample_meta, "Simulação legada não deve conter node_type no Chroma"

        config = ConciergeConfig()
        project_index = ProjectIndex(store, config)
        search_engine = HybridSearchEngine(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
            project_index=project_index,
            config=config,
        )

        # Executa busca híbrida filtrando por node_type="FACT"
        results = search_engine.search(
            query="Authentication bearer",
            project_uuid=project_uuid,
            node_type="FACT",
            top_k=5,
        )

        # Validações:
        # 1. Retornou apenas o nó FACT
        assert len(results) == 1
        assert results[0]["node_id"] == nid_fact
        # 2. O sinal vetorial NÃO foi perdido (score_breakdown.vetorial > 0)
        assert results[0]["score_breakdown"]["vetorial"] > 0.0, "Sinal vetorial não deve ser descartado"
        # 3. O resultado no pós-processamento foi enriquecido com node_type do SQLite
        assert results[0].get("node_type") == "FACT"

        store.close()

