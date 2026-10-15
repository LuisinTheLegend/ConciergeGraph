import os
import re
import glob

TABLES = ["files", "communities", "ast_edges", "agent_checkpoints", "fsm_checkpoints"]

print("=== 3A & 3B: CREATE TABLE STATEMENTS IN TESTS AND PRODUCTION ===")
for root, dirs, files in os.walk("."):
    # skip .git, .next, node_modules, _test_clean_clone_tmp, .reversa, _reversa_sdd
    if any(p in root for p in [".git", ".next", "node_modules", "_test_clean_clone_tmp", ".reversa", "_reversa_sdd"]):
        continue
    for file in files:
        if not file.endswith(".py"):
            continue
        filepath = os.path.join(root, file).replace("\\", "/")
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        
        for table in TABLES:
            pattern = re.compile(rf'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table}\s*\((.*?)\);?', re.IGNORECASE | re.DOTALL)
            for m in pattern.finditer(content):
                # find line number
                line_no = content[:m.start()].count("\n") + 1
                body = m.group(1).strip()
                print(f"\n--- Table: {table} in {filepath}:{line_no} ---")
                print(body)
