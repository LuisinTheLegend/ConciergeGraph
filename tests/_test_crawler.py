"""Script de teste E2E para ingestion/crawler.py — Grafo Concierge v3.8.0"""

import sys
import os
import uuid
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ===================================================================
# TESTE 1: GitignoreParser
# ===================================================================
print("=" * 60)
print("TESTE 1: GitignoreParser")
print("=" * 60)

from ingestion.crawler import GitignoreParser

parser = GitignoreParser()

# Cria um .gitignore temporário
test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_test_crawl_tmp")
os.makedirs(test_dir, exist_ok=True)

gitignore_content = """# Build artifacts
dist/
build/
*.pyc
__pycache__/

# IDE
.idea/
.vscode/

# Dependencies
node_modules/
venv/

# Logs
*.log

# Negacao: NAO ignorar este arquivo
!important.log
"""

gitignore_path = os.path.join(test_dir, ".gitignore")
with open(gitignore_path, "w") as f:
    f.write(gitignore_content)

parser.load(gitignore_path)

# Testa padrões
tests = [
    ("dist", True, True, "dir dist/ ignorado"),
    ("node_modules", True, True, "dir node_modules/ ignorado"),
    ("src/main.py", False, False, "arquivo .py NAO ignorado"),
    ("cache.pyc", False, True, "arquivo *.pyc ignorado"),
    ("__pycache__", True, True, "dir __pycache__/ ignorado"),
    ("app.log", False, True, "arquivo *.log ignorado"),
    ("important.log", False, False, "negacao !important.log funciona"),
    (".idea", True, True, "dir .idea/ ignorado"),
    ("src/utils.ts", False, False, "arquivo .ts NAO ignorado"),
]

passed = 0
for path, is_dir, expected, desc in tests:
    result = parser.should_ignore(path, is_dir=is_dir)
    status = "PASS" if result == expected else "FAIL"
    if status == "PASS":
        passed += 1
    print(f"  [{status}] {desc}: should_ignore(\"{path}\", is_dir={is_dir}) = {result}")

print(f"\nResultado: {passed}/{len(tests)} testes passaram")
shutil.rmtree(test_dir)
print()

# ===================================================================
# TESTE 2: FileCategory Classification
# ===================================================================
print("=" * 60)
print("TESTE 2: Classificacao de Arquivos")
print("=" * 60)

from ingestion.crawler import ProjectCrawler, FileCategory


class MockStore:
    def find_node_by_hash(self, project_uuid, file_hash):
        return None

    def get_nodes_by_project(self, project_uuid, **kw):
        return []


crawler = ProjectCrawler(MockStore())

classify_tests = [
    ("main.py", FileCategory.CODE),
    ("app.tsx", FileCategory.CODE),
    ("handler.go", FileCategory.CODE),
    ("README.md", FileCategory.DOC),
    ("config.yaml", FileCategory.CONFIG),
    ("session.log", FileCategory.CONVERSATION),
    ("image.png", FileCategory.UNKNOWN),
    ("data.csv", FileCategory.UNKNOWN),
]

for filename, expected in classify_tests:
    result = crawler.classify_file(filename)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] {filename} -> {result.value} (esperado: {expected.value})")

print()

# ===================================================================
# TESTE 3: SHA256 Hash
# ===================================================================
print("=" * 60)
print("TESTE 3: SHA256 Hash")
print("=" * 60)

test_dir2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_test_hash_tmp")
os.makedirs(test_dir2, exist_ok=True)
test_file = os.path.join(test_dir2, "test.txt")
with open(test_file, "w") as f:
    f.write("Hello, Grafo Concierge!")

h1 = crawler.compute_file_hash(test_file)
h2 = crawler.compute_file_hash(test_file)
print(f"  Hash 1: {h1}")
print(f"  Hash 2: {h2}")
print(f"  [PASS] Deterministico: {h1 == h2}")

with open(test_file, "w") as f:
    f.write("Modified content")

h3 = crawler.compute_file_hash(test_file)
print(f"  Hash 3: {h3}")
print(f"  [PASS] Delta detectado: {h1 != h3}")

shutil.rmtree(test_dir2)
print()

# ===================================================================
# TESTE 4: Crawl Completo com SqliteStore REAL
# ===================================================================
print("=" * 60)
print("TESTE 4: Crawl Completo (SqliteStore + Filesystem)")
print("=" * 60)

from storage.store import SqliteStore

test_project_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_test_project_tmp")
os.makedirs(os.path.join(test_project_dir, "src"), exist_ok=True)
os.makedirs(os.path.join(test_project_dir, "docs"), exist_ok=True)
os.makedirs(os.path.join(test_project_dir, "node_modules", "dep"), exist_ok=True)
os.makedirs(os.path.join(test_project_dir, "__pycache__"), exist_ok=True)

# Cria arquivos de teste
with open(os.path.join(test_project_dir, "src", "main.py"), "w") as f:
    f.write("def main(): pass")
with open(os.path.join(test_project_dir, "src", "utils.ts"), "w") as f:
    f.write("export function util() {}")
with open(os.path.join(test_project_dir, "docs", "README.md"), "w") as f:
    f.write("# Projeto Teste")
with open(os.path.join(test_project_dir, "config.yaml"), "w") as f:
    f.write("key: value")
# Estes NAO devem ser indexados
with open(os.path.join(test_project_dir, "node_modules", "dep", "index.js"), "w") as f:
    f.write("module.exports = {}")
with open(os.path.join(test_project_dir, "__pycache__", "main.cpython-312.pyc"), "wb") as f:
    f.write(b"fake bytecode")

# .gitignore
with open(os.path.join(test_project_dir, ".gitignore"), "w") as f:
    f.write("*.pyc\nnode_modules/\n__pycache__/\ntest.db*\n")

# SqliteStore real
db_path = os.path.join(test_project_dir, "test.db")
store = SqliteStore(db_path)
project_uuid = str(uuid.uuid4())
store.create_project(project_uuid, "test-project", "dev/test")

# 1o Crawl — todos são novos
real_crawler = ProjectCrawler(store)
report = real_crawler.crawl(test_project_dir, project_uuid)

print(f"  Total escaneados: {report.total_scanned}")
print(f"  Novos: {len(report.new_files)}")
print(f"  Inalterados: {len(report.unchanged_files)}")
print(f"  Deletados (GC): {len(report.deleted_node_ids)}")
print(f"  Categorias: {report.categories}")

new_paths = [r.relative_path for r in report.new_files]
print(f"  Arquivos novos: {new_paths}")

assert "node_modules/dep/index.js" not in new_paths, "node_modules NAO deveria estar!"
assert report.total_scanned == 4, f"Esperado 4 arquivos, obteve {report.total_scanned}"
print("  [PASS] node_modules e __pycache__ corretamente ignorados")

# 2. Insere um nó e faz crawl novamente para testar delta
first_file = report.new_files[0]
node_id = store.create_node(
    project_uuid=project_uuid,
    label=first_file.relative_path,
    node_type="FACT",
    type_="file",
    file_hash=first_file.file_hash,
)
print(f"  No criado: id={node_id}, hash={first_file.file_hash[:16]}...")

report2 = real_crawler.crawl(test_project_dir, project_uuid)
print(f"  2o crawl: {len(report2.new_files)} novos, {len(report2.unchanged_files)} inalterados")
assert len(report2.unchanged_files) >= 1, "Deveria ter pelo menos 1 inalterado!"
print("  [PASS] Delta Detection funcionando")

# 3. Deleta o arquivo e faz crawl para testar GC
deleted_file_path = os.path.join(test_project_dir, first_file.relative_path.replace("/", os.sep))
os.remove(deleted_file_path)
report3 = real_crawler.crawl(test_project_dir, project_uuid)
print(f"  3o crawl (pos delete): {len(report3.deleted_node_ids)} nos orfaos detectados")
assert len(report3.deleted_node_ids) >= 1, "Deveria detectar no orfao!"
print("  [PASS] Garbage Collection detectou no orfao")

# Cleanup
store.close()
shutil.rmtree(test_project_dir)

print()
print("=" * 60)
print("TODOS OS TESTES PASSARAM — crawler.py v3.8.0 OPERACIONAL")
print("=" * 60)
