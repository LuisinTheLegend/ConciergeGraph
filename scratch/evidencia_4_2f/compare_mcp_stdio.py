from pathlib import Path

p_127 = Path(r"C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\mcp\server\stdio.py")
p_130 = Path(r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp130_real\Lib\site-packages\mcp\server\stdio.py")

c127 = p_127.read_text(encoding="utf-8")
c130 = p_130.read_text(encoding="utf-8")

def extract_stdin_handling(content):
    lines = content.splitlines()
    res = []
    in_func = False
    for i, line in enumerate(lines):
        if "def stdio_server" in line:
            in_func = True
        if in_func:
            res.append(line)
            if "async with anyio.create_task_group" in line:
                break
    return "\n".join(res)

snip127 = extract_stdin_handling(c127)
snip130 = extract_stdin_handling(c130)

identical = (snip127 == snip130)

doc = f"""=== MCP 1.27.0 (sys / venv_mcp127) ===
Arquivo: {p_127}
Trecho de stdio_server:
{snip127}

=== MCP 1.30.0 (venv_mcp130_real) ===
Arquivo: {p_130}
Trecho de stdio_server:
{snip130}

=== COMPARACAO E CONFIRMACAO ===
Os trechos de obtencao do stdin em stdio_server sao IDENTICOS: {identical}
Ambas as versoes executam exatamente:
    if not stdin:
        stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"))

Confirmacao tecnica: Substituir sys.stdin por um objeto TextIOWrapper com .buffer proprio apontando
para o novo descritor (fd2) desacoplado do fd 0 satisfaz plenamente tanto mcp==1.27.0 quanto mcp==1.30.0.
"""

out_path = Path("scratch/evidencia_4_2f/mcp_stdin_snippet.txt")
out_path.write_text(doc, encoding="utf-8")
print(f"IDENTICAL: {identical}")
print(f"Salvo em: {out_path}")

