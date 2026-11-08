import glob
import os
import sys

files_to_check = (
    glob.glob("scratch/evidencia_4_4b/*")
    + glob.glob("audits/relatorio_4_4b.md")
    + glob.glob("audits/errata-4-3c.md")
    + glob.glob("audits/fase4-achados.md")
    + glob.glob("audits/fase4-roadmap.md")
    + glob.glob("CHANGELOG.md")
)

results = []
affected = []

for fpath in sorted(set(files_to_check)):
    if not os.path.isfile(fpath):
        continue
    with open(fpath, "rb") as f:
        raw = f.read()

    has_bom_utf8 = raw.startswith(b"\xef\xbb\xbf")
    has_bom_utf16_le = raw.startswith(b"\xff\xfe")
    has_bom_utf16_be = raw.startswith(b"\xfe\xff")
    has_null = b"\x00" in raw

    status = []
    if has_bom_utf8:
        status.append("BOM_UTF8")
    if has_bom_utf16_le:
        status.append("BOM_UTF16_LE")
    if has_bom_utf16_be:
        status.append("BOM_UTF16_BE")
    if has_null:
        status.append("NULL_BYTES")

    status_str = ", ".join(status) if status else "CLEAN_UTF8"
    line = f"{fpath}: size={len(raw)}, status={status_str}"
    results.append(line)

    if status:
        affected.append((fpath, status_str))

out_file = "scratch/evidencia_4_4b/utf8_bom_validation.txt"
with open(out_file, "w", encoding="utf-8", newline="\n") as f:
    f.write("=== VALIDAÇÃO UTF-8 SEM BOM E SEM BYTES NULOS (RODADA 4.4b) ===\n")
    f.write("\n".join(results) + "\n")
    f.write(f"\nTotal verificados: {len(results)}, Afetados com BOM/NULL: {len(affected)}\n")

print(f"Total verificados: {len(results)}, Afetados: {len(affected)}")
if affected:
    print("ARQUIVOS COM BOM OU NULOS DETECTADOS:")
    for f, st in affected:
        print(f"  - {f}: {st}")
    sys.exit(1)
else:
    print("Todos os arquivos analisados são UTF-8 puros sem BOM e sem nulos.")
