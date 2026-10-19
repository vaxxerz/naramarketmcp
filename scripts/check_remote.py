"""Verify a deployment; read its connector token from .env or the environment."""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
base = sys.argv[1].rstrip("/")
token = os.environ["MCP_ACCESS_TOKEN"]
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"}

health = requests.get(f"{base}/healthz", timeout=120)
assert health.status_code == 200 and health.json()["status"] == "ok"
print("Health: OK")
assert requests.post(f"{base}/mcp", json={}, timeout=30).status_code == 401
print("Unauthenticated access: blocked (401)")
for request_id, method, params in [
    (1, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "deployment-check", "version": "1"}}),
    (2, "tools/list", {}),
    (3, "tools/call", {"name": "get_api_operations", "arguments": {"service_type": "public_data_standard"}}),
]:
    response = requests.post(f"{base}/mcp", headers=headers, timeout=60, json={
        "jsonrpc": "2.0", "id": request_id, "method": method, "params": params,
    })
    assert response.status_code == 200, f"{method}: HTTP {response.status_code}"
    result = response.json()
    assert "error" not in result and not result["result"].get("isError", False), f"{method}: RPC error"
    if method == "tools/list":
        assert len(result["result"]["tools"]) == 16
        print("Tools: 16")
    else:
        print(f"{method}: OK")
print("Live data query requires an approved NARAMARKET_SERVICE_KEY; not tested here.")
