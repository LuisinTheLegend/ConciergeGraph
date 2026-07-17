import pytest
import os
from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR

def test_safe_ignore_behavior(store, manager):
    """Valida o funcionamento do sistema de ignore em 3 camadas do Grafo Concierge.

    Testa:
    1. Regras padrão globais (DEFAULT_IGNORE_PATTERNS) impedem a ingestão de .env, .txt, logs, lockfiles, etc.
    2. Regras no .gitignore impedem a ingestão de arquivos específicos.
    3. Regras no .conciergeignore impedem a ingestão de arquivos específicos.
    """
    # Define os caminhos dos arquivos a serem criados
    env_file = os.path.join(PROJECT_DIR, ".env")
    env_local = os.path.join(PROJECT_DIR, ".env.local")
    txt_file = os.path.join(PROJECT_DIR, "src", "logins.txt")
    log_file = os.path.join(PROJECT_DIR, "execution.log")
    lock_file = os.path.join(PROJECT_DIR, "package-lock.json")
    
    git_ignored_file = os.path.join(PROJECT_DIR, "src", "git_ignored.py")
    concierge_ignored_file = os.path.join(PROJECT_DIR, "src", "concierge_ignored.py")
    
    # Garante que o diretório src existe
    os.makedirs(os.path.join(PROJECT_DIR, "src"), exist_ok=True)

    # 1. Escreve os arquivos que devem ser ignorados por padrão (DEFAULT_IGNORE_PATTERNS)
    with open(env_file, "w", encoding="utf-8") as f:
        f.write("SECRET_KEY=123456\nAPI_KEY=abcdef")
        
    with open(env_local, "w", encoding="utf-8") as f:
        f.write("DEBUG=True")
        
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("Este é um arquivo de texto com notas que não deve ser indexado.")
        
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("INFO: executando processo...")
        
    with open(lock_file, "w", encoding="utf-8") as f:
        f.write('{"name": "test-project", "version": "1.0.0"}')

    # 2. Escreve arquivo que deve ser ignorado pelo .gitignore
    with open(git_ignored_file, "w", encoding="utf-8") as f:
        f.write("def should_not_be_indexed_by_git():\n    pass")
        
    gitignore_path = os.path.join(PROJECT_DIR, ".gitignore")
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write("src/git_ignored.py\n")

    # 3. Escreve arquivo que deve ser ignorado pelo .conciergeignore
    with open(concierge_ignored_file, "w", encoding="utf-8") as f:
        f.write("def should_not_be_indexed_by_concierge():\n    pass")
        
    conciergeignore_path = os.path.join(PROJECT_DIR, ".conciergeignore")
    with open(conciergeignore_path, "w", encoding="utf-8") as f:
        f.write("src/concierge_ignored.py\n")

    # --- Executa a Ingestão ---
    result = manager.mine(PROJECT_UUID, PROJECT_DIR, auto_tag=True)
    
    # Coleta todos os nós salvos para verificação
    nodes = store.get_nodes_by_project(PROJECT_UUID)
    labels = {n["label"] for n in nodes}
    
    # --- Verificações ---
    
    # 1. Arquivos válidos (ex: README.md, interest_calculator.py) devem ter sido ingeridos
    assert any("README.md" in l for l in labels), "README.md deveria ter sido indexado!"
    assert any("interest_calculator.py" in l for l in labels), "interest_calculator.py deveria ter sido indexado!"

    # 2. Padrões Padrão (DEFAULT_IGNORE_PATTERNS)
    # Nenhum label deve conter arquivos confidenciais ou lixo
    for label in labels:
        assert ".env" not in label, f"Arquivo confidencial indexado! {label}"
        assert ".env.local" not in label, f"Arquivo confidencial indexado! {label}"
        assert "logins.txt" not in label, f"Arquivo .txt de log/lixo indexado! {label}"
        assert "execution.log" not in label, f"Arquivo de log indexado! {label}"
        assert "package-lock.json" not in label, f"Arquivo de lock indexado! {label}"
        
    # 3. Regra de ignore .gitignore
    assert not any("git_ignored.py" in l for l in labels), "Arquivo ignorado pelo .gitignore foi indexado!"
    
    # 4. Regra de ignore .conciergeignore
    assert not any("concierge_ignored.py" in l for l in labels), "Arquivo ignorado pelo .conciergeignore foi indexado!"

    # Cleanup dos arquivos criados especificamente para este teste
    for path in [env_file, env_local, txt_file, log_file, lock_file, git_ignored_file, concierge_ignored_file, gitignore_path, conciergeignore_path]:
        try:
            os.remove(path)
        except OSError:
            pass
