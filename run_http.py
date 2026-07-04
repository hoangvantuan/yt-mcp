"""Entrypoint HTTP: gắn app MCP (streamable-http, stateless) + route web /auth, /upload.

Credentials người dùng theo từng request (header). Route web dùng chung cổng với MCP.
"""
import uvicorn
from starlette.routing import Route
from mcp.server.transport_security import TransportSecuritySettings

import web
from server import mcp

# Stateless: không giữ session; creds gửi mỗi request.
mcp.settings.stateless_http = True
# Tắt DNS-rebinding protection để client nối qua IP LAN/Tailscale (Host tùy ý).
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

# App Starlette của FastMCP (endpoint MCP mặc định ở /mcp).
app = mcp.streamable_http_app()

# Gắn thêm route web (tái dùng cùng tiến trình/cổng).
app.router.routes.extend([
    Route("/auth", web.auth_start, methods=["GET"]),
    Route("/auth/callback", web.auth_callback, methods=["GET"]),
    Route("/upload", web.upload_dispatch, methods=["GET", "POST"]),
])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
