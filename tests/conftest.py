import pytest
import os
import shutil
import sys

# Garante import do setup_workspace e bootstrap de tests/memory_stress_test
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.memory_stress_test import setup_workspace, bootstrap, TEST_DIR

@pytest.fixture(scope="module")
def stress_components():
    """Inicializa os componentes reais uma única vez para o módulo de teste de stress."""
    setup_workspace()
    store, vector, embedder, manager, janitor = bootstrap()
    yield store, vector, embedder, manager, janitor
    # Cleanup após a execução do módulo
    try:
        store.close()
    except Exception:
        pass
    try:
        shutil.rmtree(TEST_DIR, ignore_errors=True)
    except Exception:
        pass

@pytest.fixture(scope="module")
def store(stress_components):
    return stress_components[0]

@pytest.fixture(scope="module")
def vector(stress_components):
    return stress_components[1]

@pytest.fixture(scope="module")
def embedder(stress_components):
    return stress_components[2]

@pytest.fixture(scope="module")
def manager(stress_components):
    return stress_components[3]

@pytest.fixture(scope="module")
def janitor(stress_components):
    return stress_components[4]
