import glob
import os

files_to_check = glob.glob("scratch/evidencia_4_3b/*") + glob.glob("audits/*.md")
results = []
affected = []

for fpath in sorted(files_to_check):
    if not os.path.isfile(fpath):
        continue
    with open(fpath, "rb") as f:
        raw = f.read()

    has_bom_utf8 = raw.startswith(b"\xef\xbb\xbf")
    has_bom_utf16_le = raw.startswith(b"\xff\xfe")
    has_bom_utf16_be = raw.startswith(b"\xfe\xff")
    has_null = b"\x00" in raw
    
    # Try decoding
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
    print(line)
    results.append(line)
    
    if status:
        affected.append((fpath, status_str, raw))

with open("scratch/evidencia_4_3c/item1d_bom_scan.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results) + "\n")

print(f"\nTotal scanned: {len(results)}, Affected: {len(affected)}")

# Regrave os afetados com sufixo _utf8 (sem sobrescrever o commitado)
for fpath, st, raw in affected:
    # If BOM utf8, strip BOM
    if st == "BOM_UTF8":
        clean_data = raw[3:]
    elif "UTF16" in st:
        text = raw.decode("utf-16", errors="replace")
        clean_data = text.encode("utf-8")
    else:
        text = raw.decode("utf-8", errors="replace").replace("\x00", "")
        clean_data = text.encode("utf-8")
        
    base, ext = os.path.splitext(fpath)
    new_path = f"{base}_utf8{ext}"
    with open(new_path, "wb") as f:
        f.write(clean_data)
    print(f"Created clean copy: {new_path} (bytes: {len(clean_data)})")
