"""
scratch/verify_bloco2_bloco3_4_4g.py — Valida Blocos 2 e 3 da Rodada 4.4g:
1. Consumidores de stress_components + guardas (check_mcp_globals_leak, M10d, G2), ordens normal e --reverse.
2. Restauração de GRAFO_LIGHTWEIGHT_MODE quando ausente e quando presente.
3. Mutação externa (reintroduzir persist_dir=CHROMA_PATH fixo em bootstrap):
   - Prova que test_stress_components_reuse_cycle_characterization continua PASSANDO (sem teste vermelho para F4-034).
   - Prova que test_bootstrap_uses_distinct_chroma_subdir_per_call FALHA com a mutação e PASSA sem ela.
"""

import os
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4g")
PY310 = os.path.join(REPO_ROOT, ".venv_310", "Scripts", "python.exe")
PY312 = os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")
STRESS_FILE = os.path.join(REPO_ROOT, "tests", "memory_stress_test.py")


def _base_env(extra: dict[str, str] | None = None, pop_lw: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    env["TOKENIZERS_PARALLELISM"] = "false"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44g-verify-0000"
    env["GRAFO_LLM_MODEL"] = "none"
    if pop_lw:
        env.pop("GRAFO_LIGHTWEIGHT_MODE", None)
    if extra:
        env.update(extra)
    return env


def check_consumers_and_guards() -> str:
    targets = [
        "tests/memory_stress_test.py",
        "tests/test_chunk_cache.py",
        "tests/test_ignore.py",
        "tests/test_lightweight.py",
        "tests/test_stress_components_reuse.py",
        "tests/test_domain_neutrality_guard.py",
    ]
    lines = ["=== BLOCO 2/3 (RODADA 4.4g): CONSUMIDORES DE stress_components E GUARDAS ==="]
    for py_tag, py_exe in [("py310", PY310), ("py312", PY312)]:
        for ord_tag, extra_flags in [("normal", []), ("reverse", ["--reverse"])]:
            cmd = [py_exe, "-m", "pytest"] + targets + extra_flags + ["-v", "--tb=short"]
            p = subprocess.run(cmd, cwd=REPO_ROOT, env=_base_env(), capture_output=True, text=True, encoding="utf-8")
            lines.append(f"\n--- {py_tag} ({ord_tag}) | RC={p.returncode} ---")
            lines.append(p.stdout.strip())
            if p.stderr.strip():
                lines.append("STDERR:\n" + p.stderr.strip())
            assert p.returncode == 0, f"Falha em consumidores/guardas ({py_tag}, {ord_tag}):\n{p.stdout}\n{p.stderr}"

    # Rodar prova M10d (check_mcp_globals_leak + hook de baseline) e restaurar evidência da 4.4d
    raw_m10d = subprocess.check_output(["git", "show", "HEAD:scratch/evidencia_4_4d/mutacao_M10d_import.txt"], cwd=REPO_ROOT)
    p_m10d = subprocess.run(
        [PY312, "scratch/run_bloco2_4_4d_mutation.py"],
        cwd=REPO_ROOT,
        env=_base_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    with open(os.path.join(REPO_ROOT, "scratch", "evidencia_4_4d", "mutacao_M10d_import.txt"), "wb") as fm:
        fm.write(raw_m10d)
    lines.append(f"\n--- Guarda M10d / check_mcp_globals_leak (Py3.12) | RC={p_m10d.returncode} ---")
    lines.append(p_m10d.stdout.strip())
    assert p_m10d.returncode == 0

    out = "\n".join(lines) + "\n"
    with open(os.path.join(EV_DIR, "bloco2_consumers_and_guards.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    return out


def check_env_restoration() -> str:
    code = (
        "import os, sys; sys.path.insert(0, '.'); "
        "from tests.test_stress_components_reuse import ("
        "test_stress_components_reuse_cycle_characterization, "
        "test_bootstrap_uses_distinct_chroma_subdir_per_call); "
        "os.environ.pop('GRAFO_LIGHTWEIGHT_MODE', None); "
        "test_stress_components_reuse_cycle_characterization(); "
        "after_unset_1 = os.environ.get('GRAFO_LIGHTWEIGHT_MODE'); "
        "assert after_unset_1 is None, f'Vazou env: {after_unset_1}'; "
        "os.environ['GRAFO_LIGHTWEIGHT_MODE'] = 'true'; "
        "test_bootstrap_uses_distinct_chroma_subdir_per_call(); "
        "after_set_2 = os.environ.get('GRAFO_LIGHTWEIGHT_MODE'); "
        "assert after_set_2 == 'true', f'Nao restaurou env: {after_set_2}'; "
        "print(f'Env restoration OK: after_unset={after_unset_1!r}, after_true={after_set_2!r}')"
    )
    p = subprocess.run([PY310, "-c", code], cwd=REPO_ROOT, env=_base_env(pop_lw=True), capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, f"Falha env restoration:\n{p.stdout}\n{p.stderr}"
    return p.stdout.strip()


def check_mutation() -> str:
    with open(STRESS_FILE, "r", encoding="utf-8") as f:
        orig_src = f.read()

    old_block = (
        '    chroma_dir = os.path.join(CHROMA_PATH, f"run_{uuid.uuid4().hex}")\n'
        '    vector = ChromaVectorStore(\n'
        '        persist_dir=chroma_dir,'
    )
    mut_block = (
        '    vector = ChromaVectorStore(\n'
        '        persist_dir=CHROMA_PATH,'
    )
    assert old_block in orig_src, "Trecho alvo de mutação não encontrado em tests/memory_stress_test.py"

    mut_src = orig_src.replace(old_block, mut_block, 1)

    lines = [
        "=== BLOCO 3 (RODADA 4.4g): MUTAÇÃO EXTERNA (REINTRODUZIR persist_dir=CHROMA_PATH FIXO EM bootstrap) ===",
        "Objetivo: comprovar separadamente (a) o comportamento do teste de caracterização do ciclo de reuso e "
        "(b) a proteção estrutural da medida defensiva do Bloco 2.",
    ]

    try:
        with open(STRESS_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(mut_src)

        for test_node in [
            "tests/test_stress_components_reuse.py::test_stress_components_reuse_cycle_characterization",
            "tests/test_stress_components_reuse.py::test_bootstrap_uses_distinct_chroma_subdir_per_call",
        ]:
            p_mut = subprocess.run(
                [PY310, "-m", "pytest", test_node, "-v", "--tb=short"],
                cwd=REPO_ROOT,
                env=_base_env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            lines.append(f"\n--- COM MUTAÇÃO | {test_node} | RC={p_mut.returncode} ---")
            lines.append(p_mut.stdout.strip())
            if test_node.endswith("characterization"):
                assert p_mut.returncode == 0, "Esperava caracterização PASSANDO com mutação (0/60 local)."
            else:
                assert p_mut.returncode != 0, "Esperava teste estrutural FALHANDO com mutação!"
    finally:
        with open(STRESS_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(orig_src)

    # Sem mutação: ambos devem passar
    p_clean = subprocess.run(
        [PY310, "-m", "pytest", "tests/test_stress_components_reuse.py", "-v", "--tb=short"],
        cwd=REPO_ROOT,
        env=_base_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines.append(f"\n--- SEM MUTAÇÃO (código corrigido) | tests/test_stress_components_reuse.py | RC={p_clean.returncode} ---")
    lines.append(p_clean.stdout.strip())
    assert p_clean.returncode == 0

    lines.append("\n--- RESTAURAÇÃO DE AMBIENTE ---")
    lines.append(check_env_restoration())

    out = "\n".join(lines) + "\n"
    with open(os.path.join(EV_DIR, "bloco3_mutation_and_env.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    return out


def main() -> None:
    c_out = check_consumers_and_guards()
    m_out = check_mutation()
    print(c_out)
    print(m_out)
    print("Verificação dos Blocos 2 e 3 concluída com sucesso.")


if __name__ == "__main__":
    main()

