import os
import sys
import time
import subprocess
import tempfile
import shutil
import urllib.request
import urllib.error

def probe_endpoint(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Probe/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            code = resp.status
            body = resp.read(200).decode("utf-8", errors="replace")
            return code, body.strip().replace("\n", " ")
    except urllib.error.HTTPError as e:
        body = e.read(200).decode("utf-8", errors="replace")
        return e.code, body.strip().replace("\n", " ")
    except Exception as e:
        return None, f"Connection error: {type(e).__name__}: {e}"

def main():
    temp_dir = tempfile.mkdtemp(prefix="telemetry_probe_")
    db_path = os.path.join(temp_dir, "test.db")
    chroma_path = os.path.join(temp_dir, "chroma")
    log_file_path = os.path.join(temp_dir, "server.log")
    port = 18923
    
    env = os.environ.copy()
    env["GRAFO_DB_PATH"] = db_path
    env["GRAFO_CHROMA_PATH"] = chroma_path
    env["GRAFO_PORT"] = str(port)
    env["GRAFO_HOST"] = "127.0.0.1"
    env["GRAFO_TRANSPORT"] = "sse"
    env["GRAFO_LOG_LEVEL"] = "INFO"
    env["PYTHONUNBUFFERED"] = "1"
    
    print(f"Starting server in subprocess with port {port} and transport=sse...")
    log_file = open(log_file_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    
    start_time = time.time()
    server_ready = False
    
    try:
        # Wait up to 25s for startup
        while time.time() - start_time < 25:
            if proc.poll() is not None:
                print("Process terminated prematurely!")
                break
            code, msg = probe_endpoint(f"http://127.0.0.1:{port}/sse")
            if code is not None:
                server_ready = True
                print(f"Server is listening! /sse returned code: {code}")
                break
            time.sleep(1)
            
        endpoints = [
            f"http://127.0.0.1:{port}/api/mcp/state/probe",
            f"http://127.0.0.1:{port}/api/governor/metrics",
            f"http://127.0.0.1:{port}/api/gating/config",
            f"http://127.0.0.1:{port}/",
            f"http://127.0.0.1:{port}/sse",
        ]
        
        print("\n--- CONSULTA AOS ENDPOINTS ---")
        results = {}
        for ep in endpoints:
            code, resp = probe_endpoint(ep)
            print(f"Endpoint: {ep}")
            print(f"  HTTP Status: {code}")
            print(f"  Resposta (primeiras linhas): {resp[:150]}")
            results[ep] = {"code": code, "response": resp}
            
    finally:
        print("\nEncerramento do processo...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
            proc.wait()
        log_file.close()
        
        with open(log_file_path, "r", encoding="utf-8", errors="replace") as f:
            boot_logs = [line.strip() for line in f]
            
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Diretório temporário descartado.")
        
    print("\n--- LOGS DO BOOT ---")
    for line in boot_logs:
        if line.strip():
            safe_line = line.encode("ascii", errors="replace").decode("ascii")
            print("  |", safe_line)
        
    # Check if port is free
    code_after, _ = probe_endpoint(f"http://127.0.0.1:{port}/sse")
    print(f"\nVerificação de liberação da porta {port}: code={code_after} (Esperado: None/Connection error)")

if __name__ == "__main__":
    main()
