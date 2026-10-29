# update_all_tables.py
# Le todos os arquivos JSON ja gravados em e1_isolation, e2_loops e e3_mcp
# e gera as tabelas tabela_e1.txt, tabela_e2.txt e tabela_e3.txt

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def update_e1():
    out_dir = HERE / "e1_isolation"
    table_out = HERE / "tabela_e1.txt"
    results = []
    for f in sorted(out_dir.glob("*__rep*/result.json")):
        try:
            results.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    if not results:
        return
    results.sort(key=lambda x: (x.get("case", ""), x.get("rep", 0)))
    lines = []
    lines.append("=" * 95)
    lines.append("TABELA EXPERIMENTO E1 — ISOLAMENTO SEM MCP E SEM ASYNCIO (PIPE STDIN ABERTO)")
    lines.append("=" * 95)
    lines.append(f"{'Caso':<28} | {'Rep':<4} | {'Status':<8} | {'Tempo (s)':<10} | {'Reader Blocked':<15} | Detalhes")
    lines.append("-" * 95)
    for r in results:
        lines.append(f"{r.get('case',''):<28} | {r.get('rep',0):<4} | {r.get('classe',''):<8} | {r.get('time_s',0):<10.2f} | {str(r.get('reader_blocked',False)):<15} | rc={r.get('returncode','')}")
    lines.append("=" * 95)

    cases = sorted(list(set(r.get("case", "") for r in results)))
    lines.append("\nRESUMO ESTATÍSTICO DO EXPERIMENTO E1 (REPETIÇÕES CONCLUÍDAS):")
    lines.append("-" * 65)
    for c in cases:
        subset = [r for r in results if r.get("case") == c]
        total = len(subset)
        oks = sum(1 for r in subset if r.get("classe") == "OK")
        travou = sum(1 for r in subset if r.get("classe") == "TRAVOU")
        erros = sum(1 for r in subset if r.get("classe") not in ("OK", "TRAVOU"))
        lines.append(f"Caso {c:<26} | OK: {oks}/{total} | TRAVOU: {travou}/{total} | ERRO: {erros}/{total}")
    lines.append("=" * 95)
    table_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Atualizado {table_out} com {len(results)} registros.")

def update_e2():
    out_dir = HERE / "e2_loops"
    table_out = HERE / "tabela_e2.txt"
    results = []
    for f in sorted(out_dir.glob("*__rep*/result.json")):
        try:
            results.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    if not results:
        return
    results.sort(key=lambda x: (x.get("variant", ""), x.get("rep", 0)))
    lines = []
    lines.append("=== TABELA EXPERIMENTO E2: LOOP DE EVENTOS COM STDIN ABERTO ===")
    lines.append(f"{'Variante':<20} | {'Rep':<4} | {'Classe':<8} | {'Tempo(s)':<9} | {'Reader Blocked':<15} | {'Import OK':<10}")
    lines.append("-" * 75)
    for r in results:
        lines.append(
            f"{r.get('variant',''):<20} | {r.get('rep',0):<4} | {r.get('classe',''):<8} | {r.get('time_s',0):<9.2f} | "
            f"{str(r.get('reader_blocked',False)):<15} | {str(r.get('import_ok',False)):<10}"
        )
    lines.append("-" * 75)
    table_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Atualizado {table_out} com {len(results)} registros.")

def update_e3():
    out_dir = HERE / "e3_mcp"
    table_out = HERE / "tabela_e3.txt"
    results = []
    for f in sorted(out_dir.glob("*__rep*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # Extrai venv e variant do nome se nao estiver dentro
            parts = f.stem.split("__")
            if len(parts) >= 3:
                data.setdefault("venv", parts[0])
                data.setdefault("variant", parts[1])
                data.setdefault("rep", int(parts[2].replace("rep", "")))
            results.append(data)
        except Exception:
            pass
    if not results:
        return
    results.sort(key=lambda x: (x.get("venv", ""), x.get("variant", ""), x.get("rep", 0)))
    lines = []
    lines.append("=== TABELA EXPERIMENTO E3: MCP MINIMO COM VERSOES CORRETAS ===")
    lines.append(f"{'Venv':<10} | {'Variante':<26} | {'Rep':<4} | {'Classe':<8} | {'Tempo(s)':<9} | {'CPU Media(%)':<14} | {'Trace Dump'}")
    lines.append("-" * 90)
    for r in results:
        trace_path = out_dir / f"trace__{r.get('venv','')}__{r.get('variant','')}__rep{r.get('rep',0)}.txt"
        has_trace = "SIM" if trace_path.exists() and trace_path.stat().st_size > 0 else "NAO"
        lines.append(
            f"{r.get('venv',''):<10} | {r.get('variant',''):<26} | {r.get('rep',0):<4} | {r.get('classe','ERRO'):<8} | "
            f"{r.get('total_s', 0):<9.2f} | {r.get('mean_cpu', 0.0):<14.2f} | {has_trace}"
        )
    lines.append("-" * 90)
    table_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Atualizado {table_out} com {len(results)} registros.")

if __name__ == "__main__":
    update_e1()
    update_e2()
    update_e3()
