import sys
import os
import re

# Configuração de codificação UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Determinar caminhos relativos ao diretório do script
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
audits_dir = os.path.join(repo_root, 'audits')
backlog_path = os.path.join(audits_dir, 'backlog-final.md')

def normalize_sev(sev_str):
    s = sev_str.upper()
    if 'MÁXIMA' in s or 'MAXIMA' in s: return 'MAXIMA'
    if 'CRÍTICA' in s or 'CRITICA' in s or 'CRÍTICO' in s or 'CRITICO' in s: return 'CRITICA'
    if 'ALTA' in s or 'GRAVE' in s: return 'GRAVE'
    if 'MÉDIA' in s or 'MEDIA' in s or 'MÉDIO' in s or 'MEDIO' in s: return 'MEDIA'
    if 'BAIXA' in s or 'BAIXO' in s: return 'BAIXA'
    if 'OBSERVAÇÃO' in s or 'OBSERVACAO' in s: return 'BAIXA'
    return s

reports_findings = {}
for r in os.listdir(audits_dir):
    if not r.endswith('.md') or r in ['backlog-final.md', 'cruzamento-modulos.md', 'fora-de-escopo.md']:
        continue
    p = os.path.join(audits_dir, r)
    with open(p, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_table = False
    findings = {}
    for line in lines:
        l = line.strip()
        if l.startswith('|') and ('severidade' in l.lower() or 'resumo do achado' in l.lower()) and not re.search(r'\|\s*(?:\*{1,2})?#?\d+', l):
            in_table = True
            continue
        if in_table:
            if not l.startswith('|'):
                in_table = False
                continue
            parts = [part.strip() for part in l.split('|')[1:-1]]
            if not parts:
                continue
            f_num = re.sub(r'[\*#]', '', parts[0]).strip()
            if not f_num.isdigit():
                continue
            
            sev = ''
            for part in parts[1:]:
                if part.startswith('[') and ('http' in part or '.py' in part):
                    continue
                p_up = part.upper()
                if any(k in p_up for k in ['CRÍTICA', 'CRITICA', 'CRÍTICO', 'CRITICO', 'ALTA', 'GRAVE', 'MÉDIA', 'MEDIA', 'MÉDIO', 'MEDIO', 'BAIXA', 'BAIXO', 'OBSERVAÇÃO', 'OBSERVACAO']):
                    sev = part
                    break
            
            non_sev_parts = [p for p in parts[1:] if p != sev and not re.match(r'^[\d–\s,]+$', p) and not p.endswith('.py') and not (p.startswith('[') and '.py' in p)]
            desc = max(non_sev_parts, key=len) if non_sev_parts else ''
            findings[f_num] = {'sev': sev, 'norm_sev': normalize_sev(sev), 'desc': desc, 'raw_line': l}
    reports_findings[r] = findings

with open(backlog_path, 'r', encoding='utf-8') as f:
    backlog_text = f.read()

pattern = re.compile(
    r'#### \[(BL-\d+)\] (.+?)\n'
    r'- \*\*Severidade:\*\* (.+?)\n'
    r'- \*\*Arquivos & Linhas:\*\* (.+?)\n'
    r'- \*\*Relatório de Origem:\*\* \[`?([^`\]]+)`?\]\(.*?\) #(\d+)',
    re.MULTILINE
)

bl_items = pattern.findall(backlog_text)
print(f'Total de itens BL encontrados no backlog: {len(bl_items)}')

results = []
divergences = []
sev_counts = {'MAXIMA': 0, 'CRITICA': 0, 'GRAVE': 0, 'MEDIA': 0, 'BAIXA': 0}

for bl_id, title, sev, files, rep_file_raw, f_num in bl_items:
    rep_file = rep_file_raw.replace('audits/', '').strip()
    norm_s = normalize_sev(sev)
    sev_counts[norm_s] = sev_counts.get(norm_s, 0) + 1

    if rep_file not in reports_findings:
        err = f'{bl_id}: Relatório {rep_file} não encontrado!'
        divergences.append(err)
        results.append((bl_id, 'FAIL', err))
        continue
    rep_dict = reports_findings[rep_file]
    if f_num not in rep_dict:
        err = f'{bl_id}: Achado #{f_num} não existe em {rep_file}!'
        divergences.append(err)
        results.append((bl_id, 'FAIL', err))
        continue
    f_info = rep_dict[f_num]
    bl_norm_sev = normalize_sev(sev)
    rep_norm_sev = f_info['norm_sev']
    
    # Validação de severidade
    if bl_norm_sev != rep_norm_sev:
        err = f'{bl_id}: Severidade diverge! Backlog={sev} ({bl_norm_sev}) vs Relatório={f_info["sev"]} ({rep_norm_sev}) em {rep_file} #{f_num}'
        divergences.append(err)
        results.append((bl_id, 'FAIL', err))
    else:
        results.append((bl_id, 'OK', f'{rep_file} #{f_num} [{norm_s}] | {title}'))

for bl_id, status, msg in results:
    if status == 'OK':
        print(f'[OK] {bl_id}: {msg}')
    else:
        print(f'[DIVERGÊNCIA] {msg}')

print('\n' + '='*70)
print('RESUMO DA VALIDAÇÃO DE RASTREABILIDADE:')
print(f'Total de itens validados: {len(bl_items)}')
print(f'OK: {len(bl_items) - len(divergences)}')
print(f'Divergências: {len(divergences)}')
print('='*70)

print('\nCONTAGEM DE SEVERIDADES DOS ITENS:')
print(f"Máxima:   {sev_counts['MAXIMA']}")
print(f"Crítica:  {sev_counts['CRITICA']}")
print(f"Grave:    {sev_counts['GRAVE']}")
print(f"Média:    {sev_counts['MEDIA']}")
print(f"Baixa:    {sev_counts['BAIXA']}")
print(f"Total:    {sum(sev_counts.values())}")
