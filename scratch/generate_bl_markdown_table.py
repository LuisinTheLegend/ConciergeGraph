import json

with open("scratch/bl_status_map.json", "r", encoding="utf-8") as f:
    bl_map = json.load(f)

lines = []
lines.append("| BL ID | Título | Severidade | Status Proposto | Justificativa Sintética |")
lines.append("| :--- | :--- | :--- | :--- | :--- |")

for bl_id in sorted(bl_map.keys(), key=lambda x: int(x.split("-")[1])):
    item = bl_map[bl_id]
    title = item["title"].replace("|", "\\|")
    sev = item["sev"].replace("|", "\\|")
    status = item["status"]
    just = item["just"].replace("|", "\\|")
    lines.append(f"| [`{bl_id}`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#{bl_id.lower()}) | {title} | {sev} | **{status}** | {just} |")

table_text = "\n".join(lines)
with open("scratch/bl_status_table.md", "w", encoding="utf-8") as f:
    f.write(table_text)

print(f"Generated table with {len(bl_map)} rows in scratch/bl_status_table.md")
