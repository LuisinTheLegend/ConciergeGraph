"""Teste E2E para services/janitor.py — Grafo Concierge v3.8.0"""
import sys, os, shutil, uuid, time, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.store import SqliteStore
from services.janitor import (
    JanitorService, MaintenanceReport,
    STALE_TRAJECTORY_DAYS, AUTO_ZOOM_THRESHOLD,
)

# ===================================================================
# Setup
# ===================================================================
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(BASE, "_test_janitor_tmp")
os.makedirs(TEST_DIR, exist_ok=True)

db_path = os.path.join(TEST_DIR, "janitor_test.db")
store = SqliteStore(db_path)
project_uuid = str(uuid.uuid4())
store.create_project(project_uuid, "janitor-test", "dev/test")

# --- Mock VectorStore ---
class MockVectorStore:
    def __init__(self):
        self.orphans_to_return = []
        self.deleted_ids = []

    def verify_sync(self, sqlite_node_ids):
        return self.orphans_to_return

    def delete_batch(self, doc_ids):
        self.deleted_ids.extend(doc_ids)
        return len(doc_ids)

    def delete(self, doc_id):
        self.deleted_ids.append(doc_id)

    def health_check(self):
        return True

    def update_metadata(self, doc_id: str, metadata: dict) -> None:
        """Mock: aceita update de metadata sem fazer nada (ChromaDB indisponível em testes)."""
        pass

    def count(self, project_uuid=None):
        return 0

# --- Mock IngestionManager ---
class MockIngestionManager:
    def __init__(self):
        self.zoom_called = False
        self.zoom_result = {"l1_count": 3, "l2_summary": "Test compass.", "l2_tags": ["test"]}

    def generate_project_context(self, project_uuid):
        self.zoom_called = True
        return self.zoom_result

    def generate_community_summary(self, nodes_block: str):
        """Mock: sem LLM, retorna None (janitor usará o fallback heurístico)."""
        return None


mock_vector = MockVectorStore()
mock_ingestion = MockIngestionManager()

janitor = JanitorService(
    sqlite_store=store,
    vector_store=mock_vector,
    ingestion_manager=mock_ingestion,
    stale_days=STALE_TRAJECTORY_DAYS,
    auto_zoom_threshold=2,  # threshold baixo para teste
    inactive_days=0,  # marca tudo como inativo para teste
)

# ===================================================================
print("=" * 60)
print("TESTE 1: run_maintenance() — projeto vazio (sem dados)")
print("=" * 60)
report = janitor.run_maintenance(project_uuid)
print(f"  trajectories_decayed: {report.trajectories_decayed}")
print(f"  orphan_vectors_removed: {report.orphan_vectors_removed}")
print(f"  inactive_nodes_archived: {report.inactive_nodes_archived}")
print(f"  zoom_triggered: {report.zoom_triggered}")
print(f"  fts_rebuilt: {report.fts_rebuilt}")
print(f"  errors: {report.errors}")
print(f"  duration: {report.duration_seconds:.3f}s")
assert report.trajectories_decayed == 0
assert report.orphan_vectors_removed == 0
assert len(report.errors) == 0
print("  [PASS] Manutenção em projeto vazio OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 2: Decaimento de trajetórias")
print("=" * 60)
# Cria trajetórias (bulk_decay depende de created_at < threshold)
for i in range(3):
    store.create_trajectory(
        project_uuid, f"prompt_{i}", f"exec_{i}",
        status="ACTIVE",
    )
report2 = janitor.run_maintenance(project_uuid)
print(f"  trajectories_decayed: {report2.trajectories_decayed}")
# Trajetórias acabaram de ser criadas, então não devem ser decayed (< 30d)
assert report2.trajectories_decayed == 0, "Trajetórias recentes não devem ser decayed"
print("  [PASS] Trajetórias recentes não são decayed")

# ===================================================================
print()
print("=" * 60)
print("TESTE 3: Sincronização vetorial (vetores órfãos)")
print("=" * 60)
mock_vector.orphans_to_return = ["node_999", "node_998", "node_997"]
report3 = janitor.run_maintenance(project_uuid)
print(f"  orphan_vectors_removed: {report3.orphan_vectors_removed}")
print(f"  deleted_ids: {mock_vector.deleted_ids}")
assert report3.orphan_vectors_removed == 3, f"Esperado 3 orphans removidos, obteve {report3.orphan_vectors_removed}"
assert "node_999" in mock_vector.deleted_ids
mock_vector.orphans_to_return = []  # Reset
mock_vector.deleted_ids = []
print("  [PASS] Vetores órfãos removidos OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 4: Arquivamento de nós inativos")
print("=" * 60)
# Cria nós e backdata os timestamps para garantir que fiquem antes do threshold
node_ids_to_archive = []
for i in range(3):
    nid = store.create_node(project_uuid, f"test_node_{i}", node_type="FACT", type_="file")
    node_ids_to_archive.append(nid)

# Backdata os nós diretamente no banco: set last_accessed to 2 days ago
import sqlite3
raw = sqlite3.connect(db_path)
raw.execute(
    "UPDATE nodes SET last_accessed = datetime('now', '-2 days') WHERE project_uuid = ?",
    (project_uuid,),
)
raw.commit()
raw.close()

# Agora roda o janitor com inactive_days=1 (threshold = ontem)
janitor_archive = JanitorService(
    sqlite_store=store, vector_store=mock_vector,
    ingestion_manager=mock_ingestion, inactive_days=1,
)
report4 = janitor_archive.run_maintenance(project_uuid)
print(f"  inactive_nodes_archived: {report4.inactive_nodes_archived}")
assert report4.inactive_nodes_archived >= 3, f"Esperado >= 3 nós arquivados, obteve {report4.inactive_nodes_archived}"
print("  [PASS] Nós inativos arquivados OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 5: Auto-Zoom trigger")
print("=" * 60)
mock_ingestion.zoom_called = False
# Cria nós suficientes (>= threshold=2) para disparar Auto-Zoom
for i in range(5):
    store.create_node(project_uuid, f"new_node_{i}", node_type="FACT", type_="file")
report5 = janitor.run_maintenance(project_uuid)
print(f"  zoom_triggered: {report5.zoom_triggered}")
print(f"  zoom_l1_count: {report5.zoom_l1_count}")
print(f"  zoom_l2_summary: {report5.zoom_l2_summary}")
assert report5.zoom_triggered is True, "Auto-Zoom deveria ter sido disparado"
assert mock_ingestion.zoom_called is True
assert report5.zoom_l1_count == 3
print("  [PASS] Auto-Zoom disparado corretamente")

# ===================================================================
print()
print("=" * 60)
print("TESTE 6: FTS Rebuild (após mudanças)")
print("=" * 60)
# report4 teve nós arquivados → changes > 0 → FTS rebuild
assert report4.fts_rebuilt is True, "FTS deveria ter sido reconstruído após mudanças"
print("  [PASS] FTS Rebuild OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 7: Idle-Lock (mine ativo)")
print("=" * 60)
janitor.signal_mine_start()
report7 = janitor.run_maintenance(project_uuid)
print(f"  skipped_idle_lock: {report7.skipped_idle_lock}")
assert report7.skipped_idle_lock is True, "Deveria ter sido adiado pelo Idle-Lock"
janitor.signal_mine_end()
print("  [PASS] Idle-Lock funciona corretamente")

# ===================================================================
print()
print("=" * 60)
print("TESTE 8: to_dict() (compatibilidade)")
print("=" * 60)
d = report5.to_dict()
required = {"timestamp", "project_uuid", "trajectories_decayed",
            "orphan_vectors_removed", "inactive_nodes_archived",
            "zoom_triggered", "zoom_l1_count", "zoom_l2_summary",
            "fts_rebuilt", "errors", "duration_seconds", "skipped_idle_lock"}
assert required.issubset(set(d.keys())), f"Chaves faltando: {required - set(d.keys())}"
print(f"  Keys: {sorted(d.keys())}")
print("  [PASS] to_dict() OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 9: Background thread (start/stop)")
print("=" * 60)
mock_vector2 = MockVectorStore()
janitor_bg = JanitorService(
    sqlite_store=store,
    vector_store=mock_vector2,
    ingestion_manager=None,
    auto_zoom_threshold=999,  # não dispara zoom
)
janitor_bg.start_background(project_uuid, interval=1)
assert janitor_bg.is_running is True
print(f"  is_running: {janitor_bg.is_running}")
time.sleep(2.5)  # Espera pelo menos 2 ciclos
janitor_bg.stop_background(timeout=5)
assert janitor_bg.is_running is False
reports = janitor_bg.last_reports
print(f"  Ciclos executados: {len(reports)}")
assert len(reports) >= 2, f"Esperado >= 2 ciclos, obteve {len(reports)}"
print("  [PASS] Background thread start/stop OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 10: run_all_projects()")
print("=" * 60)
# Cria um segundo projeto
project2 = str(uuid.uuid4())
store.create_project(project2, "project-two", "dev/test")
janitor_all = JanitorService(
    sqlite_store=store,
    vector_store=MockVectorStore(),
    auto_zoom_threshold=999,
)
all_reports = janitor_all.run_all_projects()
print(f"  Projetos processados: {len(all_reports)}")
assert len(all_reports) >= 2, f"Esperado >= 2 projetos, obteve {len(all_reports)}"
print("  [PASS] run_all_projects() OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 11: Detecção de Comunidades (Leiden) & Sumarização")
print("=" * 60)
project3 = str(uuid.uuid4())
store.create_project(project3, "project-three", "dev/test")

# 1. Cria um super-nó com in_degree = 10
super_node_id = store.create_node(project3, "core_node", node_type="FACT")
for i in range(10):
    dep_node = store.create_node(project3, f"dep_node_{i}", node_type="FACT")
    store.create_edge(source_id=dep_node, target_id=super_node_id, relation_type="depends_on")

# 2. Cria um nó quase-super-nó com in_degree = 9 (não deve ser detectado se threshold=10)
almost_super_node_id = store.create_node(project3, "almost_core", node_type="FACT")
for i in range(9):
    dep_node = store.create_node(project3, f"almost_dep_{i}", node_type="FACT")
    store.create_edge(source_id=dep_node, target_id=almost_super_node_id, relation_type="depends_on")

# Inicializa o janitor com super_node_threshold = 10
janitor_rag = JanitorService(
    sqlite_store=store,
    vector_store=MockVectorStore(),
    ingestion_manager=mock_ingestion,
    super_node_threshold=10,
    auto_zoom_threshold=999,
)

# Detecta comunidades
communities = janitor_rag.detect_communities(project3)
print(f"  Comunidades detectadas: {list(communities.keys())}")
assert len(communities) == 1, f"Esperado 1 comunidade, obteve {len(communities)}"
assert super_node_id in communities, "O super-nó deve ser o anchor da comunidade"
assert almost_super_node_id not in communities, "O nó com in_degree 9 não deve ser anchor"

# Verifica se os membros da comunidade incluem os dependentes
members = communities[super_node_id]
print(f"  Membros da comunidade: {len(members)}")
assert len(members) == 11, f"Esperado 11 membros (super-nó + 10 dependentes), obteve {len(members)}"
assert super_node_id in members

# Gera e persiste os resumos
summaries = janitor_rag.generate_and_persist_community_summaries(project3, communities)
print(f"  Resumos gerados: {len(summaries)}")
assert len(summaries) == 1
assert summaries[0]["community_id"] == super_node_id
assert "Logical community anchored by super-node" in summaries[0]["summary"]

# Verifica se o nó INSIGHT foi persistido no SQLite
with store._conn_mgr.read() as conn:
    insight_node = conn.execute(
        "SELECT id, label, summary, node_type FROM nodes WHERE node_type = 'INSIGHT' AND project_uuid = ?",
        (project3,)
    ).fetchone()
assert insight_node is not None, "O nó INSIGHT deveria ter sido persistido"
assert insight_node["summary"] == summaries[0]["summary"]

# Verifica se os payloads vetoriais foram injetados com o community_id
print(f"  Payloads vetoriais atualizados: {list(janitor_rag.vector_payloads.keys())}")
for mid in members:
    assert mid in janitor_rag.vector_payloads, f"Nó {mid} deveria ter payload vetorial atualizado"
    assert janitor_rag.vector_payloads[mid]["community_id"] == super_node_id

# Executa o run_maintenance completo no projeto 3
report11 = janitor_rag.run_maintenance(project3)
print(f"  report11 communities_detected: {report11.communities_detected}")
print(f"  report11 summaries_generated: {report11.summaries_generated}")
assert report11.communities_detected == 1
assert report11.summaries_generated == 1
print("  [PASS] Detecção de Comunidades (Leiden) & Sumarização OK")

# ===================================================================
# Cleanup
# ===================================================================
store.close()
try:
    shutil.rmtree(TEST_DIR)
except PermissionError:
    pass  # Windows file lock — cleanup on next run

print()
print("=" * 60)
print("TODOS OS 11 TESTES PASSARAM — janitor.py v3.8.0 OPERACIONAL")
print("=" * 60)
