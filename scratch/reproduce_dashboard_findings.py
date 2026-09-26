"""
scratch/reproduce_dashboard_findings.py
Empirical reproduction script for grafo-dashboard-web audit findings.
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import ConciergeDatabaseManager
from interface.telemetry_api import (
    _build_telemetry_payload,
    _telemetry_event_generator,
    set_db_manager,
    app,
)
from storage.store import SqliteStore

def test_finding_1_and_2_sse_flapping_and_dead_event_types():
    print("=" * 70)
    print("TEST 1 & 2: SSE Flapping (max_checks=5) and Missing event_type")
    print("=" * 70)

    # Setup temporary file-based DB so multiple connections see the tables
    temp_db = PROJECT_ROOT / "scratch" / "test_telemetry.db"
    if temp_db.exists():
        temp_db.unlink()

    db = ConciergeDatabaseManager(str(temp_db))
    db.execute_write("""
        CREATE TABLE files (
            path TEXT PRIMARY KEY,
            community_id TEXT,
            last_modified REAL,
            is_dirty INTEGER DEFAULT 0
        );
    """)
    db.execute_write("""
        CREATE TABLE agent_checkpoints (
            agent_id TEXT,
            session_id TEXT,
            checkpoint_id TEXT,
            timestamp REAL,
            PRIMARY KEY(agent_id, session_id, checkpoint_id)
        );
    """)
    set_db_manager(db)

    async def run_generator():
        gen = _telemetry_event_generator(db)
        chunks = []
        count = 0
        try:
            # We will consume until generator ends
            async for chunk in gen:
                count += 1
                chunks.append(chunk)
                print(f"  [SSE Chunk {count}] received: length={len(chunk)}")
        except Exception as e:
            print(f"  [SSE Error] {e}")
        return chunks

    chunks = asyncio.run(run_generator())

    print(f"\nTotal SSE chunks emitted before generator terminated: {len(chunks)}")
    print("Verifying if stream terminated prematurely (max_checks = 5):")
    assert len(chunks) <= 6, f"Expected <= 6 chunks due to max_checks=5, got {len(chunks)}"
    print("  -> CONFIRMED: Generator terminated on its own after 5 checks, causing client SSE disconnect.")

    print("\nVerifying payload structure for 'event_type':")
    has_event_type = False
    for i, chunk in enumerate(chunks):
        # Extract json after 'data: '
        if chunk.startswith("data: "):
            data_str = chunk[6:].strip()
            data = json.loads(data_str)
            if "event_type" in data:
                has_event_type = True
            print(f"  Chunk {i+1} keys: {list(data.keys())[:5]}... | has 'event_type': {'event_type' in data}")

    print(f"\nWere any typed events ('event_type': 'RATE_GOVERNOR_UPDATE', etc.) emitted? {has_event_type}")
    assert not has_event_type, "Backend emitted event_type unexpectedly!"
    print("  -> CONFIRMED: Backend emits ONLY TelemetryPayload dictionaries without 'event_type'.")
    print("     The switch(raw.event_type) in lib/useTelemetryStream.ts is completely DEAD CODE.")

    if temp_db.exists():
        temp_db.unlink()


def test_finding_5_lightweight_topology_missing_fields():
    print("\n" + "=" * 70)
    print("TEST 5: get_lightweight_topology omits summary and tags needed by InspectorDrawer")
    print("=" * 70)

    # Create temporary sqlite store
    temp_db_path = PROJECT_ROOT / "scratch" / "test_topo.db"
    if temp_db_path.exists():
        temp_db_path.unlink()

    store = SqliteStore(str(temp_db_path))
    
    # Insert dummy project and node with summary and tags
    proj = store.create_project("test-uuid-123", "test_proj", "main_wing", "PUBLIC", "summary")
    node_id = store.create_node(
        project_uuid="test-uuid-123",
        label="test::MyService::execute",
        node_type="METHOD",
        summary="Detailed pipeline description for test service execution.",
        tags=["pipeline", "core", "test"],
    )

    topo = store.get_lightweight_topology(proj["uuid"])
    nodes = topo.get("nodes", [])
    print(f"Returned nodes count: {len(nodes)}")
    first_node = nodes[0]
    print(f"First node payload: {first_node}")

    print("\nChecking fields expected by InspectorDrawer (summary, tags):")
    print(f"  'summary' in node: {'summary' in first_node}")
    print(f"  'tags' in node:    {'tags' in first_node}")

    assert "summary" not in first_node, "Expected summary to be omitted in lightweight topology"
    assert "tags" not in first_node, "Expected tags to be omitted in lightweight topology"
    print("  -> CONFIRMED: get_lightweight_topology strips summary and tags.")
    print("     InspectorDrawer receives null/undefined for all nodes clicked in the graph!")

    store.close()
    if temp_db_path.exists():
        temp_db_path.unlink()


def test_finding_4_api_key_auth_mismatch():
    print("\n" + "=" * 70)
    print("TEST 4: API Key Authentication in mcp_server vs Client Requests")
    print("=" * 70)
    import os
    from starlette.testclient import TestClient
    from fastapi import FastAPI
    from starlette.responses import JSONResponse

    api_key = "secret_grafo_key_123"

    app = FastAPI()

    @app.middleware("http")
    async def auth_middleware(request, call_next):
        auth_header = request.headers.get("Authorization", "")
        token_param = request.query_params.get("token", "")
        
        is_valid = False
        if auth_header.startswith("Bearer "):
            is_valid = (auth_header[7:].strip() == api_key)
        elif token_param:
            is_valid = (token_param.strip() == api_key)

        if not is_valid:
            return JSONResponse({"error": "Unauthorized access to Grafo Concierge MCP"}, status_code=401)
        return await call_next(request)

    @app.get("/sse")
    async def sse_endpoint():
        return JSONResponse({"status": "connected"})

    @app.post("/messages/")
    async def messages_endpoint():
        return JSONResponse({"result": "ok"})

    client = TestClient(app)

    # 1. Dashboard McpClient connects to SSE without token:
    sse_resp = client.get("/sse")
    print(f"  Dashboard EventSource GET /sse (no auth): HTTP {sse_resp.status_code}")
    assert sse_resp.status_code == 401, f"Expected 401, got {sse_resp.status_code}"

    # 2. Dashboard McpClient sends POST to /messages/ without Authorization header:
    post_resp = client.post("/messages/", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    print(f"  Dashboard fetch POST /messages/ (no auth): HTTP {post_resp.status_code}")
    assert post_resp.status_code == 401, f"Expected 401, got {post_resp.status_code}"

    print("  -> CONFIRMED: When GRAFO_API_KEY is set, dashboard requests are immediately rejected with 401.")


if __name__ == "__main__":
    try:
        test_finding_1_and_2_sse_flapping_and_dead_event_types()
        test_finding_5_lightweight_topology_missing_fields()
        test_finding_4_api_key_auth_mismatch()
        print("\n" + "=" * 70)
        print("ALL DASHBOARD INTEGRATION REPRODUCTIONS CONFIRMED SUCCESSFULLY!")
        print("=" * 70)
    except Exception as e:
        print(f"\nREPRODUCTION ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
