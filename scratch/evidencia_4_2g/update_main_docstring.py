from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_PATH = REPO_ROOT / "main.py"

OLD_DOC = (
    '    """Decouples fd 0 from sys.stdin on Windows to prevent CRT/OpenBLAS hang.\r\n'
    '\r\n'
    '    On Windows, late imports (e.g. scipy.special / OpenBLAS) acquire an internal CRT\r\n'
    '    file lock on open stdio descriptors. If a background reader thread is blocked\r\n'
    '    in sys.stdin.buffer.readline() on fd 0, LoadLibraryExW hangs permanently.\r\n'
    '    Redirecting fd 0 to os.devnull and wrapping the duplicated fd2 into sys.stdin\r\n'
    '    avoids the lock collision while preserving bidirectional MCP stdio communication.\r\n'
    '    """'
)

NEW_DOC = (
    '    """Desacopla o fd 0 de sys.stdin no Windows para evitar travamento em imports nativos tardios.\r\n'
    '\r\n'
    '    - PROVADO (ver scratch/evidencia_4_2e e scratch/evidencia_4_2f): com um leitor\r\n'
    '      bloqueado em fd 0 do stdin (ex.: sys.stdin.buffer.readline()), o primeiro\r\n'
    '      import de bibliotecas nativas (scipy.special, openblas, torch) trava no\r\n'
    '      Windows; desacoplar o fd 0 (redirecionando fd 0 para os.devnull e envolvendo\r\n'
    '      o descritor duplicado fd2 em sys.stdin) elimina o travamento preservando o\r\n'
    '      canal stdio bidirecional do MCP.\r\n'
    '    - HIPÓTESE NÃO DEMONSTRADA: o mecanismo interno do Windows (lock do CRT / loader).\r\n'
    '    """'
)


def main():
    raw = MAIN_PATH.read_bytes().decode("utf-8")
    assert OLD_DOC in raw, "OLD_DOC not found in main.py"
    updated = raw.replace(OLD_DOC, NEW_DOC, 1)
    MAIN_PATH.write_bytes(updated.encode("utf-8"))
    print("Docstring updated preserving CRLF.")


if __name__ == "__main__":
    main()

