import os
import subprocess
import sys

scripts = [
    "scratch/append_bl006.py",
    "scratch/apply_graph_rag_fixes.py",
    "scratch/apply_test_clean_db.py",
    "scratch/build_item1b_greps.py",
    "scratch/build_item5_greps.py",
    "scratch/clean_test_edges.py",
    "scratch/debug_2a.py",
    "scratch/debug_2b.py",
    "scratch/debug_2c.py",
    "scratch/debug_2d.py",
    "scratch/debug_2e.py",
    "scratch/debug_mcp_save.py",
    "scratch/fix_embedder_init.py",
    "scratch/fix_import_embed.py",
    "scratch/fix_mcp_ext_fd.py",
    "scratch/fix_mcp_ext_order.py",
    "scratch/fix_test_call_chain_edges.py",
    "scratch/fix_test_clean_db.py",
    "scratch/run_all_item3_mutations.py",
    "scratch/run_b3_mutation.py",
    "scratch/run_full_suite_4_3c.py",
    "scratch/run_mutations_4_3c.py",
    "scratch/save_item2_green.py",
    "scratch/scan_bom_utf.py",
    "scratch/test_2a_investigation.py",
    "scratch/update_checkpointer.py",
    "scratch/update_roadmap_4_3.py",
    "scratch/update_stress_setup.py",
    "scratch/update_test_e2e.py",
    "scratch/update_test_graph_rag_janitor.py",
    "scratch/update_test_mcp_server_extensions.py",
]

py_exe = os.path.abspath(".venv_clean/Scripts/python.exe")
env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

results = []

for sc in scripts:
    sc_path = os.path.abspath(sc)
    if not os.path.exists(sc_path):
        results.append((sc, "NOT FOUND", -1, "File does not exist"))
        continue
    try:
        proc = subprocess.run(
            [py_exe, sc_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        status = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        msg = proc.stderr.strip() or proc.stdout.strip()
        first_line = msg.splitlines()[-1] if msg else ""
        results.append((sc, status, proc.returncode, first_line[:120]))
    except subprocess.TimeoutExpired:
        results.append((sc, "TIMEOUT (>10s)", -1, "Execution timed out"))
    except Exception as e:
        results.append((sc, "ERROR", -1, str(e)[:120]))

os.makedirs("scratch/evidencia_4_4b", exist_ok=True)
out_file = "scratch/evidencia_4_4b/restored_scripts_status.txt"
with open(out_file, "w", encoding="utf-8", newline="\n") as f:
    f.write(f"{'Script':<45} | {'Status':<18} | {'Code':<5} | {'Detail'}\n")
    f.write("-" * 100 + "\n")
    for sc, status, code, detail in results:
        f.write(f"{sc:<45} | {status:<18} | {code:<5} | {detail}\n")

print(f"Status written to {out_file}")

