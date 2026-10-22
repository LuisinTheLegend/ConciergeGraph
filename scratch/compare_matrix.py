"""scratch/compare_matrix.py
Compara os resultados das 31 ferramentas de fase4_0c_matrix_results_ORIGINAL.json
com os novos resultados de scratch/fase4_0c_matrix_results.json.
"""
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open("scratch/fase4_0c_matrix_results_ORIGINAL.json", "r", encoding="utf-8") as f:
    orig = json.load(f)

with open("scratch/fase4_0c_matrix_results.json", "r", encoding="utf-8") as f:
    novo = json.load(f)

print("======================================================================")
print("COMPARACAO DA MATRIZ DE FERRAMENTAS MCP (31 FERRAMENTAS)")
print("======================================================================")

orig_results = orig.get("results_p", {})
novo_results = novo.get("results_p", {})

print(f"Total de ferramentas testadas original: {len(orig_results)}")
print(f"Total de ferramentas testadas atual:    {len(novo_results)}")
assert len(orig_results) == len(novo_results) == 31, "Erro: contagem de ferramentas difere de 31!"

diffs = []
all_tools = sorted(list(set(list(orig_results.keys()) + list(novo_results.keys()))))

for tool in all_tools:
    o_cls = orig_results.get(tool, {}).get("class")
    n_cls = novo_results.get(tool, {}).get("class")
    status = "IDENTICO" if o_cls == n_cls else "DIVERGENTE"
    print(f"  [{status}] {tool.ljust(26)} -> Original: {str(o_cls).ljust(22)} | Atual: {str(n_cls)}")
    if o_cls != n_cls:
        diffs.append((tool, o_cls, n_cls))

print("\n--- RESUMO DA COMPARACAO ---")
if not diffs:
    print("CONFORMIDADE 100%: Nenhuma alteracao no comportamento ou classificacao das 31 ferramentas.")
    print("Mesmo conjunto de ferramentas funcionais, bloqueadas pelo governor ou com falha esperada de schema.")
else:
    print(f"ATENCAO: {len(diffs)} divergencias encontradas:")
    for tool, o_cls, n_cls in diffs:
        print(f"  - {tool}: {o_cls} -> {n_cls}")

print("======================================================================")
