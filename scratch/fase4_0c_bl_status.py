import sys
import os
import re
import json

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def load_data():
    with open('scratch/fase4_0c_module_status_results.json', encoding='utf-8') as f:
        mod_status_data = json.load(f)
    mod_status = {k: v['status'] for k, v in mod_status_data['modules'].items()}
    
    with open('audits/backlog-final.md', encoding='utf-8') as f:
        backlog_text = f.read()
        
    return mod_status, backlog_text

def normalize_sev(sev_str):
    s = sev_str.upper()
    if 'MÁXIMA' in s or 'MAXIMA' in s: return 'MAXIMA'
    if 'CRÍTICA' in s or 'CRITICA' in s or 'CRÍTICO' in s or 'CRITICO' in s: return 'CRITICA'
    if 'ALTA' in s or 'GRAVE' in s: return 'GRAVE'
    if 'MÉDIA' in s or 'MEDIA' in s or 'MÉDIO' in s or 'MEDIO' in s: return 'MEDIA'
    if 'BAIXA' in s or 'BAIXO' in s: return 'BAIXA'
    return s

def run_analysis():
    mod_status, backlog_text = load_data()
    
    pattern = re.compile(
        r'#### \[(BL-\d+)\] (.+?)\n'
        r'- \*\*Severidade:\*\* (.+?)\n'
        r'- \*\*Arquivos & Linhas:\*\* (.+?)\n'
        r'- \*\*Relatório de Origem:\*\* \[`?([^`\]]+)`?\]\(.*?\) #(\d+)',
        re.MULTILINE
    )
    items = pattern.findall(backlog_text)
    
    file_regex = re.compile(r'([a-zA-Z0-9_\-\./\\]+\.(?:py|ts|tsx|md|json|sql|js|sh|bat))(?::([0-9–\-, ]+))?')
    
    # 64 production modules
    prod_modules = set(mod_status.keys())
    
    bl_results = []
    
    for bl_id, title, sev, files_str, rep_file_raw, f_num in items:
        norm_sev = normalize_sev(sev)
        matches = file_regex.findall(files_str)
        
        prod_citations = []
        other_citations = []
        
        for f_path, f_lines in matches:
            norm_path = f_path.replace('\\\\', '/').replace('\\', '/')
            if norm_path.startswith('./'):
                norm_path = norm_path[2:]
            
            # If path ends in .ts or is clearly dashboard/test/doc
            if norm_path in prod_modules:
                prod_citations.append({
                    'file': norm_path,
                    'lines': f_lines,
                    'status': mod_status[norm_path]
                })
            else:
                category = 'other'
                if norm_path.startswith('tests/') or norm_path.startswith('test_'):
                    category = 'test'
                elif norm_path.startswith('grafo-dashboard-web/'):
                    category = 'dashboard'
                elif norm_path.startswith('docs') or norm_path.endswith('.md'):
                    category = 'doc'
                other_citations.append({
                    'file': norm_path,
                    'lines': f_lines,
                    'category': category
                })
                
        # Deduplicate prod_citations by file
        unique_prod = {}
        for p in prod_citations:
            if p['file'] not in unique_prod:
                unique_prod[p['file']] = p
        prod_citations_dedup = list(unique_prod.values())
        
        # Classification rule:
        # VIVO: if any main citation is in EXECUTADO EM F2 or EXECUTADO SÓ EM F1 and NONE in SÓ CARREGADO / NÃO CARREGADO
        # DORMENTE: if all citations are in SÓ CARREGADO or NÃO CARREGADO
        # MISTO: if there are both (executed and non-executed/loaded)
        # SEM CITAÇÃO PROD: if prod_citations is empty
        
        executed_mods = [p for p in prod_citations_dedup if p['status'] in ('EXECUTADO EM F2', 'EXECUTADO SÓ EM F1')]
        dormant_mods = [p for p in prod_citations_dedup if p['status'] in ('SÓ CARREGADO', 'NÃO CARREGADO')]
        
        if len(prod_citations_dedup) == 0:
            status = 'SEM CITAÇÃO PROD'
        elif len(executed_mods) > 0 and len(dormant_mods) > 0:
            status = 'MISTO'
        elif len(executed_mods) > 0:
            status = 'VIVO'
        else:
            status = 'DORMENTE'
            
        bl_results.append({
            'bl_id': bl_id,
            'title': title,
            'raw_sev': sev.strip(),
            'norm_sev': norm_sev,
            'raw_files': files_str.strip(),
            'prod_citations': prod_citations_dedup,
            'other_citations': other_citations,
            'executed_mods': [p['file'] for p in executed_mods],
            'dormant_mods': [p['file'] for p in dormant_mods],
            'status': status
        })
        
    return bl_results

if __name__ == '__main__':
    results = run_analysis()
    
    print(f"Total BL analisados: {len(results)}")
    
    status_counts = {}
    sev_counts = {}
    status_by_sev = {}
    
    for r in results:
        st = r['status']
        sev = r['norm_sev']
        status_counts[st] = status_counts.get(st, 0) + 1
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
        if sev not in status_by_sev:
            status_by_sev[sev] = {}
        status_by_sev[sev][st] = status_by_sev[sev].get(st, 0) + 1
        
    print("\n--- DISTRIBUIÇÃO GLOBAL POR STATUS ---")
    for st, c in sorted(status_counts.items()):
        print(f"  {st:20}: {c}")
        
    print("\n--- DISTRIBUIÇÃO POR SEVERIDADE (TOTAL 88) ---")
    for sev in ['MAXIMA', 'CRITICA', 'GRAVE', 'MEDIA', 'BAIXA']:
        print(f"  {sev:10}: {sev_counts.get(sev, 0)}")
        
    print("\n--- MATRIZ SEVERIDADE × STATUS ---")
    print(f"{'SEVERIDADE':<10} | {'VIVO':<8} | {'DORMENTE':<10} | {'MISTO':<8} | {'SEM PROD':<10} | {'TOTAL':<6}")
    print("-" * 65)
    for sev in ['MAXIMA', 'CRITICA', 'GRAVE', 'MEDIA', 'BAIXA']:
        v = status_by_sev.get(sev, {}).get('VIVO', 0)
        d = status_by_sev.get(sev, {}).get('DORMENTE', 0)
        m = status_by_sev.get(sev, {}).get('MISTO', 0)
        s = status_by_sev.get(sev, {}).get('SEM CITAÇÃO PROD', 0)
        tot = sev_counts.get(sev, 0)
        print(f"{sev:<10} | {v:<8} | {d:<10} | {m:<8} | {s:<10} | {tot:<6}")
        
    print("\n--- ITENS MISTO (PARA DECISÃO HUMANA) ---")
    misto_items = [r for r in results if r['status'] == 'MISTO']
    print(f"Total de itens MISTO: {len(misto_items)}")
    for r in misto_items:
        print(f"  [{r['bl_id']}] ({r['norm_sev']}) {r['title']}")
        print(f"    Executados ({len(r['executed_mods'])}): {', '.join(r['executed_mods'])}")
        print(f"    Dormentes  ({len(r['dormant_mods'])}): {', '.join(r['dormant_mods'])}")
        
    print("\n--- ITENS SEM CITAÇÃO DE PRODUÇÃO PYTHON ---")
    sem_prod = [r for r in results if r['status'] == 'SEM CITAÇÃO PROD']
    print(f"Total de itens sem citação de produção: {len(sem_prod)}")
    for r in sem_prod:
        others = [f"{o['file']} ({o['category']})" for o in r['other_citations']]
        print(f"  [{r['bl_id']}] ({r['norm_sev']}) {r['title']}")
        print(f"    Outras citações: {', '.join(others)}")
        
    # Salvar resultados completos em JSON
    with open('scratch/fase4_0c_bl_status_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(results),
            'status_counts': status_counts,
            'sev_counts': sev_counts,
            'status_by_sev': status_by_sev,
            'misto': misto_items,
            'sem_prod': sem_prod,
            'all_bl': results
        }, f, indent=2, ensure_ascii=False)
    print("\nResultados salvos em scratch/fase4_0c_bl_status_results.json")
