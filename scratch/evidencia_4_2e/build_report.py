"""
build_report.py - Lê os arquivos de evidência gerados e produz o relatório consolidado da Rodada 4.2e Revisada.
Salva em scratch/evidencia_4_2e/relatorio_final.txt e imprime na saída padrão.
"""
from pathlib import Path
import os
import sys

EV_DIR = Path(r"c:\Nexus-Memory\GrafoConcierge\scratch\evidencia_4_2e")
REPORT_FILE = EV_DIR / "relatorio_final.txt"

def read_file_safe(path: Path) -> str:
    if not path.exists():
        return f"[ARQUIVO NÃO ENCONTRADO: {path.name}]"
    return path.read_text(encoding="utf-8", errors="replace").strip()

def build_report() -> str:
    parts = []
    parts.append("==========================================================================================")
    parts.append("RELATÓRIO CONSOLIDADO — RODADA 4.2e (REVISADA) — DIAGNÓSTICO DO TRAVAMENTO NO MCP")
    parts.append("==========================================================================================")
    parts.append("Papel: executor | Regras: 2, 3, 4, 7, 10, 11, 12 | Status: CONCLUÍDO (SUSPENSÃO DA 4.2e ORIGINAL)")
    parts.append("==========================================================================================\n")

    parts.append("1. AMBIENTE E VERSÕES (scratch/evidencia_4_2e/ambiente.txt):")
    parts.append("-" * 90)
    parts.append(read_file_safe(EV_DIR / "ambiente.txt"))
    parts.append("\n" + "=" * 90 + "\n")

    parts.append("2. CONTROLE DE REGRESSÃO (Passo 2 — scratch/evidencia_4_2e/tabela_passo2.txt):")
    parts.append("-" * 90)
    parts.append(read_file_safe(EV_DIR / "tabela_passo2.txt"))
    parts.append("\n" + "=" * 90 + "\n")

    parts.append("3. REPRODUÇÃO MÍNIMA ISOLADA SEM O CONCIERGE (Passo 3 — scratch/evidencia_4_2e/tabela_passo3.txt):")
    parts.append("-" * 90)
    parts.append(read_file_safe(EV_DIR / "tabela_passo3.txt"))
    parts.append("\n" + "=" * 90 + "\n")

    parts.append("4. TESTE DE VARIÁVEIS DE AMBIENTE BLAS/OMP (Passo 4 — scratch/evidencia_4_2e/tabela_passo4.txt):")
    parts.append("-" * 90)
    parts.append(read_file_safe(EV_DIR / "tabela_passo4.txt"))
    parts.append("\n" + "=" * 90 + "\n")

    parts.append("5. PREPARAÇÃO DO COMANDO PARA EXECUÇÃO PELO DONO (Passo 5):")
    parts.append("-" * 90)
    parts.append("Script disponível: scratch/evidencia_4_2e/run_owner_check.py")
    parts.append("Comando para execução manual interativa no PowerShell:")
    parts.append("  python scratch\\evidencia_4_2e\\run_owner_check.py")
    parts.append("Arquivos gerados pela execução do dono:")
    parts.append("  - scratch/evidencia_4_2e/resultado_dono.json")
    parts.append("  - scratch/evidencia_4_2e/resultado_dono.txt")
    parts.append("\n" + "=" * 90 + "\n")

    parts.append("6. REGISTRO DE ACHADO (Passo 6):")
    parts.append("-" * 90)
    parts.append("Achado PROVISÓRIO registrado em audits/fase4-achados.md:")
    parts.append("  - Código: [F4-017]")
    parts.append("  - Título: 1ª chamada que usa o modelo trava dentro do servidor MCP no ambiente do agente (n pequeno)")
    parts.append("  - Status: NÃO CONFIRMADO")
    parts.append("  - Severidade: (A definir pelo dono/auditor)")
    parts.append("  - Status de F4-015 inalterado.")
    parts.append("\n" + "=" * 90 + "\n")

    parts.append("7. INTERPRETAÇÃO DOS DADOS (HIPÓTESES TÉCNICAS):")
    parts.append("-" * 90)
    parts.append("a) [HIPÓTESE NÃO CONFIRMADA FORA DO AGENTE]: O travamento decorre de uma restrição no runtime do")
    parts.append("   Windows quando o ProactorEventLoop do asyncio / pipes do stdio do MCP estão ativos e uma extensão C")
    parts.append("   compilada em Fortran/C (scipy.special._ufuncs) é carregada tardiamente durante a chamada de ferramenta.")
    parts.append("b) [FATO COMPROVADO]: O travamento é independente do Grafo Concierge — ocorre identicamente num servidor")
    parts.append("   FastMCP mínimo isolado de 10 linhas sob mcp 1.27.0 e mcp 1.30.0.")
    parts.append("c) [FATO COMPROVADO]: Quando o import é realizado no topo do script (pré-import), o servidor atende")
    parts.append("   normalmente em ~0.01s por chamada.")
    parts.append("d) [FATO COMPROVADO]: Restringir threads BLAS/OMP para 1 não evita o travamento.")
    parts.append("==========================================================================================")

    return "\n".join(parts) + "\n"

def main():
    content = build_report()
    REPORT_FILE.write_text(content, encoding="utf-8")
    print(content)

if __name__ == "__main__":
    main()
