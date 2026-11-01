from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROADMAP = REPO_ROOT / "audits" / "fase4-roadmap.md"
ACHADOS = REPO_ROOT / "audits" / "fase4-achados.md"


def update_roadmap():
    txt = ROADMAP.read_bytes().decode("utf-8")
    target = "| 4.2f | `17f046e`, `a64f5f1` | Correção F4-017: Opção A (desacoplamento de fd 0 no Windows); E2E definitivo 20/20 OK | Concluída | — |\r\n"
    replacement = (
        "| 4.2f | `17f046e`, `a64f5f1` | Correção F4-017: Opção A (desacoplamento de fd 0 no Windows); E2E 1.27.0 OK (1.30.0 rodou sem chromadb, ver `errata-4-2f.md`) | Concluída (com errata na 4.2g) | Sim (4 lacunas apontadas para 4.2g) |\r\n"
        "| 4.2g | `6defadc`, `5b173fd`, `30d65c1` | Fechamento das 4 lacunas da 4.2f: remoção D5 frágil + skip explícito D1; docstring separando PROVADO/HIPÓTESE (AST idêntico); E2E `mcp 1.30.0` completo (10/10 OK, 13 vetores) + controle `dd92d35` (6/6 TRAVOU); CI Windows (`.github/workflows/windows-stdin.yml`) | Concluída | — |\r\n"
    )
    assert target in txt, "Target 4.2f not found in fase4-roadmap.md"
    txt = txt.replace(target, replacement, 1)

    target_f4017 = "| F4-017 | 1ª chamada que usa o modelo trava dentro do servidor MCP no Windows (deadlock CRT fd 0) | CRÍTICA | corrigido pelo executor, aguardando verificação independente | `main.py:108-144`, `tests/test_stdin_decouple.py`; provas em `scratch/evidencia_4_2f/` (20/20 OK) |\r\n"
    replacement_f4017 = "| F4-017 | 1ª chamada que usa o modelo trava dentro do servidor MCP no Windows (leitor bloqueado em fd 0) | CRÍTICA | corrigido pelo executor, aguardando verificação independente | `main.py:111-146`, `tests/test_stdin_decouple.py`, `.github/workflows/windows-stdin.yml`; provas em `scratch/evidencia_4_2f/` e `scratch/evidencia_4_2g/` |\r\n"
    assert target_f4017 in txt, "Target F4-017 not found in fase4-roadmap.md"
    txt = txt.replace(target_f4017, replacement_f4017, 1)

    ROADMAP.write_bytes(txt.encode("utf-8"))
    print("Updated audits/fase4-roadmap.md")


def update_achados():
    txt = ACHADOS.read_bytes().decode("utf-8")
    target_f4015 = "- **Status:** **corrigido pelo executor, aguardando verificação independente** (Commits `34ad6d5`, `8366860`, `17f046e`). Os testes de lazy import da 4.2d (T1 a T5) continuam preservados e 100% verdes (D5 em `tests/test_stdin_decouple.py`). A Opção A adotada na 4.2f não exigiu aquecimento.\r\n"
    replacement_f4015 = "- **Status:** **corrigido pelo executor, aguardando verificação independente** (Commits `34ad6d5`, `8366860`, `17f046e`, `6defadc`, `30d65c1`). Os testes de lazy import da 4.2d (T1 a T5 em `tests/test_lazy_ml_imports.py`) continuam preservados, 100% verdes e integrados ao workflow `.github/workflows/windows-stdin.yml` (o D5 duplicado e frágil em `tests/test_stdin_decouple.py` foi removido na 4.2g). A Opção A adotada na 4.2f não exigiu aquecimento.\r\n"
    assert target_f4015 in txt, "Target F4-015 status not found in fase4-achados.md"
    txt = txt.replace(target_f4015, replacement_f4015, 1)

    target_f4017_block = txt[txt.index("### [F4-017]"):]
    new_f4017_block = (
        "### [F4-017] 1ª chamada que usa o modelo trava dentro do servidor MCP no Windows (leitor bloqueado em fd 0)\r\n"
        "- **Status:** **corrigido pelo executor, aguardando verificação independente** (Commits `17f046e`, `a64f5f1`, `6defadc`, `5b173fd`, `30d65c1`).\r\n"
        "- **Severidade:** 🔴 CRÍTICA (Bloqueio total do servidor MCP stdio na 1ª requisição que importa bibliotecas nativas com leitor bloqueado em fd 0 no Windows).\r\n"
        "- **Arquivos & Linhas:** [`main.py:111-146, 252-258`](file:///c:/Nexus-Memory/GrafoConcierge/main.py#L111-L146), [`tests/test_stdin_decouple.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_stdin_decouple.py), [`.github/workflows/windows-stdin.yml`](file:///c:/Nexus-Memory/GrafoConcierge/.github/workflows/windows-stdin.yml)\r\n"
        "- **Fatos Provados vs. Hipótese Não Demonstrada:**\r\n"
        "  - **PROVADO (`scratch/evidencia_4_2e`, `4_2f` e `4_2g`):** Com uma thread leitora bloqueada em `fd 0` do `stdin` (`sys.stdin.buffer.readline()`), o primeiro import tardio de bibliotecas nativas (`scipy.special`, `openblas`, `torch`, `sentence_transformers`) trava no Windows com CPU em ~0,0%; desacoplar o `fd 0` antes de iniciar o transporte stdio elimina o travamento.\r\n"
        "  - **HIPÓTESE NÃO DEMONSTRADA:** O mecanismo interno do Windows (sincronização/lock interno do CRT ou do loader em `LoadLibraryExW`).\r\n"
        "- **Técnica Adotada (Opção A — Desacoplamento de fd 0):**\r\n"
        "  Implementada a função `decouple_stdin_from_fd0() -> bool` em `main.py`, invocada antes de iniciar o transporte FastMCP stdio no Windows (`TRANSPORT == \"stdio\"`). A função:\r\n"
        "  1. Duplica o descritor herdado do pai (`fd2 = os.dup(0)`);\r\n"
        "  2. Redireciona o `fd 0` para o dispositivo nulo (`os.dup2(os.open(os.devnull, os.O_RDONLY), 0)`);\r\n"
        "  3. Reatribui `sys.stdin` a um fluxo de texto envolvendo `fd2` (`closefd=False`).\r\n"
        "- **Comprovações Experimentais e Evidências (Rodadas 4.2f e 4.2g):**\r\n"
        "  1. **Testes Unitários e Integração (D1–D4 em `tests/test_stdin_decouple.py`):** 4/4 passam no ambiente principal Windows (`scratch/evidencia_4_2g/item1_d_green_main_venv.txt`) e 3 passam + 1 skip explícito (D1 sem `scipy.special`) em venv mínimo sem ML (`scratch/evidencia_4_2g/item1_d_green_venv_min.txt`).\r\n"
        "  2. **Docstring e Prova de AST Idêntico (Item 2 da 4.2g):** Docstring retificada em `5b173fd` sem alterar nenhuma linha de código executável (`ast.dump` sem docstrings idêntico entre `21610d8` e `5b173fd` em `scratch/evidencia_4_2g/item2_ast_proof.txt`).\r\n"
        "  3. **Teste Definitivo E2E em `mcp 1.27.0` (4.2f) e `mcp 1.30.0` completo (4.2g Item 3c):**\r\n"
        "     - Em `mcp 1.27.0` (`venv_mcp127`, 4.2f): 10/10 OK (5 `search-first` + 5 `mine`, `scratch/evidencia_4_2f/tabela_passo4e.txt`; `pip freeze` registrado em `scratch/evidencia_4_2g/item3_venv_mcp127_pip_freeze.txt`). *(Nota: as 10 execuções de `mcp 1.30.0` da 4.2f rodaram sem `chromadb` em modo `NO-OP`, conforme registrado em `audits/errata-4-2f.md`).*\r\n"
        "     - Em `mcp 1.30.0` completo (`venv_mcp130_full`, 4.2g Item 3c, com `chromadb=1.5.9`, `sentence_transformers=5.4.1`, `scipy=1.17.1`, `numpy=2.4.4`, `torch=2.11.0`): **10/10 OK** (`0 TRAVOU`, `0 INVÁLIDA`, `13 vetores` no Chroma após cada `mine`, `NO-OP=False`, `scratch/evidencia_4_2g/item3_tabela_head_mcp130.txt`).\r\n"
        "  4. **Controle Negativo no Commit `dd92d35` (4.2f Passo 4f e 4.2g Item 3d):** No mesmo `venv_mcp130_full` completo ($n=3$ `search-first` + $n=3$ `mine`, timeout 180s), **6/6 TRAVOU** (`0 OK`, `CPU=0.0%`, `scratch/evidencia_4_2g/item3_tabela_control_dd92d35.txt`), confirmando que o ambiente exercita o travamento real e que o desacoplamento em `HEAD` o elimina.\r\n"
        "  5. **CI Windows (`.github/workflows/windows-stdin.yml`, 4.2g Item 4):** Matriz executada em `windows-latest` com Python 3.10, 3.12 e 3.14 (`scratch/evidencia_4_2g/item4_gh_run_main.txt` e teste de mutação na branch descartável `ci-mutacao-4-2g` em `scratch/evidencia_4_2g/item4_gh_run_mutacao.txt`).\r\n"
    )
    txt = txt.replace(target_f4017_block, new_f4017_block, 1)
    ACHADOS.write_bytes(txt.encode("utf-8"))
    print("Updated audits/fase4-achados.md")


if __name__ == "__main__":
    update_roadmap()
    update_achados()

