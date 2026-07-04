"""Auth stateless keyed-by-refresh-token.

Nguyên tắc: server KHÔNG lưu token người dùng. Mỗi request mang refresh token
qua header. Server đổi refresh -> access, cache RAM theo sha256(refresh_token)
nên đa người dùng không rò chéo (key tra cứu chính là credential người gọi).
"""
import hashlib
import threading
import time
from typing import Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from mcp.server.lowlevel.server import request_ctx

import config

# cache: sha256(refresh_token) -> (access_token, expiry_epoch)
_token_cache: dict[str, tuple[str, float]] = {}
_cache_lock = threading.Lock()


def _refresh_token_from_header() -> str:
    """Đọc refresh token từ header request hiện tại (transport streamable-http)."""
    try:
        request = request_ctx.get().request
    except LookupError as exc:
        raise RuntimeError(
            "No active HTTP request context; server phải chạy transport streamable-http."
        ) from exc
    headers = getattr(request, "headers", None)
    token = headers.get(config.REFRESH_TOKEN_HEADER) if headers else None
    if not token:
        raise ValueError(
            f"Missing credential: cần header '{config.REFRESH_TOKEN_HEADER}'. "
            f"Lấy refresh token bằng cách mở {config.PUBLIC_BASE_URL or '<PUBLIC_BASE_URL>'}/auth"
        )
    return token


def current_refresh_token() -> str:
    """Refresh token của request hiện tại (để đưa vào job upload chạy nền)."""
    return _refresh_token_from_header()


def exchange_refresh_for_access(refresh_token: str) -> str:
    """Đổi refresh token -> access token, có cache theo hash(refresh_token)."""
    key = hashlib.sha256(refresh_token.encode()).hexdigest()
    now = time.time()
    with _cache_lock:
        cached = _token_cache.get(key)
        if cached and cached[1] > now:
            return cached[0]

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri=config.TOKEN_URI,
        scopes=config.SCOPES,
    )
    creds.refresh(GoogleRequest())  # gọi Google token endpoint

    with _cache_lock:
        _token_cache[key] = (creds.token, now + config.ACCESS_TOKEN_TTL_SECONDS)
    return creds.token


def _credentials_for(refresh_token: str) -> Credentials:
    access = exchange_refresh_for_access(refresh_token)
    return Credentials(
        token=access,
        refresh_token=refresh_token,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri=config.TOKEN_URI,
        scopes=config.SCOPES,
    )


def get_service(name: str, version: str) -> Any:
    """Trả về client Google API dựng từ refresh token trong header request."""
    refresh_token = _refresh_token_from_header()
    creds = _credentials_for(refresh_token)
    return build(name, version, credentials=creds, cache_discovery=False)


def get_data_service() -> Any:
    return get_service("youtube", "v3")


def get_analytics_service() -> Any:
    return get_service("youtubeAnalytics", "v2")


def credentials_from_refresh_token(refresh_token: str) -> Credentials:
    """Cho job upload chạy ngoài request context (đã bắt refresh token sẵn)."""
    return _credentials_for(refresh_token)


def build_service_from_refresh(name: str, version: str, refresh_token: str) -> Any:
    """Dựng client Google API từ refresh token cho sẵn (không cần request context)."""
    creds = _credentials_for(refresh_token)
    return build(name, version, credentials=creds, cache_discovery=False)
