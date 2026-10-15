import os
import re
from collections import defaultdict

test_files = [
    "tests/test_agent_checkpointer.py",
    "tests/test_agent_hsm_coupling.py",
    "tests/test_alias_tracker.py",
    "tests/test_checkpoint_pruning.py",
    "tests/test_cognitive_routing_memory.py",
    "tests/test_delta_sync.py",
    "tests/test_durable_checkpoints_timetravel.py",
    "tests/test_e2e_concierge_integration.py",
    "tests/test_graph_rag_frugal.py",
    "tests/test_graph_rag_janitor.py",
    "tests/test_graph_rag_loops.py",
    "tests/test_hierarchical_state_machine.py",
    "tests/test_hsm_transition_hooks_and_delta.py",
    "tests/test_local_graph_rag_recursion.py",
    "tests/test_mcp_server_extensions.py",
    "tests/test_telemetry_api.py",
    "tests/test_vector_reconciler.py"
]

tables = ["files", "communities", "ast_edges", "agent_checkpoints", "fsm_checkpoints"]

table_variants = defaultdict(lambda: defaultdict(dict))

for tf in test_files:
    if not os.path.exists(tf):
        continue
    with open(tf, "r", encoding="utf-8") as f:
        content = f.read()
    
    for t in tables:
        pattern = re.compile(rf'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{t}\s*\((.*?)\);?', re.IGNORECASE | re.DOTALL)
        for m in pattern.finditer(content):
            lno = content[:m.start()].count("\n") + 1
            body = m.group(1).replace('"', '').replace("'", "").replace('\n', ' ').strip()
            # clean whitespace
            body = re.sub(r'\s+', ' ', body)
            table_variants[t][f"{tf}:{lno}"] = body

with open("scratch/table_variants_summary.txt", "w", encoding="utf-8") as out:
    for t in tables:
        out.write(f"\n==================== TABLE: {t} ====================\n")
        for loc, body in table_variants[t].items():
            out.write(f"  [{loc}]\n    {body}\n")

print("Generated scratch/table_variants_summary.txt")
