import subprocess
import os

def run_test(test_target):
    res = subprocess.run(
        ["python", "-m", "pytest", "-v", test_target],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return res.stdout + res.stderr, res.returncode

# -------------------------------------------------------------
# M6: Swap [0] with [-1] in ingestion/orchestrator.py:768
# -------------------------------------------------------------
orch_path = r"ingestion\orchestrator.py"
with open(orch_path, "r", encoding="utf-8") as f:
    orch_orig = f.read()

target_m6 = "target_node_id = global_symbol_map[call_name][0]"
mutated_m6 = "target_node_id = global_symbol_map[call_name][-1]"
assert target_m6 in orch_orig, "target_m6 not found"

print("Applying M6...")
with open(orch_path, "w", encoding="utf-8") as f:
    f.write(orch_orig.replace(target_m6, mutated_m6))

out_m6, code_m6 = run_test("tests/test_call_chain_edges_nodes.py::TestCallChainEdgesNodes::test_repeated_symbol_name_orchestrator_behavior")
print("M6 returncode:", code_m6, "(expected non-zero)")
with open(r"scratch\evidencia_4_3c\m6_mutation_last_symbol.txt", "w", encoding="utf-8") as f:
    f.write(out_m6)

# Revert M6
with open(orch_path, "w", encoding="utf-8") as f:
    f.write(orch_orig)
print("Reverted M6.")
diff_m6 = subprocess.check_output(["git", "diff", "--stat", orch_path], text=True)
print("Diff after M6 revert:", diff_m6.strip() or "EMPTY (OK)")
assert not diff_m6.strip(), "M6 not reverted cleanly!"

# -------------------------------------------------------------
# M7a: make save_checkpoint_detailed set self.last_error
# -------------------------------------------------------------
cp_path = r"core\checkpointer.py"
with open(cp_path, "r", encoding="utf-8") as f:
    cp_orig = f.read()

target_m7a = "err = None if success else (str(res) if res is not None else \"Unknown write error\")\n            return bool(success), err"
mutated_m7a = "err = None if success else (str(res) if res is not None else \"Unknown write error\")\n            self.last_error = err\n            return bool(success), err"
assert target_m7a in cp_orig, "target_m7a not found"

print("Applying M7a...")
with open(cp_path, "w", encoding="utf-8") as f:
    f.write(cp_orig.replace(target_m7a, mutated_m7a))

out_m7a, code_m7a = run_test("tests/test_agent_checkpoints_schema.py::TestAgentCheckpointsOfficialSchema::test_save_checkpoint_detailed_does_not_mutate_instance_state")
print("M7a returncode:", code_m7a, "(expected non-zero)")
with open(r"scratch\evidencia_4_3c\m7a_mutation_mutates_state.txt", "w", encoding="utf-8") as f:
    f.write(out_m7a)

# Revert M7a
with open(cp_path, "w", encoding="utf-8") as f:
    f.write(cp_orig)
print("Reverted M7a.")
diff_m7a = subprocess.check_output(["git", "diff", "--stat", cp_path], text=True)
print("Diff after M7a revert:", diff_m7a.strip() or "EMPTY (OK)")
assert not diff_m7a.strip(), "M7a not reverted cleanly!"

# -------------------------------------------------------------
# M7b: make agent_save_checkpoint read getattr(checkpointer, "last_error", None)
# -------------------------------------------------------------
mcp_path = r"interface\mcp_server.py"
with open(mcp_path, "r", encoding="utf-8") as f:
    mcp_orig = f.read()

target_m7b = """    save_fn = getattr(checkpointer, "save_checkpoint_detailed", None)
    if callable(save_fn):
        success, raw_err = save_fn(agent_id, session_id, checkpoint_id, state_dict)
    else:
        success = checkpointer.save_checkpoint(
            agent_id, session_id, checkpoint_id, state_dict
        )
        raw_err = getattr(checkpointer, "last_error", None)"""

mutated_m7b = """    save_fn = getattr(checkpointer, "save_checkpoint_detailed", None)
    if callable(save_fn):
        success, _ = save_fn(agent_id, session_id, checkpoint_id, state_dict)
        raw_err = getattr(checkpointer, "last_error", None)
    else:
        success = checkpointer.save_checkpoint(
            agent_id, session_id, checkpoint_id, state_dict
        )
        raw_err = getattr(checkpointer, "last_error", None)"""
assert target_m7b in mcp_orig, "target_m7b not found"

print("Applying M7b...")
with open(mcp_path, "w", encoding="utf-8") as f:
    f.write(mcp_orig.replace(target_m7b, mutated_m7b, 1))

out_m7b, code_m7b = run_test("tests/test_agent_checkpoints_schema.py::TestAgentCheckpointsOfficialSchema::test_agent_save_checkpoint_does_not_read_last_error_poison")
print("M7b returncode:", code_m7b, "(expected non-zero)")
with open(r"scratch\evidencia_4_3c\m7b_mutation_reads_poison_last_error.txt", "w", encoding="utf-8") as f:
    f.write(out_m7b)

# Revert M7b
with open(mcp_path, "w", encoding="utf-8") as f:
    f.write(mcp_orig)
print("Reverted M7b.")
diff_m7b = subprocess.check_output(["git", "diff", "--stat", mcp_path], text=True)
print("Diff after M7b revert:", diff_m7b.strip() or "EMPTY (OK)")
assert not diff_m7b.strip(), "M7b not reverted cleanly!"

print("All 3 mutations executed, killed, and reverted cleanly!")

