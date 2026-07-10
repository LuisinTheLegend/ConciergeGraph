import pytest
import os
import shutil
from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR, UTILS_FILE

def test_chunk_cache_behavior(store, vector, manager):
    """Valida o funcionamento do Delta Cache em nível de chunk.

    Verifica se chunks inalterados são reaproveitados (IDs preservados,
    file_hash atualizado) enquanto novos/modificados são inseridos.
    """
    # --- 1. Primeira Ingestão ---
    result1 = manager.mine(PROJECT_UUID, PROJECT_DIR, auto_tag=True)
    assert result1.files_processed > 0
    
    # Coleta nós do utils.py antes da modificação
    nodes_before = store.get_nodes_by_project(PROJECT_UUID)
    utils_nodes_before = [n for n in nodes_before if "utils.py" in n["label"]]
    assert len(utils_nodes_before) > 0
    
    # Mapeia label -> id, file_hash, summary
    before_map = {n["label"]: (n["id"], n["file_hash"], n["summary"]) for n in utils_nodes_before}
    
    # --- 2. Modifica apenas uma parte do utils.py ---
    # Lemos o conteúdo atual do utils.py
    with open(UTILS_FILE, "r", encoding="utf-8") as f:
        original_code = f.read()
        
    # Adicionamos uma nova função no final
    modified_code = original_code + "\n\ndef new_helper_function():\n    return 'cached!'"
    
    with open(UTILS_FILE, "w", encoding="utf-8") as f:
        f.write(modified_code)
        
    # --- 3. Segunda Ingestão ---
    result2 = manager.mine(PROJECT_UUID, PROJECT_DIR, auto_tag=True)
    assert result2.files_processed == 1  # Apenas o utils.py foi re-processado
    
    # Coleta nós do utils.py após a modificação
    nodes_after = store.get_nodes_by_project(PROJECT_UUID)
    utils_nodes_after = [n for n in nodes_after if "utils.py" in n["label"]]
    
    # Mapeia label -> id, file_hash, summary
    after_map = {n["label"]: (n["id"], n["file_hash"], n["summary"]) for n in utils_nodes_after}
    
    # --- 4. Asserções do Delta Cache ---
    # A nova função helper deve ter sido criada como um no-id diferente
    new_helper_label = f"src/utils.py::new_helper_function"
    assert new_helper_label in after_map
    
    # As funções antigas (ex: print_success) devem ter tido CACHE HIT
    for label, (old_id, old_hash, old_summary) in before_map.items():
        # Desconsidera o arquivo utils.py inteiro e a raiz do módulo (pois seu hash/conteúdo mudou)
        if "::" not in label or label.endswith("::<module>"):
            continue
            
        assert label in after_map, f"Nó {label} desapareceu pós-cache!"
        new_id, new_hash, new_summary = after_map[label]
        
        # O ID deve ser exatamente o mesmo (reaproveitado!)
        assert new_id == old_id, f"ID do nó {label} mudou de {old_id} para {new_id}!"
        
        # O file_hash deve ter sido atualizado para o novo hash
        assert new_hash != old_hash, f"file_hash do nó {label} não foi atualizado pós-cache!"
        
        # O resumo deve ser o mesmo
        assert new_summary == old_summary, f"Resumo do nó {label} foi modificado!"
