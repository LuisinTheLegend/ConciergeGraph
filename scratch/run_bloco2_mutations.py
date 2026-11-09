"""
Runner para as mutações do Bloco 2 (M10a até M10e) de acordo com o PEDIDO 4.4c.
Aplica cada mutação em arquivos de teste externos, executa o pytest no alvo correspondente,
grava a evidência em scratch/evidencia_4_4c/mutacao_<id>.txt e restaura o arquivo original.
"""

import os
import subprocess
import sys

EVIDENCIA_DIR = "scratch/evidencia_4_4c"
VENV_PYTEST = ".venv_clean/Scripts/pytest.exe"

os.makedirs(EVIDENCIA_DIR, exist_ok=True)

MUTATIONS = [
    {
        "id": "M10a",
        "name": "E2E troca db_manager por atribuição direta na função (nível function)",
        "file": "tests/test_e2e_concierge_integration.py",
        "target_test": "tests/test_e2e_concierge_integration.py::TestConciergeSovereignE2EAudit::test_e2e_flow_full_lifecycle_and_communication",
        "replace_from": "def test_e2e_flow_full_lifecycle_and_communication(self):",
        "replace_to": """def test_e2e_flow_full_lifecycle_and_communication(self):
        import interface.mcp_server as _mcp
        _mcp.db_manager = object()""",
    },
    {
        "id": "M10b",
        "name": "Classe de teste troca graph_rag no setup_class sem restaurar (nível class)",
        "file": "tests/test_mcp_server_handlers.py",
        "target_test": "tests/test_mcp_server_handlers.py::TestHandleMine",
        "replace_from": "class TestHandleMine:",
        "replace_to": """class TestHandleMine:
    @classmethod
    def setup_class(cls):
        import interface.mcp_server as _mcp
        _mcp.graph_rag = object()""",
    },
    {
        "id": "M10c",
        "name": "Módulo de teste troca _gc no nível de módulo (nível module)",
        "file": "tests/test_mcp_server_handlers.py",
        "target_test": "tests/test_mcp_server_handlers.py",
        "replace_from": "# ---------------------------------------------------------------------------\n# Fixtures",
        "replace_to": """@pytest.fixture(autouse=True, scope="module")
def _leak_module_gc():
    import interface.mcp_server as _mcp
    _mcp._gc = object()

# ---------------------------------------------------------------------------
# Fixtures""",
    },
    {
        "id": "M10d",
        "name": "Adiciona global novo em mcp_server durante teste",
        "file": "tests/test_e2e_concierge_integration.py",
        "target_test": "tests/test_e2e_concierge_integration.py::TestConciergeSovereignE2EAudit::test_e2e_flow_full_lifecycle_and_communication",
        "replace_from": "def test_e2e_flow_full_lifecycle_and_communication(self):",
        "replace_to": """def test_e2e_flow_full_lifecycle_and_communication(self):
        import interface.mcp_server as _mcp
        _mcp.novo_objeto = object()""",
    },
    {
        "id": "M10e",
        "name": "Remove global existente del mcp_server._gc durante teste",
        "file": "tests/test_e2e_concierge_integration.py",
        "target_test": "tests/test_e2e_concierge_integration.py::TestConciergeSovereignE2EAudit::test_e2e_flow_full_lifecycle_and_communication",
        "replace_from": "def test_e2e_flow_full_lifecycle_and_communication(self):",
        "replace_to": """def test_e2e_flow_full_lifecycle_and_communication(self):
        import interface.mcp_server as _mcp
        del _mcp._gc""",
    },
]


def run_test(target_test: str, timeout_sec: int = 25) -> tuple[int, str]:
    cmd = [VENV_PYTEST, target_test, "-v"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        return proc.returncode, proc.stdout + "\n" + proc.stderr
    except subprocess.TimeoutExpired as te:
        return 999, f"TIMEOUT EXPIRED após {timeout_sec}s: {te}"


def main():
    results = []

    for m in MUTATIONS:
        m_id = m["id"]
        m_name = m["name"]
        src_file = m["file"]
        target = m["target_test"]
        print(f"\n==================== Rodando Mutação {m_id}: {m_name} ====================")

        with open(src_file, "r", encoding="utf-8") as f:
            original_content = f.read()

        # 1. Roda teste SEM mutação (espera-se verde)
        ret_clean, out_clean = run_test(target, timeout_sec=25)
        clean_status = "PASSED" if ret_clean == 0 else f"FAILED (ret={ret_clean})"
        print(f"Sem mutação: {clean_status}")

        # 2. Aplica mutação
        if m["replace_from"] not in original_content:
            print(f"ERRO: Alvo de substituição para {m_id} não encontrado em {src_file}!")
            results.append((m_id, "ERRO_SUBSTITUICAO", False))
            continue

        mutated_content = original_content.replace(m["replace_from"], m["replace_to"], 1)
        with open(src_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(mutated_content)

        # 3. Roda teste COM mutação (espera-se falha)
        ret_mut, out_mut = run_test(target, timeout_sec=25)
        mut_status = "KILLED (FAILED)" if ret_mut != 0 else "SURVIVED (PASSED)"
        print(f"Com mutação: {mut_status} (ret={ret_mut})")

        # 4. Restaura original
        with open(src_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(original_content)

        # 5. Grava evidência
        evidencia_path = os.path.join(EVIDENCIA_DIR, f"mutacao_{m_id}.txt")
        with open(evidencia_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"MUTAÇÃO {m_id}: {m_name}\n")
            f.write(f"Arquivo: {src_file}\n")
            f.write(f"Alvo: {target}\n")
            f.write(f"Substituição:\n- {m['replace_from']}\n+ {m['replace_to']}\n\n")
            f.write("--- RESULTADO COM MUTAÇÃO (esperado: FALHA/KILLED) ---\n")
            f.write(f"Retcode: {ret_mut}\n")
            f.write(out_mut)
            f.write("\n--- RESULTADO SEM MUTAÇÃO (esperado: PASSOU) ---\n")
            f.write(f"Retcode: {ret_clean}\n")
            f.write(out_clean)

        killed = (ret_mut != 0) and (ret_clean == 0)
        results.append((m_id, m_name, killed))

    print("\n\n==================== RESUMO FINAL DAS MUTAÇÕES BLOCO 2 ====================")
    all_ok = True
    for m_id, name, killed in results:
        status_str = "MORTA (OK)" if killed else "FALHOU / SOBREVIVEU"
        if not killed:
            all_ok = False
        print(f"[{status_str}] {m_id}: {name}")

    if all_ok:
        print("\nTodas as 5 mutações (M10a a M10e) foram mortas com sucesso!")
    else:
        print("\nATENÇÃO: Nem todas as mutações foram mortas!")
        sys.exit(1)


if __name__ == "__main__":
    main()
