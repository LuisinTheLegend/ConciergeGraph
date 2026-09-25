"""
scratch/reproduce_telemetry_findings.py

Empirical reproduction of findings in interface/telemetry_api.py:
1. Fatal OperationalError in production due to phantom tables (files & agent_checkpoints).
2. Out-of-the-box inoperability due to unconfigured database manager (RuntimeError).
3. SSE stream termination after 5 seconds due to hardcoded test limit (max_checks = 5).
4. Perpetual SHA-256 cache invalidation due to dynamic datetime.now() in payload.
5. Insecure CORS and unauthenticated state mutation (MCP state, gating mode, governor tokens).
6. Fragile timestamp deserialization crashing on NoneType or ISO str.
"""

import os
import sys
import tempfile
import time
import json
import sqlite3
from datetime import datetime, timezone
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))

from core.database import ConciergeDatabaseManager
from interface.telemetry_api import (
    app,
    get_db_manager,
    set_db_manager,
    _build_telemetry_payload,
    _hash_payload,
    mcp_governor,
    gating_interceptor_service,
    rate_governor_service,
)

def test_finding_1_production_schema_missing_tables():
    print("=" * 70)
    print("TESTE 1: Falha Fatal em Produção por Suposição de Tabelas Inexistentes")
    print("=" * 70)
    # Testa contra o banco real do repositório (data/concierge.db)
    db_real = ConciergeDatabaseManager("data/concierge.db")
    
    app.dependency_overrides[get_db_manager] = lambda: db_real
    client = TestClient(app, raise_server_exceptions=False)
    
    resp = client.get("/api/telemetry/snapshot")
    print(f"Status retornado por GET /api/telemetry/snapshot em produção: {resp.status_code}")
    print(f"Corpo do erro: {resp.text[:200]}")
    
    crashed = resp.status_code == 500
    print(f"-> [CONFIRMADO] API crashou com HTTP 500 em produção: {crashed}\n")
    app.dependency_overrides.clear()
    return crashed

def test_finding_2_unconfigured_db_manager():
    print("=" * 70)
    print("TESTE 2: Inoperância Fora da Caixa (RuntimeError: db_manager not configured)")
    print("=" * 70)
    # Sem overrides e sem set_db_manager
    import interface.telemetry_api as api_mod
    orig = api_mod._db_manager_instance
    api_mod._db_manager_instance = None
    
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/telemetry/snapshot")
    print(f"Status retornado sem set_db_manager(): {resp.status_code}")
    print(f"Resposta: {resp.text[:200]}")
    
    api_mod._db_manager_instance = orig
    confirmed = resp.status_code == 500
    print(f"-> [CONFIRMADO] API inacessível sem injeção manual externa: {confirmed}\n")
    return confirmed

def test_finding_3_sse_stream_5_seconds_abort():
    print("=" * 70)
    print("TESTE 3: Stream SSE Aborta após 5 Segundos (max_checks = 5)")
    print("=" * 70)
    tmp = tempfile.mktemp(suffix=".db")
    db = ConciergeDatabaseManager(tmp)
    db.write_query("CREATE TABLE files (path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL);")
    db.write_query("CREATE TABLE agent_checkpoints (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, session_id TEXT, checkpoint_id TEXT, timestamp REAL);")
    
    app.dependency_overrides[get_db_manager] = lambda: db
    client = TestClient(app)
    
    events_count = 0
    t0 = time.time()
    with client.stream("GET", "/api/telemetry/stream") as response:
        for line in response.iter_lines():
            if line.startswith("data:"):
                events_count += 1
    duration = time.time() - t0
    print(f"Duração total do stream SSE: {duration:.2f}s")
    print(f"Total de eventos emitidos antes do encerramento forçado da conexão: {events_count}")
    
    confirmed = (events_count <= 6) and (duration < 7.0)
    print(f"-> [CONFIRMADO] Conexão persistente SSE morre prematuramente em ~5s: {confirmed}\n")
    app.dependency_overrides.clear()
    return confirmed

def test_finding_4_perpetual_hash_invalidation():
    print("=" * 70)
    print("TESTE 4: Invalidação Perpétua do SHA-256 por datetime.now() Dinâmico")
    print("=" * 70)
    tmp = tempfile.mktemp(suffix=".db")
    db = ConciergeDatabaseManager(tmp)
    db.write_query("CREATE TABLE files (path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL);")
    db.write_query("CREATE TABLE agent_checkpoints (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, session_id TEXT, checkpoint_id TEXT, timestamp REAL);")
    
    p1 = _build_telemetry_payload(db)
    h1 = _hash_payload(p1)
    time.sleep(0.05)
    p2 = _build_telemetry_payload(db)
    h2 = _hash_payload(p2)
    
    print(f"Hash 1 (t=0.00s): {h1}")
    print(f"Hash 2 (t=0.05s): {h2}")
    print(f"p1['janitor_status']['next_scheduled_run']: {p1['janitor_status']['next_scheduled_run']}")
    print(f"p2['janitor_status']['next_scheduled_run']: {p2['janitor_status']['next_scheduled_run']}")
    print(f"Hashes são idênticos em banco ocioso? {h1 == h2}")
    
    confirmed = (h1 != h2)
    print(f"-> [CONFIRMADO] Detecção de mudanças 100% inoperante (re-emissão perpétua): {confirmed}\n")
    return confirmed

def test_finding_5_cors_and_unauthenticated_mutations():
    print("=" * 70)
    print("TESTE 5: CORS Permissivo e Mutações de Estado Sem Autenticação")
    print("=" * 70)
    client = TestClient(app)
    
    # 5.1 Verificar CORS headers com Origin externa
    res_cors = client.options("/api/mcp/state", headers={
        "Origin": "http://evil-attacker-site.com",
        "Access-Control-Request-Method": "POST",
    })
    print(f"CORS allow-origin retornado para site arbitrário: {res_cors.headers.get('access-control-allow-origin')}")
    print(f"CORS allow-credentials: {res_cors.headers.get('access-control-allow-credentials')}")
    
    # 5.2 Mudar estado de sessão alheia via POST não-autenticado
    res_state = client.post("/api/mcp/state", json={"session_id": "victim_agent", "state_name": "MAINTENANCE"})
    print(f"Mutações de estado de sessão sem token/auth: status={res_state.status_code}, state={res_state.json().get('active_state')}")
    
    # 5.3 Mudar modo de gating sem auth
    res_gate = client.post("/api/gating/config", json={"mode": "auto-approve"})
    print(f"Alteração de regime monorepo para auto-approve sem auth: status={res_gate.status_code}, mode={res_gate.json().get('new_mode')}")
    
    # 5.4 Injetar tokens no governor sem auth
    res_gov = client.post("/api/governor/report", json={"tokens_used": 999999})
    print(f"Injeção de consumo de tokens no governor: status={res_gov.status_code}, new_tpm={res_gov.json()['metrics']['current_tpm']}")
    
    confirmed = (res_state.status_code == 200 and res_gate.status_code == 200 and res_gov.status_code == 200)
    print(f"-> [CONFIRMADO] Controle total da governança acessível a terceiros sem credenciais: {confirmed}\n")
    return confirmed

def test_finding_6_timestamp_crash_on_none_and_str():
    print("=" * 70)
    print("TESTE 6: Crash em Timestamps (NoneType e ISO String)")
    print("=" * 70)
    tmp = tempfile.mktemp(suffix=".db")
    db = ConciergeDatabaseManager(tmp)
    db.write_query("CREATE TABLE files (path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL);")
    db.write_query("CREATE TABLE agent_checkpoints (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, session_id TEXT, checkpoint_id TEXT, timestamp REAL);")
    
    # 6.1 Checkpoint com timestamp NULL
    db.write_query(
        "INSERT INTO agent_checkpoints (agent_id, session_id, checkpoint_id, timestamp) VALUES (?, ?, ?, ?);",
        ("agent_1", "sess_null", "chk_1", None)
    )
    crash_null = False
    try:
        _build_telemetry_payload(db)
    except TypeError as e:
        crash_null = True
        print(f"6.1 Crash com timestamp=None: {e}")
        
    # Limpa e testa com string ISO (padrão SQLite CURRENT_TIMESTAMP)
    db.write_query("DELETE FROM agent_checkpoints;")
    db.write_query(
        "INSERT INTO agent_checkpoints (agent_id, session_id, checkpoint_id, timestamp) VALUES (?, ?, ?, ?);",
        ("agent_1", "sess_str", "chk_2", "2026-09-24 21:00:00")
    )
    crash_str = False
    try:
        _build_telemetry_payload(db)
    except TypeError as e:
        crash_str = True
        print(f"6.2 Crash com timestamp ISO string: {e}")
        
    confirmed = crash_null and crash_str
    print(f"-> [CONFIRMADO] Fragilidade fatal de tipagem em datas SQLite: {confirmed}\n")
    return confirmed

def main():
    f1 = test_finding_1_production_schema_missing_tables()
    f2 = test_finding_2_unconfigured_db_manager()
    f3 = test_finding_3_sse_stream_5_seconds_abort()
    f4 = test_finding_4_perpetual_hash_invalidation()
    f5 = test_finding_5_cors_and_unauthenticated_mutations()
    f6 = test_finding_6_timestamp_crash_on_none_and_str()
    
    print("=" * 70)
    print("RESUMO DE REPRODUÇÃO (interface/telemetry_api.py):")
    print(f"Achado 1 (Tabelas Inexistentes / Crash 500 em Produção): {'REPRODUZIDO' if f1 else 'FALHOU'}")
    print(f"Achado 2 (Inoperância Out-of-the-Box / db_manager None): {'REPRODUZIDO' if f2 else 'FALHOU'}")
    print(f"Achado 3 (Stream SSE Morre após 5s / max_checks=5): {'REPRODUZIDO' if f3 else 'FALHOU'}")
    print(f"Achado 4 (Invalidação Perpétua de Hash por datetime.now): {'REPRODUZIDO' if f4 else 'FALHOU'}")
    print(f"Achado 5 (CORS Permissivo e Mutações Desprotegidas): {'REPRODUZIDO' if f5 else 'FALHOU'}")
    print(f"Achado 6 (Crash de Tipagem em Timestamps None e String): {'REPRODUZIDO' if f6 else 'FALHOU'}")
    print("=" * 70)

if __name__ == "__main__":
    main()
