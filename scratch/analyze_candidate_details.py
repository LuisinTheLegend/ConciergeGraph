import os
import re
import json

candidates = [
    {
        "name": "agent/run_agent.py",
        "slug": "run_agent",
        "terms": ["run_agent.py", "run_agent", "CognitiveAgentRunner", "HermesAgentRunner"]
    },
    {
        "name": "agent/agent_prompts.py",
        "slug": "agent_prompts",
        "terms": ["agent_prompts.py", "agent_prompts", "DynamicPromptBuilder"]
    },
    {
        "name": "agents/revisor_critico.py",
        "slug": "revisor_critico",
        "terms": ["revisor_critico.py", "revisor_critico", "RevisorCritico"]
    },
    {
        "name": "interface/telemetry_api.py",
        "slug": "telemetry_api",
        "terms": ["telemetry_api.py", "telemetry_api"]
    },
    {
        "name": "core/rate_governor.py",
        "slug": "rate_governor",
        "terms": ["rate_governor.py", "rate_governor", "RateGovernor"]
    },
    {
        "name": "core/gating_interceptor.py",
        "slug": "gating_interceptor",
        "terms": ["gating_interceptor.py", "gating_interceptor", "GatingInterceptor"]
    },
    {
        "name": "core/nozomio_router.py",
        "slug": "nozomio_router",
        "terms": ["nozomio_router.py", "nozomio_router"]
    },
    {
        "name": "grafo-dashboard-web",
        "slug": "grafo_dashboard_web",
        "terms": ["grafo-dashboard-web"]
    }
]

# 1. Tests importing candidate
test_files = [os.path.join("tests", f) for f in os.listdir("tests") if f.endswith(".py")]

# Count tests per file
def get_test_count(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return len(re.findall(r"def test_", content))

test_counts = {tf: get_test_count(tf) for tf in test_files}

# 2. Documents
doc_files = []
for root, _, files in os.walk("docs-grafo-concierge"):
    for f in files:
        if f.endswith(".md"):
            doc_files.append(os.path.join(root, f))
for f in ["README.md", "README_pt.md", "CONTRIBUTING.md", "ATTRIBUTION_AND_LINEAGE.md", "pyproject.toml", "Dockerfile", "docker-compose.yml"]:
    if os.path.exists(f):
        doc_files.append(f)

# 3. Backlog items
with open("audits/backlog-final.md", "r", encoding="utf-8") as f:
    backlog_text = f.read()

# Split backlog by items #### [BL-xxx]
bl_blocks = re.findall(r"(#### \[BL-\d+\].*?)(?=#### \[BL-\d+\]|\Z)", backlog_text, re.DOTALL)
print(f"Total BL blocks: {len(bl_blocks)}")

def parse_bl(block):
    m_id = re.search(r"#### \[(BL-\d+)\] (.*)", block)
    bl_id = m_id.group(1) if m_id else ""
    title = m_id.group(2).strip() if m_id else ""
    m_sev = re.search(r"- \*\*Severidade:\*\* (.*)", block)
    sev = m_sev.group(1).strip() if m_sev else ""
    m_files = re.search(r"- \*\*Arquivos & Linhas:\*\* (.*)", block)
    files = m_files.group(1).strip() if m_files else ""
    return bl_id, title, sev, files, block

bl_items = [parse_bl(b) for b in bl_blocks]

candidate_analysis = {}

for cand in candidates:
    c_name = cand["name"]
    terms = cand["terms"]
    
    # Check test imports
    importing_tests = []
    for tf in test_files:
        with open(tf, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for t in terms:
            if re.search(rf"\b(import|from)\b.*{t}", content):
                importing_tests.append({"file": tf, "tests": test_counts[tf]})
                break
                
    # Check doc citations
    citing_docs = []
    for df in doc_files:
        with open(df, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for t in terms:
            if t in content:
                citing_docs.append(df)
                break
                
    # Check BL items
    citing_bls = []
    for bl_id, title, sev, files_field, full_block in bl_items:
        # Check if candidate name is in files_field
        matched = False
        for t in terms:
            if t in files_field:
                matched = True
                break
        if matched:
            citing_bls.append({
                "bl_id": bl_id,
                "title": title,
                "severity": sev,
                "files_field": files_field
            })
            
    candidate_analysis[c_name] = {
        "importing_tests": importing_tests,
        "citing_docs": citing_docs,
        "citing_bls": citing_bls
    }

with open("scratch/candidate_details.json", "w", encoding="utf-8") as f:
    json.dump(candidate_analysis, f, indent=2, ensure_ascii=False)

print("Saved scratch/candidate_details.json successfully!")
