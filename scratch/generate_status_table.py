import re
import json

with open("scratch/candidate_details.json", "r", encoding="utf-8") as f:
    cand_data = json.load(f)

with open("audits/backlog-final.md", "r", encoding="utf-8") as f:
    backlog_text = f.read()

bl_blocks = re.findall(r"(#### \[BL-\d+\].*?)(?=#### \[BL-\d+\]|\Z)", backlog_text, re.DOTALL)

def parse_bl(block):
    m_id = re.search(r"#### \[(BL-\d+)\] (.*)", block)
    bl_id = m_id.group(1) if m_id else ""
    title = m_id.group(2).strip() if m_id else ""
    m_sev = re.search(r"- \*\*Severidade:\*\* (.*)", block)
    sev = m_sev.group(1).strip() if m_sev else ""
    m_files = re.search(r"- \*\*Arquivos & Linhas:\*\* (.*)", block)
    files = m_files.group(1).strip() if m_files else ""
    return bl_id, title, sev, files

items = [parse_bl(b) for b in bl_blocks]

# Map candidate to BLs
bl_to_status = {}

for bl_id, title, sev, files in items:
    # default ATIVO
    status = "ATIVO"
    just = "Núcleo essencial do sistema mantido em produção."
    
    # Check candidate intersections
    has_telemetry = "telemetry_api.py" in files
    has_dashboard = "grafo-dashboard-web" in files
    has_run_agent = "run_agent.py" in files
    has_prompts = "agent_prompts.py" in files
    has_revisor = "revisor_critico.py" in files
    has_rate_gov = "rate_governor.py" in files
    has_gating = "gating_interceptor.py" in files
    has_nozomio = "nozomio_router.py" in files
    has_mcp = "mcp_server.py" in files
    has_hsm = "hsm_engine.py" in files
    has_store = "store.py" in files
    has_governor = "mcp_governor.py" in files
    
    # Specific BL rules
    if bl_id == "BL-014":
        status = "DEPENDE"
        just = "Cruza agent/run_agent.py (candidato), core/hsm_engine.py e interface/mcp_server.py (ativos). Se podar run_agent, o MCP não integra com runner mas mantém FSM."
    elif bl_id == "BL-015":
        status = "DEPENDE"
        just = "Cruza core/mcp_governor.py (ativo) e interface/telemetry_api.py:357 (candidato). O MCPToolGovernor precisa de correção de estado inicial independentemente da telemetria."
    elif bl_id == "BL-070":
        status = "DEPENDE"
        just = "Cruza grafo-dashboard-web e interface/telemetry_api.py:556. Se ambos forem podados, vai para QUARENTENA; se um for mantido, permanece ativo."
    elif bl_id == "BL-072":
        status = "DEPENDE"
        just = "Cruza grafo-dashboard-web (candidato) e interface/mcp_server.py:186 (ativo). A rejeição HTTP 401 afeta o cliente MCP do dashboard e qualquer cliente FastMCP externo."
    elif bl_id == "BL-073":
        status = "DEPENDE"
        just = "Cruza storage/store.py (ativo) e InspectorDrawer.tsx (candidato). A omissão de metadados em get_full_topology afeta a ferramenta MCP de topologia do núcleo."
    elif bl_id == "BL-003":
        # BL-003 is about removing local DDLs from tests
        status = "ATIVO"
        just = "Essencial para purgar Test Mirage e unificar schema oficial no core, mesmo que suítes de módulos podados sejam arquivadas."
    elif has_telemetry and not has_dashboard and not has_mcp and not has_governor:
        status = "QUARENTENA"
        just = "Módulo periférico interface/telemetry_api.py proposto para arquivamento temporário."
    elif has_dashboard and not has_telemetry and not has_store and not has_mcp:
        status = "QUARENTENA"
        just = "Frontend periférico grafo-dashboard-web proposto para arquivamento temporário."
    elif has_run_agent or has_prompts:
        status = "QUARENTENA"
        just = "Runtime de agente experimental (agent/run_agent.py ou agent_prompts.py) proposto para arquivamento."
    elif has_revisor:
        status = "QUARENTENA"
        just = "Agente de auditoria periférico (agents/revisor_critico.py) proposto para arquivamento."
    elif has_rate_gov:
        status = "QUARENTENA"
        just = "Mecanismo complexo de rate limiting multi-thread (core/rate_governor.py) proposto para arquivamento."
    elif has_gating and not has_telemetry:
        status = "QUARENTENA"
        just = "Interceptor de permissões monorepo (core/gating_interceptor.py) proposto para arquivamento."
    elif has_nozomio:
        status = "QUARENTENA"
        just = "Shim deprecado (core/nozomio_router.py) proposto para remoção/arquivamento."
    
    bl_to_status[bl_id] = {
        "title": title,
        "sev": sev,
        "status": status,
        "just": just
    }

# Print summary
counts = {}
for b, data in bl_to_status.items():
    st = data["status"]
    counts[st] = counts.get(st, 0) + 1

print("Contagem por status proposto:")
for st, cnt in sorted(counts.items()):
    print(f"  {st}: {cnt}")

with open("scratch/bl_status_map.json", "w", encoding="utf-8") as f:
    json.dump(bl_to_status, f, indent=2, ensure_ascii=False)
