import os
import sys
import shutil
import subprocess
import tempfile
import re
import json

candidates = [
    ('agent/run_agent.py', 'run_agent'),
    ('agent/agent_prompts.py', 'agent_prompts'),
    ('agents/revisor_critico.py', 'revisor_critico'),
    ('interface/telemetry_api.py', 'telemetry_api'),
    ('core/rate_governor.py', 'rate_governor'),
    ('core/gating_interceptor.py', 'gating_interceptor'),
    ('core/nozomio_router.py', 'nozomio_router'),
    ('grafo-dashboard-web', 'grafo_dashboard_web')
]

results = {}

for rel_path, slug in candidates:
    print(f"=== Testing candidate: {rel_path} ===")
    temp_dir = os.path.join(tempfile.gettempdir(), f"grafo_sim_{slug}")
    # clean up previous if any
    subprocess.run(["git", "worktree", "remove", "--force", temp_dir], capture_output=True)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    res_add = subprocess.run(["git", "worktree", "add", temp_dir, "HEAD"], capture_output=True, text=True)
    if res_add.returncode != 0:
        print(f"Failed to add worktree for {slug}: {res_add.stderr}")
        continue
        
    target_in_worktree = os.path.join(temp_dir, rel_path.replace("/", os.sep))
    if os.path.isfile(target_in_worktree):
        os.remove(target_in_worktree)
    elif os.path.isdir(target_in_worktree):
        shutil.rmtree(target_in_worktree)
    else:
        print(f"Target {target_in_worktree} not found!")
        
    env = os.environ.copy()
    env["PYTHONPATH"] = temp_dir
    
    # 1. import interface.mcp_server
    cmd_mcp = [sys.executable, "-c", "import interface.mcp_server; print('OK')"]
    p_mcp = subprocess.run(cmd_mcp, cwd=temp_dir, env=env, capture_output=True, text=True)
    out_mcp = (p_mcp.stdout + p_mcp.stderr).strip()
    
    # 2. import main
    cmd_main = [sys.executable, "-c", "import main; print('OK')"]
    p_main = subprocess.run(cmd_main, cwd=temp_dir, env=env, capture_output=True, text=True)
    out_main = (p_main.stdout + p_main.stderr).strip()
    
    # 3. pytest collect-only
    cmd_pytest = [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"]
    p_pytest = subprocess.run(cmd_pytest, cwd=temp_dir, env=env, capture_output=True, text=True)
    out_pytest = (p_pytest.stdout + p_pytest.stderr).strip()
    
    m = re.search(r"(\d+)\s+tests? collected", out_pytest)
    count = m.group(1) if m else "ERROR"
    
    results[rel_path] = {
        "mcp_server_rc": p_mcp.returncode,
        "mcp_server_out": out_mcp,
        "main_rc": p_main.returncode,
        "main_out": out_main,
        "pytest_rc": p_pytest.returncode,
        "pytest_collected": count,
        "pytest_out_tail": "\n".join(out_pytest.splitlines()[-15:])
    }
    
    subprocess.run(["git", "worktree", "remove", "--force", temp_dir], capture_output=True)
    print(f"Done {slug}: mcp_rc={p_mcp.returncode} | main_rc={p_main.returncode} | pytest_collected={count}")
    sys.stdout.flush()

with open("scratch/simulation_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Saved scratch/simulation_results.json successfully!")
