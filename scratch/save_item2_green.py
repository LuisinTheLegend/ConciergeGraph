import subprocess

res = subprocess.run(
    ["python", "-m", "pytest", "-v", "tests/test_call_chain_edges_nodes.py", "tests/test_agent_checkpoints_schema.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
)

with open("scratch/evidencia_4_3c/item2_tests_green.txt", "w", encoding="utf-8") as f:
    f.write(res.stdout + res.stderr)

print("Saved scratch/evidencia_4_3c/item2_tests_green.txt, returncode:", res.returncode)

