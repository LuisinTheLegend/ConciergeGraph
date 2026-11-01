# Errata da Rodada 4.2f (`audits/relatorio_4_2f.md`)

> **Data:** 2026-10-31  
> **Referência:** Auditoria independente do commit `21610d8` (Rodada 4.2f) e correções aplicadas na Rodada 4.2g.

---

## 1. Execução E2E do Passo 4e em `mcp 1.30.0` rodou sem `chromadb` (modo `NO-OP`)

- **O que foi afirmado na 4.2f:** O relatório da 4.2f afirmou que o teste definitivo E2E (Passo 4e) obteve `20/20 OK` exercitando o caminho completo tanto em `mcp 1.27.0` quanto em `mcp 1.30.0`.
- **Correção factual:** O resultado `20/20` da 4.2f valia plenamente **apenas para as 10 execuções em `mcp 1.27.0`** (`venv_mcp127`, onde `chromadb` estava instalado e a mineração levou ~32–34 s). No ambiente `venv_mcp130_real` (`mcp 1.30.0`), o pacote `chromadb` não estava instalado (`WARNING | chromadb not installed` e `WARNING | ChromaVectorStore operating in NO-OP mode`, visível em `scratch/evidencia_4_2f/boot_check_mcp130.txt`), o que reduziu a carga e o tempo de mineração para ~10 s e não exercitou o armazenamento vetorial real no Chroma.
- **Resolução na 4.2g (Item 3):** Criado `venv_mcp130_full` com `mcp==1.30.0` e todas as dependências do projeto (`chromadb`, `sentence-transformers`, `scipy`, `numpy`, `torch`), validando em cada `result.json` as versões instaladas, a ausência de `"NO-OP"` / `"not installed"` no `stderr`, a contagem real de vetores (`count_embeddings > 0`) após `mine`, e o controle negativo no commit `dd92d35`.

---

## 2. Fragilidade do Teste `D5` em `tests/test_stdin_decouple.py`

- **O que ocorria na 4.2f:** O teste `test_d5_lazy_ml_imports_remain_green` (D5) invocava `pytest tests/test_lazy_ml_imports.py -k "test_t1 or test_t2" -q` em subprocesso e exigia literalmente `assert "2 passed" in res.stdout`. Em qualquer ambiente sem `sentence_transformers` instalado, `T1` e `T2` são legitimamente pulados (`2 skipped`), fazendo o `D5` falhar por asserção de string.
- **Resolução na 4.2g (Item 1):** Reproduzida a falha em venv limpo sem `sentence_transformers` (`scratch/evidencia_4_2g/item1_d5_red.txt`) e removido o `D5` de `tests/test_stdin_decouple.py` (pois apenas duplicava `T1`/`T2`, que já fazem parte de `tests/test_lazy_ml_imports.py`), adicionando também guarda de skip explícita em `D1` quando `scipy.special` não está instalado.

---

## 3. Docstring de `decouple_stdin_from_fd0` em `main.py` afirmava mecanismo interno como fato

- **O que ocorria na 4.2f:** A docstring de `decouple_stdin_from_fd0()` em `main.py` continha a afirmação `"acquire an internal CRT file lock on open stdio descriptors"`, apresentando como fato provado um mecanismo interno do Windows/CRT que não foi demonstrado diretamente.
- **Resolução na 4.2g (Item 2):** A docstring em `main.py` foi reescrita separando explicitamente o que está **PROVADO** (`scratch/evidencia_4_2e` e `scratch/evidencia_4_2f`: com leitor bloqueado em `fd 0` do `stdin`, o primeiro import de bibliotecas nativas como `scipy.special`, `openblas` e `torch` trava no Windows, e desacoplar o `fd 0` elimina o travamento) do que permanece **HIPÓTESE NÃO DEMONSTRADA** (o mecanismo interno de lock do CRT / loader do Windows). Provado via `ast.dump` sem docstrings (`scratch/evidencia_4_2g/item2_ast_proof.txt`) que zero linhas de código executável mudaram em `main.py`.

