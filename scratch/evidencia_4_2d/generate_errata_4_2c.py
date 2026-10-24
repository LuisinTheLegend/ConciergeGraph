"""
scratch/evidencia_4_2d/generate_errata_4_2c.py — Gera audits/errata-4-2c.md
mecanicamente a partir dos arquivos de scratch/evidencia_4_2c/ (Regra 12).
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
EVIDENCIA_4_2C = REPO_ROOT / "scratch" / "evidencia_4_2c"


def extract_metrics(filepath: Path) -> dict[str, str]:
    if not filepath.exists():
        return {}
    txt = filepath.read_text(encoding="utf-8", errors="replace")

    def get(pat):
        m = re.search(pat, txt)
        return m.group(1) if m else "N/A"

    return {
        "st": get(r"import: sentence_transformers\s*\|\s*([\d\.]+)s"),
        "torch": get(r"import: torch \(top-level\)\s*\|\s*([\d\.]+)s"),
        "chroma": get(r"import: chromadb \(top-level\)\s*\|\s*([\d\.]+)s"),
        "mcp_server": get(r"import: interface\.mcp_server\s*\|\s*([\d\.]+)s"),
        "sqlite_inst": get(r"instantiate: SqliteStore\s*\|\s*([\d\.]+)s"),
        "chroma_inst": get(r"instantiate: ChromaVectorStore\s*\|\s*([\d\.]+)s"),
        "server_inst": get(r"instantiate: GrafoConciergeServer \(31 tools\)\s*\|\s*([\d\.]+)s"),
        "boot": get(r"TOTAL: bootstrap\(\) completo\s*\|\s*([\d\.]+)s"),
        "load": get(r"embedding: _load_model\(\) \(carga de pesos\)\s*\|\s*([\d\.]+)s"),
        "first_inf": get(r"embedding: 1a inferencia \(embed_query\)\s*\|\s*([\d\.]+)s"),
    }


def extract_c4(filepath: Path) -> dict[str, str]:
    if not filepath.exists():
        return {}
    txt = filepath.read_text(encoding="utf-8", errors="replace")

    def get(pat):
        m = re.search(pat, txt)
        return m.group(1) if m else "N/A"

    return {
        "boot": get(r"bootstrap\(\) completou em ([\d\.]+)s com HF_HUB_OFFLINE=1"),
        "load": get(r"embedder\._load_model\(\) completou em ([\d\.]+)s offline"),
        "first_inf": get(r"embed\(\) retornou vetor com 384 dimensoes em ([\d\.]+)s"),
    }


def extract_e2e(filepath: Path) -> dict[str, str]:
    if not filepath.exists():
        return {}
    txt = filepath.read_text(encoding="utf-8", errors="replace")

    def get(pat):
        m = re.search(pat, txt)
        return m.group(1) if m else "N/A"

    return {
        "init": get(r"\(a\) Tempo ate resposta initialize\s*\|\s*([\d\.]+)s"),
        "list": get(r"\(b\) Tempo ate list_tools \(desde spawn\)\s*\|\s*([\d\.]+)s"),
        "reg": get(r"\(c\.1\) concierge_register\s*\|\s*([\d\.]+)s"),
        "mine": get(r"\(c\.2\) concierge_mine \(1o embedding / carga\)\s*\|\s*([\d\.]+)s"),
        "search": get(r"\(c\.3\) concierge_search \(busca vetorial\)\s*\|\s*([\d\.]+)s"),
        "total": get(r"TOTAL E2E \(spawn ate fim da busca\)\s*\|\s*([\d\.]+)s"),
    }


def main():
    c1 = extract_metrics(EVIDENCIA_4_2C / "c1_startup_profile_fresh.txt")
    c2_rep2 = extract_metrics(EVIDENCIA_4_2C / "c2_startup_profile_rep2.txt")
    c2_rep3 = extract_metrics(EVIDENCIA_4_2C / "c2_startup_profile_rep3.txt")
    c3_rep1 = extract_metrics(EVIDENCIA_4_2C / "c3_startup_profile_rep1.txt")
    c3_rep2 = extract_metrics(EVIDENCIA_4_2C / "c3_startup_profile_rep2.txt")
    c3_rep3 = extract_metrics(EVIDENCIA_4_2C / "c3_startup_profile_rep3.txt")
    c4 = extract_c4(EVIDENCIA_4_2C / "c4_hf_offline_test.txt")

    e2e_c1 = extract_e2e(EVIDENCIA_4_2C / "c1_e2e_fresh.txt")
    e2e_c2 = extract_e2e(EVIDENCIA_4_2C / "c2_e2e_rep2.txt")
    e2e_c3 = extract_e2e(EVIDENCIA_4_2C / "c3_e2e_profile.txt")

    # Calculo das medias de C3
    c3_st_avg = (float(c3_rep1["st"]) + float(c3_rep2["st"]) + float(c3_rep3["st"])) / 3
    c3_torch_avg = (float(c3_rep1["torch"]) + float(c3_rep2["torch"]) + float(c3_rep3["torch"])) / 3
    c3_chroma_avg = (float(c3_rep1["chroma"]) + float(c3_rep2["chroma"]) + float(c3_rep3["chroma"])) / 3
    c3_boot_avg = (float(c3_rep1["boot"]) + float(c3_rep2["boot"]) + float(c3_rep3["boot"])) / 3
    c3_load_avg = (float(c3_rep1["load"]) + float(c3_rep2["load"]) + float(c3_rep3["load"])) / 3
    c3_inf_avg = (float(c3_rep1["first_inf"]) + float(c3_rep2["first_inf"]) + float(c3_rep3["first_inf"])) / 3

    md = []
    md.append("# Errata da Rodada 4.2c — Correção das Tabelas de Medição e Notas de Calibração")
    md.append("")
    md.append("> **Data:** 2026-10-24  ")
    md.append("> **Origem dos Dados:** Extração mecânica direta dos arquivos em `scratch/evidencia_4_2c/` (Regra 12)  ")
    md.append("> **Documento Corrigido:** [`audits/fase4-2c-medicao-inicializacao.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/fase4-2c-medicao-inicializacao.md)  ")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 1. Motivação da Errata")
    md.append("")
    md.append("Durante a auditoria e verificação cruzada com a Rodada 4.2d, identificaram-se discrepâncias entre os valores citados no texto do relatório original da 4.2c e os números reais gravados nos arquivos de evidência redirecionados (`scratch/evidencia_4_2c/`). Além disso, duas premissas analíticas requerem retificação técnica:")
    md.append("1. **Valores de Carga de Modelo (`_load_model`):** Citações informais em discussões e resumos mencionavam valores que divergiam dos arquivos brutos (ex.: citar 4,83 s para C1 quando o arquivo registra 1,5044 s; citar 0,86 s para C2 quando os arquivos registram 1,3780 s e 1,2304 s; e citar 0,80 s para C3 quando 0,8025 s é a medição estrita de C4 offline).")
    md.append("2. **Ausência de Medição de 1ª Carga no E2E da 4.2c:** O script `scratch/mcp_e2e_profile.py` executou `concierge_mine` em apenas 0,0018 s porque passou parâmetros que não dispararam a mineração nem o carregamento real do modelo de embedding. O teste E2E da 4.2c, portanto, **não mediu** a primeira carga do modelo.")
    md.append("3. **Superestimativa da Opção 1 (< 0,5 s):** A estimativa preliminar de que o bootstrap cairia para \"< 0,5 s\" apenas tornando lazy o `sentence_transformers` desconsiderou o tempo residual do ChromaDB (~1,85 s de import + ~0,20 s de instanciação). O valor real medido na 4.2d é de **~2,77 s**.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 2. Tabela de Inicialização Retificada (Gerada por Script a partir dos Arquivos Brutos)")
    md.append("")
    md.append("| Fase / Operação | C1 (Frio, Venv Novo) | C2 (Quente, Rep 2) | C2 (Quente, Rep 3) | C3 (Dono, Média 3 Reps) | C4 (HF_HUB_OFFLINE=1) |")
    md.append("|---|---|---|---|---|---|")
    md.append(f"| **import: sentence_transformers** | {c1['st']} s | {c2_rep2['st']} s | {c2_rep3['st']} s | {c3_st_avg:.4f} s | — |")
    md.append(f"| **import: torch** | {c1['torch']} s | {c2_rep2['torch']} s | {c2_rep3['torch']} s | {c3_torch_avg:.4f} s | — |")
    md.append(f"| **import: chromadb** | {c1['chroma']} s | {c2_rep2['chroma']} s | {c2_rep3['chroma']} s | {c3_chroma_avg:.4f} s | — |")
    md.append(f"| import: interface.mcp_server | {c1['mcp_server']} s | {c2_rep2['mcp_server']} s | {c2_rep3['mcp_server']} s | — | — |")
    md.append(f"| instantiate: SqliteStore | {c1['sqlite_inst']} s | {c2_rep2['sqlite_inst']} s | {c2_rep3['sqlite_inst']} s | — | — |")
    md.append(f"| instantiate: ChromaVectorStore | {c1['chroma_inst']} s | {c2_rep2['chroma_inst']} s | {c2_rep3['chroma_inst']} s | — | — |")
    md.append(f"| instantiate: GrafoConciergeServer | {c1['server_inst']} s | {c2_rep2['server_inst']} s | {c2_rep3['server_inst']} s | — | — |")
    md.append(f"| **TOTAL: bootstrap() Completo** | **{c1['boot']} s** | **{c2_rep2['boot']} s** | **{c2_rep3['boot']} s** | **{c3_boot_avg:.4f} s** | **{c4['boot']} s** |")
    md.append(f"| **embedding: carga modelo (`_load_model`)** | **{c1['load']} s** | **{c2_rep2['load']} s** | **{c2_rep3['load']} s** | **{c3_load_avg:.4f} s** | **{c4['load']} s** |")
    md.append(f"| **embedding: 1ª inferência (`embed`)** | {c1['first_inf']} s | {c2_rep2['first_inf']} s | {c2_rep3['first_inf']} s | {c3_inf_avg:.4f} s | {c4['first_inf']} s |")
    md.append("")
    md.append("### Detalhamento das 3 Repetições de C3 nos Arquivos Brutos:")
    md.append(f"- Repetição 1 (`scratch/evidencia_4_2c/c3_startup_profile_rep1.txt`): Bootstrap = {c3_rep1['boot']} s | `_load_model()` = {c3_rep1['load']} s | Inferência = {c3_rep1['first_inf']} s")
    md.append(f"- Repetição 2 (`scratch/evidencia_4_2c/c3_startup_profile_rep2.txt`): Bootstrap = {c3_rep2['boot']} s | `_load_model()` = {c3_rep2['load']} s | Inferência = {c3_rep2['first_inf']} s")
    md.append(f"- Repetição 3 (`scratch/evidencia_4_2c/c3_startup_profile_rep3.txt`): Bootstrap = {c3_rep3['boot']} s | `_load_model()` = {c3_rep3['load']} s | Inferência = {c3_rep3['first_inf']} s")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 3. Retificação das Medições E2E MCP da 4.2c")
    md.append("")
    md.append("| Métrica E2E MCP | C1 (`c1_e2e_fresh.txt`) | C2 (`c2_e2e_rep2.txt`) | C3 (`c3_e2e_profile.txt`) |")
    md.append("|---|---|---|---|")
    md.append(f"| **(a) Tempo até resposta `initialize`** | **{e2e_c1['init']} s** | **{e2e_c2['init']} s** | **{e2e_c3['init']} s** |")
    md.append(f"| **(b) Tempo até `list_tools` (desde spawn)** | {e2e_c1['list']} s | {e2e_c2['list']} s | {e2e_c3['list']} s |")
    md.append(f"| (c.1) Duração de `concierge_register` | {e2e_c1['reg']} s | {e2e_c2['reg']} s | {e2e_c3['reg']} s |")
    md.append(f"| (c.2) Duração de `concierge_mine` (*) | {e2e_c1['mine']} s | {e2e_c2['mine']} s | {e2e_c3['mine']} s |")
    md.append(f"| (c.3) Duração de `concierge_search` | {e2e_c1['search']} s | {e2e_c2['search']} s | {e2e_c3['search']} s |")
    md.append(f"| **TOTAL E2E** | {e2e_c1['total']} s | {e2e_c2['total']} s | {e2e_c3['total']} s |")
    md.append("")
    md.append(">(*) **Nota Crítica sobre `concierge_mine` no E2E da 4.2c:**  ")
    md.append("> O tempo de ~0,0018 s indica que o comando não disparou a ingestão real nem a carga do modelo de embedding (o pipeline retornou imediatamente antes da inferência). Portanto, **o teste E2E da 4.2c NÃO mediu a latência da primeira inferência/carga de modelo**. A medição real e fidedigna dessa carga foi implementada e medida na Rodada 4.2d através de `scratch/evidencia_4_2d/first_embed_profile.py` e `functional_real_test.py`.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 4. Retificação da Estimativa da Opção 1")
    md.append("")
    md.append("- **Afirmação Original da 4.2c:** \"o servidor responde initialize em < 0.5 s\".")
    md.append("- **Retificação Pós-Medição 4.2d:** Esta estimativa estava superestimada. O import de `chromadb` consome ~1,83 s e a instanciação de `ChromaVectorStore` consome ~0,20 s. Com a remoção de `sentence_transformers` e `torch` no bootstrap, o tempo medido de `initialize` E2E caiu para **~3,03 s** (e bootstrap direto para **~2,77 s**). Para atingir tempos inferiores a 1 segundo no arranque, seria necessário também adiar o carregamento do `chromadb`, o que está fora do escopo da Rodada 4.2d.")
    md.append("")

    content = "\n".join(md) + "\n"
    target = REPO_ROOT / "audits" / "errata-4-2c.md"
    target.write_text(content, encoding="utf-8")
    print(f"Errata gerada com sucesso em: {target}")


if __name__ == "__main__":
    main()
