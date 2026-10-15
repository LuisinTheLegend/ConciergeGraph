import os
import re

DIRS = ["core", "interface", "storage", "ingestion", "agent", "agents", "services"]
TABLES = ["files", "communities", "ast_edges", "agent_checkpoints", "fsm_checkpoints"]

results = {t: [] for t in TABLES}

for d in DIRS:
    if not os.path.exists(d):
        continue
    for root, dirs, files in os.walk(d):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f).replace("\\", "/")
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = fp.readlines()
            except Exception:
                continue

            for idx, line in enumerate(lines):
                for t in TABLES:
                    if re.search(rf'\b{t}\b', line, re.IGNORECASE):
                        ctx = "".join(lines[max(0, idx - 4):min(len(lines), idx + 8)])
                        if any(k in ctx.upper() for k in ["SELECT", "INSERT", "UPDATE", "DELETE"]):
                            results[t].append((path, idx + 1, line.strip(), ctx))

with open("scratch/sql_usage_report.txt", "w", encoding="utf-8") as out:
    for t in TABLES:
        out.write(f"\n{'='*70}\n")
        out.write(f"TABLE: {t} — USAGE IN PRODUCTION CODE\n")
        out.write(f"{'='*70}\n")
        seen = set()
        for path, lno, line, ctx in results[t]:
            key = (path, lno)
            if key in seen:
                continue
            seen.add(key)
            out.write(f"\n[{path}:{lno}] {line}\n")
            query_lines = [cl.strip() for cl in ctx.splitlines() if any(w in cl.upper() for w in ["SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "SET", "VALUES", t.upper()])]
            out.write("  Snippet: " + " ".join(query_lines)[:300] + "\n")

print("Generated scratch/sql_usage_report.txt successfully.")
