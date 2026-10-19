"""Authenticated Streamable HTTP deployment for a shared Claude connector."""

import hmac
import logging
import os

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

logger = logging.getLogger("naramarket.remote_auth")


class TeamAccessMiddleware:
    """Protect every HTTP route except the platform's health probe."""

    def __init__(self, app, token: str):
        self.app = app
        self.expected_token = token.encode("utf-8")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            if scope["path"] == "/healthz" and scope["method"] in {"GET", "HEAD"}:
                response = JSONResponse({"status": "ok"})
                await response(scope, receive, send)
                return
            authorization = Headers(scope=scope).get("authorization", "")
            parts = authorization.split()
            reason = None
            if not authorization:
                reason = "missing_authorization_header"
            elif not parts or parts[0].lower() != "bearer":
                reason = "missing_bearer_prefix"
            elif len(parts) != 2:
                reason = "malformed_bearer_header"
            elif not hmac.compare_digest(parts[1].encode("utf-8"), self.expected_token):
                reason = "token_mismatch"
            if reason:
                # Never log credentials, headers, query strings, or request bodies.
                logger.warning(
                    "MCP authentication rejected: reason=%s authorization_present=%s credential_length=%d",
                    reason, bool(authorization), len(parts[-1]) if parts else 0,
                )
                response = JSONResponse(
                    {"error": "Unauthorized", "reason": reason}, status_code=401,
                    headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_http_app(mcp, host: str):
    token = os.environ.get("MCP_ACCESS_TOKEN", "").strip()
    if token and len(token) < 32:
        raise ValueError("MCP_ACCESS_TOKEN must contain at least 32 characters")
    if not token and host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("MCP_ACCESS_TOKEN is required for a public HTTP server")
    # Stateless requests survive restarts and do not share team members' sessions.
    app = mcp.http_app(path="/mcp", stateless_http=True, json_response=True)
    if token:
        app.add_middleware(TeamAccessMiddleware, token=token)
    if not token:
        from starlette.routing import Route

        async def health(request):
            return JSONResponse({"status": "ok"})

        app.routes.append(Route("/healthz", health, methods=["GET", "HEAD"]))
    return app
