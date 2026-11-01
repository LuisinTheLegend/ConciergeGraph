"""Execute the 4 mandatory mutations of Bloco 1 and record the resulting test failures."""
import os
import pathlib
import subprocess
import sys

out_dir = pathlib.Path("scratch/evidencia_4_2i")
py_exe = r"C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe"
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["GRAFO_LLM_API_KEY"] = "AQ.FAKEFAKEFAKE0001"

# ---------------------------------------------------------------------------
# MUTATION 1: Voltar o esquema para 3 colunas
# ---------------------------------------------------------------------------
p_schema = pathlib.Path("storage/schema.py")
orig_schema = p_schema.read_bytes()
try:
    print("[Mutation 1] Reverting schema to 3 columns (dropping content)...")
    mut_schema = orig_schema.decode("utf-8").replace(
        "label, tags, summary, content, content='nodes', content_rowid='id'",
        "label, tags, summary, content='nodes', content_rowid='id'",
        1,
    )
    p_schema.write_bytes(mut_schema.encode("utf-8"))

    r1 = subprocess.run(
        [py_exe, "-m", "pytest", "tests/test_fts_code_search.py", "-k", "test_sentinel_words_found_in_content_when_summary_is_null", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    (out_dir / "b1_mut1_3_columns.txt").write_text(
        f"# Mutacao 1: Reverter nodes_fts para 3 colunas (sem 'content')\n"
        f"[returncode={r1.returncode}]\n{r1.stdout}{r1.stderr}",
        encoding="utf-8",
    )
    print(f"  Mutation 1 finished with rc={r1.returncode} (expected 1)")
finally:
    p_schema.write_bytes(orig_schema)

# ---------------------------------------------------------------------------
# MUTATION 2: Remover o escape de FTS5
# ---------------------------------------------------------------------------
p_logic = pathlib.Path("storage/logic.py")
orig_logic = p_logic.read_bytes()
try:
    print("[Mutation 2] Removing FTS5 escaping in fts_search...")
    text_l = orig_logic.decode("utf-8")
    target_l = "and_query, or_query = self._build_fts5_queries(query)"
    assert target_l in text_l, f"Target '{target_l}' not found in storage/logic.py"
    # Bypass parser and pass unescaped raw query directly into MATCH
    mut_logic = text_l.replace(
        target_l,
        "and_query, or_query = query, None",
        1,
    )
    assert mut_logic != text_l
    p_logic.write_bytes(mut_logic.encode("utf-8"))

    r2 = subprocess.run(
        [py_exe, "-m", "pytest", "tests/test_fts_code_search.py", "-k", "test_fts5_injection_safety", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    (out_dir / "b1_mut2_no_fts5_escape.txt").write_text(
        f"# Mutacao 2: Remover o escape de FTS5 e passar a query crua\n"
        f"[returncode={r2.returncode}]\n{r2.stdout}{r2.stderr}",
        encoding="utf-8",
    )
    print(f"  Mutation 2 finished with rc={r2.returncode} (expected 1)")
finally:
    p_logic.write_bytes(orig_logic)

# ---------------------------------------------------------------------------
# MUTATION 3: Remover a restrição de search_symbols à coluna label
# ---------------------------------------------------------------------------
p_store = pathlib.Path("storage/store.py")
orig_store = p_store.read_bytes()
try:
    print("[Mutation 3] Removing 'label :' column restriction in search_symbols...")
    mut_store = orig_store.decode("utf-8").replace(
        'params: list[Any] = [f\'label : "{safe_query}"\']',
        'params: list[Any] = [f\'"{safe_query}"\']',
        1,
    )
    p_store.write_bytes(mut_store.encode("utf-8"))

    r3 = subprocess.run(
        [py_exe, "-m", "pytest", "tests/test_fts_code_search.py", "-k", "test_search_symbols_restricted_to_label_regression", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    (out_dir / "b1_mut3_search_symbols_no_label_restriction.txt").write_text(
        f"# Mutacao 3: Remover restricao 'label :' em search_symbols\n"
        f"[returncode={r3.returncode}]\n{r3.stdout}{r3.stderr}",
        encoding="utf-8",
    )
    print(f"  Mutation 3 finished with rc={r3.returncode} (expected 1)")
finally:
    p_store.write_bytes(orig_store)

# ---------------------------------------------------------------------------
# MUTATION 4: Remover o fallback OR
# ---------------------------------------------------------------------------
try:
    print("[Mutation 4] Removing fallback OR query execution in fts_search...")
    mut_logic4 = orig_logic.decode("utf-8").replace(
        "if not rows and or_query:",
        "if False and or_query:",
        1,
    )
    p_logic.write_bytes(mut_logic4.encode("utf-8"))

    r4 = subprocess.run(
        [py_exe, "-m", "pytest", "tests/test_fts_code_search.py", "-k", "test_multiword_and_fallback_to_or", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    (out_dir / "b1_mut4_no_or_fallback.txt").write_text(
        f"# Mutacao 4: Desabilitar o fallback OR em fts_search\n"
        f"[returncode={r4.returncode}]\n{r4.stdout}{r4.stderr}",
        encoding="utf-8",
    )
    print(f"  Mutation 4 finished with rc={r4.returncode} (expected 1)")
finally:
    p_logic.write_bytes(orig_logic)

print("All 4 mutations completed successfully!")
