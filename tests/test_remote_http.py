"""Exercise the real Streamable HTTP endpoint used by Claude Team."""

import pytest
from starlette.testclient import TestClient

from src.core.remote_http import create_http_app
from src.main import mcp

TOKEN = "test-only-connector-token-" + "x" * 32
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json, text/event-stream",
}


def test_public_binding_requires_strong_token(monkeypatch):
    monkeypatch.delenv("MCP_ACCESS_TOKEN", raising=False)
    with pytest.raises(ValueError, match="required"):
        create_http_app(mcp, "0.0.0.0")
    monkeypatch.setenv("MCP_ACCESS_TOKEN", "short")
    with pytest.raises(ValueError, match="32"):
        create_http_app(mcp, "0.0.0.0")


def test_auth_health_and_mcp_protocol_without_data_key(monkeypatch):
    monkeypatch.setenv("MCP_ACCESS_TOKEN", TOKEN)
    monkeypatch.delenv("NARAMARKET_SERVICE_KEY", raising=False)
    monkeypatch.delenv("QUERY_STRING", raising=False)
    with TestClient(create_http_app(mcp, "0.0.0.0")) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        for method in (client.get, client.post, client.delete):
            assert method("/mcp").status_code == 401
        assert client.get("/mcp", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get("/mcp", params={"token": TOKEN}).status_code == 401
        response = client.post("/mcp", headers=HEADERS, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-03-26", "capabilities": {},
                "clientInfo": {"name": "deployment-check", "version": "1"},
            },
        })
        assert response.status_code == 200, response.text
        assert "serverInfo" in response.json()["result"]
        response = client.post("/mcp", headers=HEADERS, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        })
        assert response.status_code == 200, response.text
        names = {tool["name"] for tool in response.json()["result"]["tools"]}
        assert len(names) == 16
        assert "get_recent_bid_announcements" in names
        response = client.post("/mcp", headers=HEADERS, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "get_api_operations", "arguments": {"service_type": "public_data_standard"}},
        })
        assert response.status_code == 200, response.text
        assert not response.json()["result"].get("isError", False)


def test_portal_key_and_request_error_do_not_leak(monkeypatch, caplog):
    import requests
    from src.core.config import get_service_key
    from src.core.enhanced_client import EnhancedAPIClient

    monkeypatch.setenv("NARAMARKET_SERVICE_KEY", "secret%2Bvalue%2F%3D")
    monkeypatch.delenv("QUERY_STRING", raising=False)
    assert get_service_key() == "secret+value/="
    client = EnhancedAPIClient()

    def fail(*args, **kwargs):
        raise requests.ConnectionError("https://example.test/?ServiceKey=secret+value/=")

    monkeypatch.setattr(client.session, "get", fail)
    # Call the undecorated body to avoid intentional retry delays.
    with pytest.raises(RuntimeError) as error:
        client.call_api.__wrapped__(client, "public_data_standard", "getDataSetOpnStdBidPblancInfo", {})
    assert "secret" not in str(error.value)
    assert "secret" not in caplog.text
